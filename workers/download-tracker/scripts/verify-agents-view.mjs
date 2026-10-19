/**
 * AGENT-SUBNET-1.0 peer viewer: public counts + tip compare, signed-statement forward only,
 * private keys refused and never forwarded, fail closed without the binding. Author: Aziel Eliab.
 */
import assert from "node:assert/strict";
import { agentsPublic, agentsScoped, agentsPanelHtml } from "../src/agents-view.js";
const SURFACE = process.env.SURFACE || "azos";
const calls = [];
const tip = { seq: 9, h: "d".repeat(64), lattice: { primary: "e".repeat(64), secondary: "f".repeat(64) } };
const bind = { fetch: async (req) => { calls.push({ url: req.url, method: req.method, body: req.method === "POST" ? await req.json() : null }); return req.method === "POST" ? Response.json({ ok: true, scope: "agent", matched: 1, receipts: [{ seq: 3, agentcomm: { kind: "send" } }] }) : Response.json({ ok: true, total: 9, by_kind: { send: 2 }, e2e_verified_observed: 0, tip, live: false }); } };
let n = 0;
let r = await agentsPublic({ AZIEL_RUNTIME: bind }, { surface: SURFACE, localTip: { primary: "e".repeat(64) } });
assert.equal(r.status, 200); assert.equal(r.body.live, false); assert.equal(r.body.tip_state, "agree"); assert.equal(r.body.chain, "agentcomms");
assert.ok(!("receipts" in r.body)); n++;
r = await agentsPublic({ AZIEL_RUNTIME: bind }, { surface: SURFACE, localTip: { primary: "0".repeat(64) } });
assert.equal(r.body.tip_state, "lagging"); n++;
r = await agentsPublic({}, { surface: SURFACE });
assert.equal(r.status, 503); assert.equal(r.body.ok, false); assert.equal(r.body.fail_closed, true); n++;
const view = { v: "AGENT-SUBNET-1.0", kind: "agent-view", scope: "agent", subject_public_key: "x", challenge: "c", t: "t", nonce: "n".repeat(16), sig: "s" };
const post = (b) => new Request("https://tracker.example/v1/agents/receipts", { method: "POST", body: typeof b === "string" ? b : JSON.stringify(b) });
calls.length = 0;
r = await agentsScoped({ AZIEL_RUNTIME: bind }, post(view), { surface: SURFACE });
assert.equal(r.status, 200); assert.equal(r.body.matched, 1); assert.equal(calls.length, 1); assert.deepEqual(calls[0].body, view); n++;
calls.length = 0;
r = await agentsScoped({ AZIEL_RUNTIME: bind }, post({ ...view, private_key: "zz" }), { surface: SURFACE });
assert.equal(r.body.code, "AGENTS-PRIVATE-KEY"); assert.equal(calls.length, 0);
r = await agentsScoped({ AZIEL_RUNTIME: bind }, post({ ...view, seed: "zz" }), { surface: SURFACE });
assert.equal(r.body.code, "AGENTS-PRIVATE-KEY"); assert.equal(calls.length, 0);
r = await agentsScoped({ AZIEL_RUNTIME: bind }, post({ ...view, kind: "agent-send" }), { surface: SURFACE });
assert.equal(r.body.code, "AGENTS-BAD-VIEW"); assert.equal(calls.length, 0);
r = await agentsScoped({ AZIEL_RUNTIME: bind }, post("x".repeat(9000)), { surface: SURFACE });
assert.equal(r.body.code, "AGENTS-BAD-VIEW"); assert.equal(calls.length, 0); n++;
r = await agentsScoped({}, post(view), { surface: SURFACE });
assert.equal(r.status, 503); assert.equal(r.body.code, "AGENTS-RUNTIME-UNBOUND"); n++;
const html = agentsPanelHtml();
assert.ok(html.includes("/v1/agents/receipts")); assert.ok(!/type="password"|name="(seed|private|key)/i.test(html)); assert.ok(/textContent/.test(html) && !/innerHTML/.test(html)); n++;
console.log(`ok agents view (${SURFACE}): ${n} checks`);
