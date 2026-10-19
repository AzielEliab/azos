/**
 * AZ-LOCKSTEP-1.0 union proxy (AZBot review of #44 / #39): the runtime proxy times out (~4 s) with
 * 503 LEG-RUNTIME-TIMEOUT standalone:true and aborts the upstream request; the caller's CF-Connecting-IP
 * goes to the runtime as X-Azrt-Client-IP (and CF-Connecting-IP itself is never forwarded); AZ-OS caps
 * POST bodies at 256 KB from Content-Length first, then aborts the stream; union refusals carry a peer
 * refusal receipt, and when the runtime is down that seal never delays the response. Author: Aziel Eliab.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("..", import.meta.url));
const LEG = /name\s*=\s*"azos-/.test(readFileSync(root + "wrangler.toml", "utf8")) ? "azos" : "azinterface";
const worker = (await import(root + "src/" + (LEG === "azos" ? "index.js" : "entry.js"))).default;
globalThis.fetch = async () => { throw new Error("network off in test"); };
const KV = { get: async () => null, put: async () => {}, list: async () => ({ keys: [], list_complete: true }), delete: async () => {} };
const base = { DOWNLOADS: KV, ASSETS: { fetch: async () => new Response("a") } };
const waits = [];
const ctx = { waitUntil(p) { waits.push(p); } };
let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };
const call = (path, env, init = {}) => worker.fetch(new Request("https://leg.example" + path, init), env, ctx);
const READ = "/v1/memory";

// 1. a runtime that never answers: 503 LEG-RUNTIME-TIMEOUT within the default 4 s, upstream aborted
{
  let seen = null;
  const hung = { fetch: (req) => { if (new URL(req.url).hostname === "peer.aziel.internal") return new Promise(() => {}); seen = req; return new Promise(() => {}); } };
  const t0 = Date.now();
  const r = await call(READ, { ...base, AZIEL_RUNTIME: hung });
  const ms = Date.now() - t0;
  const b = await r.json();
  ok(r.status === 503 && b.code === "LEG-RUNTIME-TIMEOUT" && b.standalone === true && b.ok === false && b.live === false, `timeout body ${JSON.stringify(b).slice(0, 120)}`);
  ok(ms >= 3900 && ms < 4600, `default timeout ~4 s (took ${ms} ms)`);
  ok(seen && seen.signal && seen.signal.aborted === true, "upstream request aborted");
  ok(b.refusal_receipt && b.refusal_receipt.sealed === false && b.refusal_receipt.status === "receipt_pending", "seal deferred to the background, response not delayed");
  const t1 = Date.now();
  const r2 = await call(READ, { ...base, AZIEL_RUNTIME: hung, LEG_RUNTIME_TIMEOUT_MS: "300" });
  ok(r2.status === 503 && Date.now() - t1 < 800, "LEG_RUNTIME_TIMEOUT_MS=300 honored");
}

// 2. caller IP forwarded as X-Azrt-Client-IP only
{
  const got = [];
  const echo = { fetch: async (req) => { got.push(req); return new Response("{}", { status: 200, headers: { "content-type": "application/json" } }); } };
  await call(READ, { ...base, AZIEL_RUNTIME: echo }, { headers: { "CF-Connecting-IP": "203.0.113.7", "X-Forwarded-For": "1.1.1.1", "X-Azrt-Client-IP": "9.9.9.9" } });
  ok(got[0].headers.get("X-Azrt-Client-IP") === "203.0.113.7", "X-Azrt-Client-IP from CF-Connecting-IP (caller's own header overwritten)");
  ok(!got[0].headers.has("CF-Connecting-IP") && !got[0].headers.has("X-Forwarded-For"), "CF-Connecting-IP / XFF not forwarded");
  await call(READ, { ...base, AZIEL_RUNTIME: echo }, { headers: { "X-Azrt-Client-IP": "9.9.9.9" } });
  ok(!got[1].headers.has("X-Azrt-Client-IP"), "no CF-Connecting-IP: no client header (a caller cannot pick one)");
}

// 3. AZ-OS body cap: Content-Length first, then streamed early abort
if (LEG === "azos") {
  const echo = { fetch: async () => new Response("{}", { status: 200 }) };
  let pulled = 0;
  const neverRead = new ReadableStream({ pull() { pulled++; throw new Error("body must not be read"); } }, { highWaterMark: 0 });
  let r = await call("/v1/fraggate/call", { ...base, AZIEL_RUNTIME: echo }, { method: "POST", headers: { "content-type": "application/json", "content-length": "300000" }, body: neverRead, duplex: "half" });
  const rb = await r.json();
  ok(r.status === 413 && rb.code === "LEG-BODY-TOO-LARGE" && pulled === 0, `Content-Length over cap -> 413 without reading (status ${r.status}, pulled ${pulled})`);
  let chunks = 0, cancelled = false;
  const big = new ReadableStream({ pull(c) { chunks++; c.enqueue(new Uint8Array(65536)); if (chunks > 160) c.close(); }, cancel() { cancelled = true; } });
  r = await call("/v1/fraggate/call", { ...base, AZIEL_RUNTIME: echo }, { method: "POST", headers: { "content-type": "application/json" }, body: big, duplex: "half" });
  ok(r.status === 413 && cancelled && chunks <= 6, `chunked over cap -> 413, stream cancelled after ${chunks} chunks`);
  const small = JSON.stringify({ slug: "azos", op: "status" });
  const got = [];
  r = await call("/v1/fraggate/call", { ...base, AZIEL_RUNTIME: { fetch: async (req) => { got.push(await req.text()); return new Response("{}", { status: 200 }); } } }, { method: "POST", headers: { "content-type": "application/json" }, body: small });
  ok(r.status === 200 && got[0] === small, "small body forwarded byte for byte");
}

// 4. union refusals are sealed through the peer refusal wrapper
{
  const peer = { fetch: async (req) => (new URL(req.url).hostname === "peer.aziel.internal" ? Response.json({ refusal_receipt: { kind: "refusal", sealed: true, chain: "refusals", seq: 7, h: "a".repeat(64) } }) : new Response("{}", { status: 500 })) };
  const path = LEG === "azos" ? "/v1/fraggate/call" : "/v1/status";
  const init = LEG === "azos" ? { method: "POST", headers: { "content-length": "999999" }, body: "x" } : {};
  const r = await call(path, { ...base, AZIEL_RUNTIME: peer }, init);
  const b = await r.json();
  ok(r.status >= 400 && b.refusal_receipt && b.refusal_receipt.sealed === true && r.headers.get("X-Azrt-Refusal-Receipt").startsWith("sealed"), `${path} refusal sealed`);
  if (LEG === "azinterface") {
    const l = await (await call("/v1/lattice", { ...base, AZIEL_RUNTIME: peer }, { method: "POST", body: "{}" })).json();
    ok(l.code === "LATTICE-WRITE-NOT-ON-THIS-LEG" && l.refusal_receipt && l.refusal_receipt.sealed === true, "403 lattice refusal sealed");
  }
  const a = await (await call(READ, base)).json();
  ok(a.code === "LEG-RUNTIME-ABSENT" && a.refusal_receipt && a.refusal_receipt.sealed === false, "absent binding: refusal stands, receipt unavailable");
}
await Promise.allSettled(waits.splice(0).map((p) => Promise.race([p, new Promise((r) => setTimeout(r, 10))])));
console.log(`ok ${LEG} union proxy: ${n} checks`);
process.exit(0);
