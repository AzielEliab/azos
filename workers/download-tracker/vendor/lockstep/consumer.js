/**
 * AZ-LOCKSTEP-1.0 consumer side. Pure; no imports. aziel-runtime, AZInterface, and AZ-OS all run
 * this same file (the legs vendor it byte-for-byte, pinned by SHA-256 in LOCKSTEP.pin.json).
 *
 * Each leg is independent and optional. A leg compares the contract it was built against (its
 * vendored, pinned copy) with the one the runtime serves now at GET /v1/lockstep:
 *   agree  - same contract hash and same design-token hash
 *   drift  - the runtime answered with a different hash
 *   absent - the runtime could not be reached (the leg keeps running standalone)
 * Displayed live flags are true only when the state is agree AND the contract says true AND the
 * leg itself proves it. Anything else shows false. Nothing here writes, signs, or flips a flag.
 * Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
 */
export const LOCKSTEP_SPEC = "AZ-LOCKSTEP-1.0";
export const LOCKSTEP_PATH = "/v1/lockstep";
export const LOCKSTEP_CODES = Object.freeze({
  agree: "LOCKSTEP-AGREE",
  drift: "LOCKSTEP-DRIFT",
  absent: "LOCKSTEP-RUNTIME-ABSENT",
  bad: "LOCKSTEP-BAD-DOCUMENT",
  pin: "LOCKSTEP-PIN-MISMATCH",
});

export function canonicalize(value) {
  if (value === undefined) return undefined;
  if (value === null) return "null";
  const t = typeof value;
  if (t === "number") {
    if (!Number.isFinite(value)) throw new Error("cannot canonicalize non-finite number");
    return JSON.stringify(value);
  }
  if (t === "boolean") return value ? "true" : "false";
  if (t === "string") return JSON.stringify(value);
  if (Array.isArray(value)) return "[" + value.map((v) => canonicalize(v)).join(",") + "]";
  if (t === "object") {
    const keys = Object.keys(value).filter((k) => value[k] !== undefined).sort();
    return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalize(value[k])).join(",") + "}";
  }
  throw new Error(`cannot canonicalize ${t}`);
}

export async function sha256Hex(input) {
  const bytes = typeof input === "string" ? new TextEncoder().encode(input) : input;
  const buf = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function hashOf(value) {
  return sha256Hex(canonicalize(value));
}

const isHex64 = (s) => typeof s === "string" && /^[0-9a-f]{64}$/.test(s);

/** Every boolean in contract.flags, forced false unless agree + contract true + leg proof true. */
export function displayFlags(contractFlags, state, legProof = {}) {
  const out = {};
  for (const k of Object.keys(contractFlags || {}).sort()) {
    if (typeof contractFlags[k] !== "boolean") continue;
    out[k] = state === "agree" && contractFlags[k] === true && legProof[k] === true;
  }
  return out;
}

/** The tether/mesh facts a leg holds locally must match the contract (same chains, same key, same mesh). */
export function checkTether(contract, local = {}) {
  const c = (contract && contract.chains) || {};
  const m = (contract && contract.mesh) || {};
  const problems = [];
  if (local.tether_pubkey !== undefined && local.tether_pubkey !== c.tether_pubkey) problems.push("tether_pubkey");
  if (local.lattice_names && canonicalize(local.lattice_names) !== canonicalize(c.lattice_names)) problems.push("lattice_names");
  if (local.tether_chains && local.tether_chains.some((x) => !(c.tether_chains || []).includes(x))) problems.push("tether_chains");
  if (local.mesh_spec !== undefined && local.mesh_spec !== m.spec) problems.push("mesh_spec");
  if (local.mesh_path !== undefined && local.mesh_path !== m.path) problems.push("mesh_path");
  return { ok: problems.length === 0, problems };
}

/**
 * pinned: the vendored contract/lockstep.json ({contract, contract_sha256, tokens_sha256}).
 * fetchDoc: async () => the runtime /v1/lockstep body, or null/throw when the runtime is absent.
 */
export async function verifyLockstep({ leg, pinned, fetchDoc, legProof = {}, local = {}, timeoutMs = 4000 } = {}) {
  const base = { spec: LOCKSTEP_SPEC, leg, independent: true, optional: true, writes: false };
  if (!pinned || !pinned.contract || !isHex64(pinned.contract_sha256)) {
    return { ...base, ok: false, state: "absent", code: LOCKSTEP_CODES.pin, flags: displayFlags({}, "absent") };
  }
  const pinHash = await hashOf(pinned.contract);
  if (pinHash !== pinned.contract_sha256) {
    return { ...base, ok: false, state: "drift", code: LOCKSTEP_CODES.pin, pinned_contract_sha256: pinned.contract_sha256, computed: pinHash, flags: displayFlags(pinned.contract.flags, "drift") };
  }
  const tether = checkTether(pinned.contract, local);
  let doc = null;
  try {
    let timer;
    const late = new Promise((r) => { timer = setTimeout(() => r(null), timeoutMs); });
    doc = await Promise.race([Promise.resolve().then(fetchDoc), late]);
    clearTimeout(timer);
  } catch {
    doc = null;
  }
  const pinnedOut = { pinned_contract_sha256: pinned.contract_sha256, pinned_tokens_sha256: pinned.tokens_sha256, runtime_version: pinned.contract.runtime && pinned.contract.runtime.version };
  if (!doc || typeof doc !== "object") {
    return { ...base, ...pinnedOut, ok: false, state: "absent", code: LOCKSTEP_CODES.absent, standalone: true, tether, flags: displayFlags(pinned.contract.flags, "absent") };
  }
  if (!doc.contract || !isHex64(doc.contract_sha256) || (await hashOf(doc.contract)) !== doc.contract_sha256) {
    return { ...base, ...pinnedOut, ok: false, state: "drift", code: LOCKSTEP_CODES.bad, tether, flags: displayFlags(pinned.contract.flags, "drift") };
  }
  const agree = doc.contract_sha256 === pinned.contract_sha256 && doc.tokens_sha256 === pinned.tokens_sha256 && tether.ok;
  const state = agree ? "agree" : "drift";
  return {
    ...base,
    ...pinnedOut,
    ok: agree,
    state,
    code: agree ? LOCKSTEP_CODES.agree : LOCKSTEP_CODES.drift,
    runtime_contract_sha256: doc.contract_sha256,
    runtime_tokens_sha256: doc.tokens_sha256,
    runtime_git_sha: doc.git_sha || null,
    tether,
    flags: displayFlags(pinned.contract.flags, state, legProof),
  };
}
