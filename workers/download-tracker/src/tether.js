/**
 * AZ-OS side of the runtime cross-tether (AZRT-AZOS-TETHER-1.0).
 *
 * aziel-runtime SENDS signed dual-lattice tips. This tracker CHECKS and STORES
 * them over its own API. Nothing here runs runtime code, and the runtime does
 * not exec into AZ-OS. The runtime's FragGate `azos` `lattice` op stays refused
 * (REMAIN-OFF item 8). This is not the TemporalLock /v1/lattice bind route.
 *
 * POST /v1/tether/tip checks, in order: shape and size, the pinned runtime
 * public key (RUNTIME_TETHER_PUBKEY), the Ed25519 signature over the canonical
 * packet, every row's primary and secondary hash, the link from the tip already
 * stored (genesis on first contact), and offline doubles. Only then are the new
 * tips written to KV. Any failure refuses and nothing is stored.
 *
 * Dual lattice rules (same as aziel-runtime src/dual-lattice.js):
 *   primary   = H({document: document_hash, prev: primary_prev})
 *   secondary = online:  H({offline: false, prev: secondary_prev, primary})
 *               offline: H({primary: document_hash, username})
 *
 * Not mesh membership. Not a second device. Not a public ledger. Not courtroom proof.
 * Author: Aziel Eliab. Identity is Aziel Eliab only.
 */

export const TETHER_SPEC = "AZRT-AZOS-TETHER-1.0";
export const TETHER_KIND = "azrt-lattice-tip";
export const GENESIS = "0".repeat(64);
export const MAX_BODY_BYTES = 262144;
export const MAX_ROWS = 64;
const HEX64 = /^[a-f0-9]{64}$/;
const USER_RE = /^[a-zA-Z0-9._-]{1,80}$/;
const CHAIN_RE = /^[a-z][a-z0-9_-]{0,31}$/;

export const TETHER_FACTS = Object.freeze({
  spec: TETHER_SPEC,
  direction: "runtime-sends, azos-verifies-and-stores",
  runtime_exec_into_azos: false,
  azos_lattice_refusal_stays: true,
  remain_off_item: 8,
  mesh_node_live: false,
  second_device: false,
  internet_live: false,
  public_ledger: false,
  courtroom_proof: false,
  author: "Aziel Eliab",
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
  if (Array.isArray(value)) return "[" + value.map((item) => canonicalize(item)).join(",") + "]";
  if (t === "object") {
    const keys = Object.keys(value).filter((k) => value[k] !== undefined).sort();
    return "{" + keys.map((k) => JSON.stringify(k) + ":" + canonicalize(value[k])).join(",") + "}";
  }
  throw new Error("cannot canonicalize " + t);
}

export async function sha256Hex(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function primaryOf(documentHash, prev) {
  return sha256Hex(canonicalize({ document: documentHash, prev: prev || GENESIS }));
}

export async function offlineSecondaryOf(documentHash, username) {
  return sha256Hex(canonicalize({ primary: documentHash, username: String(username) }));
}

export async function onlineSecondaryOf(primary, prev) {
  return sha256Hex(canonicalize({ offline: false, prev: prev || GENESIS, primary }));
}

function b64urlBytes(text) {
  const s = String(text || "").replace(/-/g, "+").replace(/_/g, "/");
  const pad = s.length % 4 ? "=".repeat(4 - (s.length % 4)) : "";
  try {
    const bin = atob(s + pad);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  } catch {
    return null;
  }
}

export async function verifySignature(publicKey, packet) {
  const raw = b64urlBytes(publicKey);
  const sig = b64urlBytes(packet && packet.sig);
  if (!raw || raw.length !== 32 || !sig || sig.length !== 64) return false;
  const { sig: _omit, ...unsigned } = packet;
  try {
    const key = await crypto.subtle.importKey("raw", raw, { name: "Ed25519" }, false, ["verify"]);
    return await crypto.subtle.verify("Ed25519", key, sig, new TextEncoder().encode(canonicalize(unsigned)));
  } catch {
    return false;
  }
}

function refuse(code, message, status = 400, extra = {}) {
  return { status, body: { ok: false, refused: true, stored: false, verified: false, code, message, ...extra, ...TETHER_FACTS } };
}

function stateKey(chain) {
  return "tether|chain|" + chain;
}

function offKey(chain, secondary) {
  return "tether|off|" + chain + "|" + secondary;
}

const INDEX_KEY = "tether|index";

async function readJsonKv(kv, key) {
  if (!kv) return null;
  const raw = await kv.get(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function pinnedKey(env) {
  const key = String((env && env.RUNTIME_TETHER_PUBKEY) || "").trim();
  return key || null;
}

/** Check one packet against the stored state. Returns { ok, rows, tips } or a refusal. Pure, no writes. */
export async function checkPacket(packet, { pinned, stored, hasOffline }) {
  if (!packet || typeof packet !== "object" || Array.isArray(packet)) return refuse("TETHER-SHAPE", "The tether body must be one JSON object.");
  if (packet.spec !== TETHER_SPEC || packet.kind !== TETHER_KIND) return refuse("TETHER-SPEC", "Unknown tether spec or kind.");
  if (!CHAIN_RE.test(String(packet.chain || ""))) return refuse("TETHER-CHAIN", "The chain name is not a short roster token.");
  if (!pinned) return refuse("TETHER-KEY-UNPINNED", "This tracker has no pinned runtime public key, so nothing can be verified or stored.", 503);
  if (packet.public_key !== pinned) return refuse("TETHER-KEY-MISMATCH", "The packet key is not the pinned runtime key.", 403);
  if (!(await verifySignature(pinned, packet))) return refuse("TETHER-SIG", "The Ed25519 signature does not verify against the pinned runtime key.", 403);
  const rows = Array.isArray(packet.rows) ? packet.rows : null;
  if (!rows || rows.length < 1 || rows.length > MAX_ROWS) return refuse("TETHER-ROWS", "A packet carries between 1 and " + MAX_ROWS + " rows.");
  let expected = stored && stored.tips ? { primary: stored.tips.primary, secondary: stored.tips.secondary } : { primary: GENESIS, secondary: GENESIS };
  const seenOffline = new Set();
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i] || {};
    if (!HEX64.test(String(row.document_hash)) || !HEX64.test(String(row.primary)) || !HEX64.test(String(row.secondary))) {
      return refuse("TETHER-ROW-SHAPE", "Row " + i + " is missing a 64-hex document, primary, or secondary hash.");
    }
    if (!Array.isArray(row.lattices) || !row.lattices.includes("primary") || !row.lattices.includes("secondary")) {
      return refuse("TETHER-ROW-SHAPE", "Row " + i + " does not name both lattices.");
    }
    if (row.primary_prev !== expected.primary || row.secondary_prev !== expected.secondary) {
      return refuse("TETHER-LINK", "Row " + i + " does not link to the tip this tracker already stored.", 409, { stored_tips: stored ? stored.tips : null });
    }
    if ((await primaryOf(row.document_hash, row.primary_prev)) !== row.primary) {
      return refuse("TETHER-PRIMARY", "Row " + i + " primary hash does not recompute.");
    }
    if (row.offline === true) {
      if (!USER_RE.test(String(row.username || ""))) return refuse("TETHER-USERNAME", "Offline row " + i + " needs a short username handle.");
      if ((await offlineSecondaryOf(row.document_hash, row.username)) !== row.secondary) {
        return refuse("TETHER-SECONDARY", "Row " + i + " offline secondary hash does not recompute.");
      }
      if (seenOffline.has(row.secondary) || (hasOffline && (await hasOffline(row.secondary)))) {
        return refuse("TETHER-DOUBLE", "Row " + i + " is an offline document this user already stored. It was not stored twice.", 409);
      }
      seenOffline.add(row.secondary);
    } else {
      if (row.username != null) return refuse("TETHER-SECONDARY", "Online row " + i + " must not carry a username.");
      if ((await onlineSecondaryOf(row.primary, row.secondary_prev)) !== row.secondary) {
        return refuse("TETHER-SECONDARY", "Row " + i + " online secondary hash does not recompute.");
      }
    }
    expected = { primary: row.primary, secondary: row.secondary };
  }
  if (!packet.tips || packet.tips.primary !== expected.primary || packet.tips.secondary !== expected.secondary) {
    return refuse("TETHER-TIPS", "The packet tips are not the last row's hashes.");
  }
  return { ok: true, rows, tips: expected, offline: [...seenOffline] };
}

export async function receiveTether(request, env, now = new Date().toISOString()) {
  const kv = env && env.DOWNLOADS;
  const text = await request.text();
  if (new TextEncoder().encode(text).length > MAX_BODY_BYTES) {
    const r = refuse("TETHER-SIZE", "The tether body is too large.", 413);
    return r;
  }
  let packet;
  try {
    packet = JSON.parse(text);
  } catch {
    return refuse("TETHER-JSON", "The tether body is not JSON.");
  }
  const chain = String((packet && packet.chain) || "");
  const stored = CHAIN_RE.test(chain) ? await readJsonKv(kv, stateKey(chain)) : null;
  if (stored && packet && packet.tips && stored.tips &&
    stored.tips.primary === packet.tips.primary && stored.tips.secondary === packet.tips.secondary) {
    // Already stored. Still check the signature so an unsigned replay cannot read as verified.
    const pinned = pinnedKey(env);
    if (!pinned || packet.public_key !== pinned || !(await verifySignature(pinned, packet))) {
      return refuse("TETHER-SIG", "The Ed25519 signature does not verify against the pinned runtime key.", 403);
    }
    return { status: 200, body: { ok: true, stored: true, verified: true, already: true, chain, tips: stored.tips, rows: stored.rows, ...TETHER_FACTS } };
  }
  const checked = await checkPacket(packet, {
    pinned: pinnedKey(env),
    stored,
    hasOffline: async (secondary) => Boolean(kv && (await kv.get(offKey(chain, secondary)))),
  });
  if (!checked.ok) return checked;
  if (!kv) return refuse("TETHER-STORE-UNBOUND", "This tracker has no KV binding, so nothing was stored.", 503);
  const next = {
    chain,
    tips: checked.tips,
    rows: (stored && stored.rows ? stored.rows : 0) + checked.rows.length,
    verified: true,
    updated_at: now,
    runtime_git_sha: typeof packet.git_sha === "string" ? packet.git_sha.slice(0, 64) : null,
    packet_hash: typeof packet.packet_hash === "string" ? packet.packet_hash.slice(0, 64) : null,
    public_key: packet.public_key,
    spec: TETHER_SPEC,
  };
  for (const secondary of checked.offline) await kv.put(offKey(chain, secondary), now);
  await kv.put(stateKey(chain), JSON.stringify(next));
  const index = (await readJsonKv(kv, INDEX_KEY)) || [];
  if (!index.includes(chain)) {
    index.push(chain);
    await kv.put(INDEX_KEY, JSON.stringify(index.slice(0, 64)));
  }
  return {
    status: 200,
    body: { ok: true, stored: true, verified: true, already: false, chain, tips: next.tips, rows: next.rows, rows_accepted: checked.rows.length, ...TETHER_FACTS },
  };
}

export async function tetherState(env) {
  const kv = env && env.DOWNLOADS;
  const pinned = pinnedKey(env);
  const index = (await readJsonKv(kv, INDEX_KEY)) || [];
  const chains = [];
  for (const chain of index) {
    const row = await readJsonKv(kv, stateKey(chain));
    if (!row) continue;
    chains.push({
      chain,
      tips: row.tips,
      rows: row.rows,
      verified: row.verified === true && row.public_key === pinned,
      updated_at: row.updated_at,
      runtime_git_sha: row.runtime_git_sha,
    });
  }
  return {
    ok: true,
    ...TETHER_FACTS,
    public_key: pinned,
    key_pinned: Boolean(pinned),
    chains,
    stored_chains: chains.length,
    azos_updated: Boolean(pinned) && chains.length > 0 && chains.every((row) => row.verified),
    azos_updated_rule: "true only when this tracker stored a tip it verified against the pinned runtime key.",
    plain: chains.length
      ? "AZ-OS stored and verified signed lattice tips from aziel-runtime. The runtime did not run anything inside AZ-OS."
      : "AZ-OS has not stored a verified tip yet. Nothing is marked updated.",
  };
}
