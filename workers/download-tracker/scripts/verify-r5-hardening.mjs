/**
 * R5 lockstep hardening (leg side): (1) the proxy deadline covers the body, not only headers; (2) a refusal
 * proxied from the runtime is never sealed a second time by this leg; (3) the KV tether write is
 * compare-and-set: a tip that changed mid-check gives 409 TETHER-CAS-CONFLICT and nothing is overwritten.
 * Leg-agnostic (azinterface and AZ-OS). Author: Aziel Eliab.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("..", import.meta.url));
const AZOS = /name\s*=\s*"azos-/.test(readFileSync(root + "wrangler.toml", "utf8"));
const worker = (await import(root + "src/" + (AZOS ? "index.js" : "entry.js"))).default;
const tether = await import(root + "src/" + (AZOS ? "tether.js" : "lattice-tether.js"));
const { withPeerRefusalReceipt } = await import(root + "src/refusal-peer.js");
globalThis.fetch = async () => { throw new Error("network off in test"); };
const KV = { get: async () => null, put: async () => {}, list: async () => ({ keys: [], list_complete: true }), delete: async () => {} };
const base = { DOWNLOADS: KV, ASSETS: { fetch: async () => new Response("a") } };
const ctx = { waitUntil() {} };
let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };
const call = (path, env, init = {}) => worker.fetch(new Request("https://leg.example" + path, init), env, ctx);
const READ = "/v1/memory";
const isPeer = (req) => new URL(req.url).hostname === "peer.aziel.internal";

// 1. headers arrive, body stalls: still a timeout inside the same deadline, upstream aborted
{
  let seen = null;
  const stall = { fetch: async (req) => {
    if (isPeer(req)) return new Response(JSON.stringify({ refusal_receipt: { sealed: true } }), { headers: { "content-type": "application/json" } });
    seen = req;
    const body = new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode('{"ok":')); } });
    return new Response(body, { status: 200, headers: { "content-type": "application/json" } });
  } };
  const t0 = Date.now();
  const r = await call(READ, { ...base, AZIEL_RUNTIME: stall, LEG_RUNTIME_TIMEOUT_MS: "300" });
  const ms = Date.now() - t0;
  const b = await r.json();
  ok(r.status === 503 && b.code === "LEG-RUNTIME-TIMEOUT" && b.timeout_ms === 300, `stalled body -> timeout (${r.status} ${b.code})`);
  ok(ms < 1500, `body deadline honored (${ms} ms)`);
  ok(seen && seen.signal && seen.signal.aborted === true, "upstream aborted on body stall");
  ok(b.live === false, "nothing shown as live");
}
// 2. a full body inside the deadline passes through unchanged
{
  const good = { fetch: async () => new Response('{"ok":true,"x":1}', { status: 200, headers: { "content-type": "application/json", "content-length": "17" } }) };
  const r = await call(READ, { ...base, AZIEL_RUNTIME: good });
  ok(r.status === 200 && r.headers.get("X-Served-Through") === "AZIEL_RUNTIME", "served through runtime");
  ok((await r.text()) === '{"ok":true,"x":1}', "body intact");
  const h = await call(READ, { ...base, AZIEL_RUNTIME: good }, { method: "HEAD" });
  ok(h.status === 200 && (await h.text()) === "", "HEAD has no body");
}
// 3. a runtime 4xx proxied through the leg is not sealed again
{
  let peer = 0;
  const rt = { fetch: async (req) => {
    if (isPeer(req)) { peer++; return new Response(JSON.stringify({ refusal_receipt: { kind: "refusal", sealed: true } }), { headers: { "content-type": "application/json" } }); }
    return new Response(JSON.stringify({ ok: false, code: "RT-SOMETHING-REFUSED", message: "no" }), { status: 404, headers: { "content-type": "application/json" } });
  } };
  const r = await call(READ, { ...base, AZIEL_RUNTIME: rt });
  const b = await r.json();
  ok(r.status === 404 && b.code === "RT-SOMETHING-REFUSED", "runtime refusal passes through");
  ok(peer === 0, `peer door not called for a runtime refusal (called ${peer})`);
  ok(b.refusal_receipt === undefined && !r.headers.has("X-Azrt-Refusal-Receipt"), "no second receipt added");
  // direct: leg-own refusal still sealed; header-marked ones skipped
  const req = new Request("https://leg.example/v1/x");
  const mk = (h = {}) => new Response(JSON.stringify({ ok: false, code: "LEG-OWN-REFUSED" }), { status: 400, headers: { "content-type": "application/json", ...h } });
  const own = await withPeerRefusalReceipt(req, mk(), { AZIEL_RUNTIME: rt }, { surface: "test", ctx });
  ok(peer === 1 && (await own.json()).refusal_receipt.sealed === true, "leg-own refusal still sealed once");
  await withPeerRefusalReceipt(req, mk({ "X-Served-Through": "AZIEL_RUNTIME" }), { AZIEL_RUNTIME: rt }, { surface: "test", ctx });
  await withPeerRefusalReceipt(req, mk({ "X-Azrt-Refusal-Receipt": "abc" }), { AZIEL_RUNTIME: rt }, { surface: "test", ctx });
  ok(peer === 1, "X-Served-Through / existing receipt header: skipped");
}
// 4. tether KV write is compare-and-set
{
  const vector = JSON.parse(readFileSync(root + "scripts/fixtures/azos-tether-vector.json", "utf8"));
  const [p1, p2] = vector.packets;
  const mkKv = () => { const map = new Map(); return { map, async get(k) { return map.has(k) ? map.get(k) : null; }, async put(k, v) { map.set(k, String(v)); }, async delete(k) { map.delete(k); }, async list() { return { keys: [] }; } }; };
  const post = (env, p) => tether.receiveTether(new Request("https://leg.example/v1/tether/tip", { method: "POST", body: JSON.stringify(p) }), env);
  // a racer stores p1 between our first read and the CAS re-read
  const kv = mkKv();
  const stateK = [...kv.map.keys()];
  let racer = null;
  const env = { DOWNLOADS: kv, RUNTIME_TETHER_PUBKEY: vector.test_public_key };
  const helperKv = mkKv();
  await post({ DOWNLOADS: helperKv, RUNTIME_TETHER_PUBKEY: vector.test_public_key }, p1);
  const sk = [...helperKv.map.keys()].find((k) => k !== "tether|index" && helperKv.map.get(k).includes('"tips"'));
  ok(sk && stateK.length === 0, "state key found");
  let gets = 0;
  const realGet = kv.get.bind(kv);
  kv.get = async (k) => { if (k === sk && ++gets === 2) kv.map.set(k, helperKv.map.get(sk)); return realGet(k); };
  const r = await post(env, p1);
  ok(r.status === 409 && r.body.code === "TETHER-CAS-CONFLICT", `mid-check change refused (${r.status} ${r.body && r.body.code})`);
  ok(kv.map.get(sk) === helperKv.map.get(sk), "racer's tip not overwritten");
  // no race: normal path still stores and links
  const clean = mkKv();
  const e2 = { DOWNLOADS: clean, RUNTIME_TETHER_PUBKEY: vector.test_public_key };
  ok((await post(e2, p1)).status === 200 && (await post(e2, p2)).status === 200, "clean path stores both packets");
  // read-back mismatch (lost the write race) is reported
  const lossy = mkKv();
  lossy.put = async (k, v) => { lossy.map.set(k, k === sk ? helperKv.map.get(sk).replace(/"rows":\d+/, '"rows":999') : String(v)); };
  const r3 = await post({ DOWNLOADS: lossy, RUNTIME_TETHER_PUBKEY: vector.test_public_key }, p1);
  ok(r3.status === 409 && r3.body.code === "TETHER-CAS-CONFLICT", "read-back mismatch -> 409");
  void racer;
}
// 5. hostscan pattern carries the R5 ranges
{
  const src = readFileSync(root + "scripts/verify-lockstep.mjs", "utf8");
  const PRIVATE_IP = eval(src.match(/const PRIVATE_IP = (\/.*\/i);/)[1]);
  for (const bad of ["100.64.0.1", "100.127.1.1", "::1", "fe80::1", "febf::1"]) ok(PRIVATE_IP.test(` ${bad} `), `hostscan catches ${bad}`);
  for (const fine of ["100.63.0.1", "100.128.0.1", "2001:db8::1", "std::10"]) ok(!PRIVATE_IP.test(` ${fine} `), `hostscan passes ${fine}`);
}
// 6. vendored parsing scanner matches the runtime's and catches the inet_aton / mapped forms
{
  const { hostDataFinding } = await import(new URL("./lockstep-hostscan.mjs", import.meta.url).href);
  for (const bad of ["0.0.0.0", "2130706433", "0177.0.0.1", "0x7f.1", "127.1", "::ffff:127.0.0.1", "::ffff:7f00:1"]) ok(hostDataFinding(` ${bad} `), `parsed scan catches ${bad}`);
  for (const fine of ["8.8.8.8", "0x1234", "0.5", "2.0.0-rc1", "::ffff:8.8.8.8"]) ok(!hostDataFinding(` ${fine} `), `parsed scan passes ${fine}`);
}
console.log(`ok R5 lockstep hardening (${AZOS ? "azos" : "azinterface"}): ${n} checks`);
