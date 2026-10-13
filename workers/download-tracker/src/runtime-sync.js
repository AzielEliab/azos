/**
 * RUNTIME-SYNC-1.0 (additive, read-only). GET /v1/runtime/sync
 * Mirrors today's aziel-runtime surfaces so this side of the lattice can see them:
 * lattice_tip (RECEIPTS-LATTICE-TIP-1.0), tether bases (TETHER-BASES-1.0), mesh bootstrap and
 * install (MESH-BOOTSTRAP-1.0 / MESH-ONBOARD-1.0), and lattice-learn (LATTICE-LEARN-1.0, runtime-side).
 * Where this tracker stores verified tips of its own, each one is compared with the runtime tip:
 * "agree" (same primary), "lagging" (the runtime has moved on; the next tether push catches up),
 * or "unknown". Nothing here writes, signs, or flips a flag; every live flag stays false.
 * Fails closed: an unreachable runtime gives ok:false and no claims.
 * Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
 */
export const RUNTIME_SYNC_SPEC = "RUNTIME-SYNC-1.0";
export const RUNTIME_ORIGIN = "https://aziel-runtime.vibelock.workers.dev";

async function getJson(fetchImpl, url, ms) {
  const ctl = typeof AbortController === "function" ? new AbortController() : null;
  const t = setTimeout(() => ctl && ctl.abort(), ms);
  try {
    const r = await fetchImpl(url, { headers: { accept: "application/json" }, signal: ctl ? ctl.signal : undefined });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  } finally {
    clearTimeout(t);
  }
}

export async function runtimeSync({ side, localChains = [], fetchImpl = fetch, origin = RUNTIME_ORIGIN, timeoutMs = 4000 } = {}) {
  const honest = { live: false, alt_internet_live: false, packet_path_live: false, second_device: false, public_mail_send_live: false, kernel_live: false, writes: false };
  const [tip, tether, boot] = await Promise.all([
    getJson(fetchImpl, `${origin}/v1/receipts/tip`, timeoutMs),
    getJson(fetchImpl, `${origin}/v1/tether`, timeoutMs),
    getJson(fetchImpl, `${origin}/v1/mesh/bootstrap`, timeoutMs),
  ]);
  const lt = tip && tip.lattice_tip;
  if (!lt || lt.ok !== true || !Array.isArray(lt.chains)) {
    return { ok: false, spec: RUNTIME_SYNC_SPEC, side, code: "RUNTIME-SYNC-UNREACHABLE", fail_closed: true, ...honest };
  }
  const rt = new Map(lt.chains.map((c) => [c.c, c]));
  const compare = (localChains || []).map((l) => {
    const r = rt.get(l.chain);
    if (!r || !l.primary) return { chain: l.chain, state: "unknown" };
    return { chain: l.chain, state: r.primary === l.primary ? "agree" : "lagging", local_primary: l.primary, runtime_primary: r.primary, runtime_seq: r.seq, local_verified: l.verified === true };
  });
  const bases = tether && Array.isArray(tether.bases) ? tether.bases.map((b) => ({ base: b.base, door: b.door, live: false, runtime_says_live: b.live === true, proof_required: b.proof_required, self_test: b.self_test ? { log: b.self_test.log, proves_live: false } : null })) : null;
  return {
    ok: true,
    spec: RUNTIME_SYNC_SPEC,
    side,
    code: "RUNTIME-SYNC-OK",
    source: origin,
    lattice_tip: { code: lt.code, chains: lt.chains.map((c) => ({ c: c.c, seq: c.seq, primary: c.primary, secondary: c.secondary })) },
    compare,
    compare_ok: compare.every((x) => x.state !== "unknown"),
    tether_bases: bases,
    mesh_bootstrap: boot && boot.ok ? { phase: boot.phase, peer_count: boot.peer_count, starting_address_count: boot.starting_address_count, live_multi_provider: false, path: `${origin}/v1/mesh/bootstrap` } : null,
    mesh_install: { path: `${origin}/v1/mesh/install?slug=<slug>&version=<v>`, script: `${origin}/v1/mesh/install.sh?slug=<slug>&version=<v>` },
    lattice_learn: { runtime_op: "fraggate memory lattice-learn", scheduled: "runtime crons", here: false },
    ...honest,
  };
}
