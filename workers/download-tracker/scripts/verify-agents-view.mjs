/**
 * AGENT-SUBNET-1.0 peer viewer: public counts + tip compare, signed-statement forward only,
 * private keys refused and never forwarded, fail closed without the binding. Author: Aziel Eliab.
 */
import assert from "node:assert/strict";
import { agentsPublic, agentsScoped, agentsPanelHtml, agentsTimeoutMs, visitorIpHash, agentIpKey, bucketSeq } from "../src/agents-view.js";
import { HINTS_HTML } from "../src/hints.js";
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
// Timeouts (AZBot #40/#45): a runtime that never answers gives AGENTS-RUNTIME-TIMEOUT, fail closed, on both calls.
const hang = { fetch: (req) => new Promise((res, rej) => { if (req.signal) req.signal.addEventListener("abort", () => rej(new Error("aborted"))); }) };
let t0 = Date.now();
r = await agentsPublic({ AZIEL_RUNTIME: hang, AGENTS_RUNTIME_TIMEOUT_MS: "300" }, { surface: SURFACE });
assert.equal(r.status, 503); assert.equal(r.body.code, "AGENTS-RUNTIME-TIMEOUT"); assert.equal(r.body.timeout_ms, 300); assert.equal(r.body.fail_closed, true); assert.ok(Date.now() - t0 < 2000);
t0 = Date.now();
r = await agentsScoped({ AZIEL_RUNTIME: hang, AGENTS_RUNTIME_TIMEOUT_MS: "300" }, post(view), { surface: SURFACE });
assert.equal(r.status, 503); assert.equal(r.body.code, "AGENTS-RUNTIME-TIMEOUT"); assert.equal(r.body.live, false); assert.ok(Date.now() - t0 < 2000);
assert.equal(agentsTimeoutMs({}), 4000); assert.equal(agentsTimeoutMs({ AGENTS_RUNTIME_TIMEOUT_MS: "5" }), 250); assert.equal(agentsTimeoutMs({ AGENTS_RUNTIME_TIMEOUT_MS: "99999" }), 10000); n++;
// A throwing runtime is UNREACHABLE, not a hang.
r = await agentsScoped({ AZIEL_RUNTIME: { fetch: async () => { throw new Error("x"); } } }, post(view), { surface: SURFACE });
assert.equal(r.body.code, "AGENTS-RUNTIME-UNREACHABLE"); n++;
// Hashed visitor IP forwarded for the runtime's limiter; the raw IP never leaves.
const seen = [];
const bind2 = { fetch: async (req) => { seen.push({ h: Object.fromEntries(req.headers), body: await req.text() }); return Response.json({ ok: true, matched: 0, receipts: [] }); } };
const ipReq = new Request("https://tracker.example/v1/agents/receipts", { method: "POST", headers: { "cf-connecting-ip": "192.0.2.77" }, body: JSON.stringify(view) });
r = await agentsScoped({ AZIEL_RUNTIME: bind2 }, ipReq, { surface: SURFACE });
assert.equal(r.status, 200);
const want = await visitorIpHash(new Request("https://x/", { headers: { "cf-connecting-ip": "192.0.2.77" } }));
assert.match(want, /^[a-f0-9]{32}$/);
assert.equal(seen[0].h["x-azrt-visitor-ip-h"], want);
assert.ok(!JSON.stringify(seen[0]).includes("192.0.2.77"), "raw visitor IP must not be forwarded");
assert.ok(!("cf-connecting-ip" in seen[0].h));
seen.length = 0;
await agentsScoped({ AZIEL_RUNTIME: bind2 }, post(view), { surface: SURFACE });
assert.ok(!("x-azrt-visitor-ip-h" in seen[0].h)); n++;
// Honest wording: "designed to", hashed not encrypted, no "only you can open".
assert.ok(/designed to/.test(html) && /hashed, not encrypted/.test(html) && /live: false/.test(html));
assert.ok(!/only you can open/i.test(html + HINTS_HTML));
assert.ok(HINTS_HTML.includes("This is designed to let your agents talk to other agents. Messages are designed to be sealed and signed, with a hash-only receipt (hashed, not encrypted). Nothing links without your OK. Not live yet.")); n++;
// No exact row numbers in public (runtime #304 N5): runtime and local tips show a bucketed seq.
r = await agentsPublic({ AZIEL_RUNTIME: bind }, { surface: SURFACE, localTip: { seq: 37, primary: "e".repeat(64), secondary: "f".repeat(64), verified: true } });
assert.equal(r.body.runtime_tip.seq, "<10"); assert.equal(r.body.local_tip.seq, "30+"); assert.equal(r.body.local_tip.primary, "e".repeat(64));
assert.ok(!("tiebreak" in r.body.runtime_tip), "agent receipt tip without tiebreak keeps its keys");
const tbTip = { seq: 9, h: "d".repeat(64), lattice: { primary: "e".repeat(64), secondary: "f".repeat(64), tiebreak: { status: "synced", hash: "c".repeat(64), prev: "0".repeat(64) } } };
const bindTb = { fetch: async () => Response.json({ ok: true, total: 9, by_kind: { send: 2 }, e2e_verified_observed: 0, tip: tbTip, live: false }) };
r = await agentsPublic({ AZIEL_RUNTIME: bindTb }, { surface: SURFACE, localTip: { primary: "e".repeat(64) } });
assert.equal(r.body.runtime_tip.tiebreak.hash, "c".repeat(64));
assert.equal(bucketSeq(9), "<10"); assert.equal(bucketSeq(120), "120+"); assert.equal(bucketSeq("<10"), "<10"); n++;
// IPv6 is cut to its /64 before hashing (same rule as the runtime).
assert.equal(agentIpKey("2001:db8:1:2:aaaa::1"), "2001:db8:1:2::/64");
assert.equal(agentIpKey("192.0.2.1"), "192.0.2.1");
// IPv4-mapped IPv6 is the IPv4 it carries (same rule as the runtime): mapped visitors never share a bucket.
assert.equal(agentIpKey("::ffff:192.0.2.1"), "192.0.2.1");
assert.equal(agentIpKey("::ffff:c000:201"), "192.0.2.1");
assert.ok(agentIpKey("::ffff:192.0.2.1") !== agentIpKey("::ffff:192.0.2.2"));
const v6a = await visitorIpHash(new Request("https://x/", { headers: { "cf-connecting-ip": "2001:db8:1:2:aaaa::1" } }));
const v6b = await visitorIpHash(new Request("https://x/", { headers: { "cf-connecting-ip": "2001:db8:1:2:bbbb:cccc:dddd:9" } }));
const v6c = await visitorIpHash(new Request("https://x/", { headers: { "cf-connecting-ip": "2001:db8:1:3::1" } }));
assert.equal(v6a, v6b); assert.notEqual(v6a, v6c); n++;
console.log(`ok agents view (${SURFACE}): ${n} checks`);
