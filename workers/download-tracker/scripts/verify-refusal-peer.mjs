/**
 * AZRT-REFUSAL-RECEIPT-1.0 addendum, peer side: coded non-auth refusals are reported to the runtime
 * peer door; the refusal never changes; no binding / failure / slow -> honest unsealed status;
 * auth refusals, 429s and refusals-chain tether packets are not sealed. Author: Aziel Eliab.
 */
import assert from "node:assert/strict";
import { withPeerRefusalReceipt, peerRefusals, isAuthRefusal, REFUSAL_PEER_URL } from "../src/refusal-peer.js";

const SURFACE = process.env.SURFACE || "azos";
const calls = [];
const view = { spec: "AZRT-REFUSAL-RECEIPT-1.0", kind: "refusal", sealed: true, chain: "refusals", seq: 7, h: "a".repeat(64), lattice: { primary: "b".repeat(64), secondary: "c".repeat(64) }, status: "sealed" };
const bind = { fetch: async (req) => { calls.push({ url: req.url, body: await req.json() }); return new Response(JSON.stringify({ ok: true, refusal_receipt: { ...view, surface: SURFACE } }), { headers: { "content-type": "application/json" } }); } };
const refusal = (status, body) => new Response(JSON.stringify(body, null, 2), { status, headers: { "content-type": "application/json" } });
const req = (p, m = "GET") => new Request("https://tracker.example" + p, { method: m });
let n = 0;

// 1) coded refusal: unchanged fields + refusal_receipt + header; peer door called once with the surface.
let r = await withPeerRefusalReceipt(req("/v1/newsmap/x"), refusal(400, { ok: false, code: "NEWSMAP-UNKNOWN-OP", message: "unknown op" }), { AZIEL_RUNTIME: bind }, { surface: SURFACE });
let b = await r.json();
assert.equal(r.status, 400); assert.equal(b.ok, false); assert.equal(b.code, "NEWSMAP-UNKNOWN-OP"); assert.equal(b.message, "unknown op");
assert.equal(b.refusal_receipt.sealed, true); assert.equal(b.refusal_receipt.surface, SURFACE);
assert.match(r.headers.get("x-azrt-refusal-receipt"), /^sealed; chain=refusals; seq=7; h=a{64}$/);
assert.equal(calls.length, 1); assert.equal(calls[0].url, REFUSAL_PEER_URL);
assert.deepEqual(Object.keys(calls[0].body).sort(), ["code", "method", "reason", "reason_sha256", "route", "status", "surface"]);
// RIB-018 follow-up: reason text is never sent, only the sha256 hex of the full reason.
assert.equal(calls[0].body.reason, null); assert.equal(calls[0].body.reason_sha256, "eea83946a6239e4cf834ab9e1704152b56c798353d6f6583014cbcafc08ef8d6");
assert.equal(calls[0].body.surface, SURFACE); assert.equal(calls[0].body.route, "/v1/newsmap/x"); n++;

// 2) not sealed: success, 429, auth codes, 401, uncoded, already sealed upstream, refusals tether packet.
const skip = [
  [req("/"), new Response("ok")],
  [req("/x"), refusal(429, { ok: false, code: "RATE-LIMITED" })],
  [req("/x"), refusal(401, { ok: false, code: "SOMETHING" })],
  [req("/v1/tether/tip", "POST"), refusal(403, { ok: false, code: "TETHER-SIG" })],
  [req("/x"), refusal(400, { ok: false, code: "token_required" })],
  [req("/x"), refusal(404, { error: "not found" })], // uncoded outside /v1/: not sealed
  [req("/v1/x"), refusal(500, { error: "boom" })], // uncoded 5xx: not a refusal
  [req("/v1/mesh/install"), refusal(400, { ok: false, code: "ONBOARD-BAD-SLUG", refusal_receipt: view })],
];
for (const [q, s] of skip) {
  const before = calls.length;
  const out = await withPeerRefusalReceipt(q, s, { AZIEL_RUNTIME: bind }, { surface: SURFACE });
  assert.equal(calls.length, before); assert.equal(out.headers.get("x-azrt-refusal-receipt"), null);
}
const before = calls.length;
await withPeerRefusalReceipt(req("/v1/tether/tip", "POST"), refusal(409, { ok: false, code: "TETHER-LINK" }), { AZIEL_RUNTIME: bind }, { surface: SURFACE, tetherChain: "refusals" });
assert.equal(calls.length, before);
assert.equal(isAuthRefusal(403, "CL-NOT-ISSUER"), true); assert.equal(isAuthRefusal(400, "MESH-UNKNOWN"), false); n++;

// 2b) uncoded 4xx under /v1/: fixed code, body unchanged; caller-echoing reason sent only as a hash.
let c0 = calls.length;
r = await withPeerRefusalReceipt(req("/v1/newsmap/zz-caller-text?q=hello-there"), refusal(404, { error: "no such op zz-caller-text" }), { AZIEL_RUNTIME: bind }, { surface: SURFACE });
b = await r.json();
assert.equal(b.code, undefined); assert.equal(b.error, "no such op zz-caller-text");
assert.equal(calls.length, c0 + 1); assert.equal(calls[c0].body.code, "HTTP-404-UNCODED");
assert.equal(calls[c0].body.reason, null); assert.match(calls[c0].body.reason_sha256, /^[a-f0-9]{64}$/);
assert.equal(JSON.stringify(calls[c0].body).includes("hello-there"), false);
n++;

// 3) fail closed: no binding -> unavailable; peer error -> unavailable; slow -> receipt_pending; never a hash.
b = await (await withPeerRefusalReceipt(req("/x"), refusal(400, { ok: false, code: "MESH-UNKNOWN" }), {}, { surface: SURFACE })).json();
assert.equal(b.code, "MESH-UNKNOWN"); assert.equal(b.refusal_receipt.sealed, false); assert.equal(b.refusal_receipt.status, "unavailable"); assert.equal(b.refusal_receipt.h, undefined);
const bad = { fetch: async () => new Response(JSON.stringify({ ok: false, code: "REFUSAL-PEER-NOT-BOUND" }), { status: 403, headers: { "content-type": "application/json" } }) };
b = await (await withPeerRefusalReceipt(req("/x"), refusal(400, { ok: false, code: "MESH-UNKNOWN" }), { AZIEL_RUNTIME: bad }, { surface: SURFACE })).json();
assert.equal(b.refusal_receipt.status, "unavailable"); assert.match(b.refusal_receipt.reason, /403 REFUSAL-PEER-NOT-BOUND/);
const slow = { fetch: () => new Promise(() => {}) };
let waited = 0;
b = await (await withPeerRefusalReceipt(req("/x"), refusal(400, { ok: false, code: "MESH-UNKNOWN" }), { AZIEL_RUNTIME: slow }, { surface: SURFACE, budgetMs: 20, ctx: { waitUntil: () => { waited++; } } })).json();
assert.equal(b.refusal_receipt.status, "receipt_pending"); assert.equal(b.refusal_receipt.sealed, false); assert.equal(waited, 1);
const boom = { fetch: async () => { throw new Error("down"); } };
b = await (await withPeerRefusalReceipt(req("/x"), refusal(503, { ok: false, code: "NEWS-COPY-UNAVAILABLE" }), { AZIEL_RUNTIME: boom }, { surface: SURFACE })).json();
assert.equal(b.code, "NEWS-COPY-UNAVAILABLE"); assert.equal(b.refusal_receipt.status, "unavailable"); n++;

// 4) /v1/refusals: reads the shared chain, filters this surface, compares the local tip.
const list = { fetch: async () => new Response(JSON.stringify({ ok: true, total: 3, tip: { seq: 3, lattice: { primary: "p".repeat(64), secondary: "s".repeat(64) } }, receipts: [{ seq: 3, refusal: { surface: SURFACE } }, { seq: 2, refusal: { surface: "runtime" } }] }), { headers: { "content-type": "application/json" } }) };
let o = await peerRefusals({ AZIEL_RUNTIME: list }, { surface: SURFACE, localTip: { primary: "p".repeat(64) } });
assert.equal(o.status, 200); assert.equal(o.body.tip_state, "agree"); assert.equal(o.body.mine_recent.length, 1); assert.equal(o.body.signed, false);
o = await peerRefusals({ AZIEL_RUNTIME: list }, { surface: SURFACE, localTip: { primary: "q".repeat(64) } });
assert.equal(o.body.tip_state, "lagging");
o = await peerRefusals({}, { surface: SURFACE });
assert.equal(o.status, 503); assert.equal(o.body.code, "REFUSALS-RUNTIME-UNBOUND"); n++;

// 2c) RIB-018 follow-up: a long or body-echoing reason is never sent as text (no cut piece either).
{
  const CALLER = "hello-this-is-public-caller-text-" + "x".repeat(300);
  const c1 = calls.length;
  await withPeerRefusalReceipt(req("/v1/newsmap/x"), refusal(400, { ok: false, code: "NEWSMAP-ECHO", message: `unknown name "${CALLER}"` }), { AZIEL_RUNTIME: bind }, { surface: SURFACE });
  assert.equal(calls.length, c1 + 1);
  assert.equal(calls[c1].body.reason, null); assert.match(calls[c1].body.reason_sha256, /^[a-f0-9]{64}$/);
  assert.equal(JSON.stringify(calls[c1].body).includes("hello-this-is-public"), false); n++;
}

console.log(`verify-refusal-peer (${SURFACE}): ok (${n} groups)`);
