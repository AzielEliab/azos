import assert from "node:assert/strict";
import { runtimeSync } from "../src/runtime-sync.js";
const P = "a".repeat(64);
const fake = (map) => async (url) => { const k = Object.keys(map).find((x) => url.endsWith(x)); return k ? { ok: true, json: async () => map[k] } : { ok: false }; };
const good = {
  "/v1/receipts/tip": { lattice_tip: { ok: true, code: "LATTICE-TIP-OK", chains: [{ c: "acts", seq: 3, primary: P, secondary: P }, { c: "session", seq: 9, primary: "b".repeat(64) }] } },
  "/v1/tether": { bases: [{ base: "kernel", door: "fraggate azos boot_path", live: true, proof_required: "x" }] },
  "/v1/mesh/bootstrap": { ok: true, phase: "E", peer_count: 2, starting_address_count: 1 },
};
const r = await runtimeSync({ side: "t", localChains: [{ chain: "acts", primary: P, verified: true }, { chain: "session", primary: "c".repeat(64) }], fetchImpl: fake(good) });
assert.equal(r.ok, true); assert.equal(r.compare[0].state, "agree"); assert.equal(r.compare[1].state, "lagging");
assert.equal(r.tether_bases[0].live, false); assert.equal(r.tether_bases[0].runtime_says_live, true);
assert.equal(r.alt_internet_live, false); assert.equal(r.writes, false);
assert.ok(!("tiebreak" in r.lattice_tip.chains[0]), "receipt tip without tiebreak does not gain a key");
const tb = { status: "synced", hash: "c".repeat(64), prev: "0".repeat(64) };
const tipped = {
  ...good,
  "/v1/receipts/tip": { lattice_tip: { ok: true, code: "LATTICE-TIP-OK", chains: [{ c: "acts", seq: 3, primary: P, secondary: P, tiebreak: tb }] } },
};
const shown = await runtimeSync({ side: "t", localChains: [], fetchImpl: fake(tipped) });
assert.deepEqual(shown.lattice_tip.chains[0].tiebreak, tb);
const bad = await runtimeSync({ side: "t", fetchImpl: async () => { throw new Error("down"); } });
assert.equal(bad.ok, false); assert.equal(bad.code, "RUNTIME-SYNC-UNREACHABLE");
console.log("verify-runtime-sync: ok");
{
  const { HINTS_HTML } = await import("../src/hints.js");
  assert.match(HINTS_HTML, /azrt\.hints\.v1/); assert.ok(!/fetch\(|sendBeacon|XMLHttpRequest/.test(HINTS_HTML));
  console.log("verify-runtime-sync: hints ok");
}
