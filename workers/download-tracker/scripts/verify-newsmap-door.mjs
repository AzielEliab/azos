/**
 * Prove the hosted AZNews / 4DMap paths (joined, AZNews standalone, 4DMap standalone)
 * go through the runtime FragGate door, pass flags through, and never raise them.
 */
import assert from "node:assert/strict";
import { handleNewsmap, newsmapView, NEWSMAP_OPS } from "../src/newsmap-door.js";
import worker from "../src/index.js";

const HOST = "azos";
const calls = [];
function fakeRuntime(result, { outerOk = true, status = 200, throws = false } = {}) {
  return {
    fetch: async (req) => {
      if (throws) throw new Error("down");
      const body = await req.json();
      calls.push({ url: req.url, method: req.method, body });
      return new Response(JSON.stringify({ ok: outerOk, code: "FG-OK", slug: "4dmap", op: body.op, result: typeof result === "function" ? result(body) : result }), { status });
    },
  };
}
const absent = { ok: true, op: "news_status", refused_source: true, code: "AZNEWS-SOURCE-ABSENT", outlets: 50, outlets_live: 0, live: false, merged: false };
const req = (path, method = "GET", body) =>
  new Request("https://h.example" + path, { method, body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body), headers: { "content-type": "application/json" } });

// Every op name the Worker exposes maps to a runtime 4dmap op.
assert.deepEqual(Object.values(NEWSMAP_OPS).map((s) => s.op).sort(), ["lattice_tip", "library_pin", "news_ingest", "news_open", "news_pin", "news_sources", "news_status", "news_weather", "plot"]);
assert.deepEqual([...new Set(Object.values(NEWSMAP_OPS).map((s) => s.path))].sort(), ["4dmap-standalone", "aznews-standalone", "joined"]);

// Joined status: live runtime shape today (source absent) stays refused, not live, not merged.
let env = { AZIEL_RUNTIME: fakeRuntime(absent) };
let out = await handleNewsmap(req("/v1/newsmap"), new URL("https://h.example/v1/newsmap"), env, HOST);
assert.equal(out.status, 200);
assert.equal(calls.at(-1).body.name, "4dmap");
assert.equal(calls.at(-1).body.op, "news_status");
assert.ok(calls.at(-1).url.endsWith("/v1/fraggate/call"));
assert.equal(out.body.path, "joined");
assert.equal(out.body.code, "AZNEWS-SOURCE-ABSENT");
assert.equal(out.body.refused, true);
assert.equal(out.body.live, false);
assert.equal(out.body.merged, false);
assert.equal(out.body.joined, false);
assert.equal(out.body.outlets_live, 0);
assert.equal(out.body.installed, false);
assert.equal(out.body.engine_installed, false);
assert.equal(out.body.second_map, false);
assert.equal(out.body.second_door, false);
assert.equal(out.body.host, HOST);

// A runtime that claims live while refusing still reads as not live here.
env = { AZIEL_RUNTIME: fakeRuntime({ ok: false, code: "AZNEWS-SOURCE-ABSENT", live: true, merged: true, joined: true }) };
out = await handleNewsmap(req("/v1/newsmap"), new URL("https://h.example/v1/newsmap"), env, HOST);
assert.equal(out.body.live, false);
assert.equal(out.body.merged, false);
assert.equal(out.body.joined, false);

// Pass-through only: a runtime that reports a landed pin is shown as live, never more.
env = { AZIEL_RUNTIME: fakeRuntime({ ok: true, op: "news_pin", live: true, joined: true, merged: false, source_present: true, outlets_live: 1 }) };
out = await handleNewsmap(req("/v1/newsmap/pin", "POST", { item: { url: "https://example.org/a" } }), new URL("https://h.example/v1/newsmap/pin"), env, HOST);
assert.equal(calls.at(-1).body.op, "news_pin");
assert.deepEqual(calls.at(-1).body.payload, { item: { url: "https://example.org/a" } });
assert.equal(out.body.live, true);
assert.equal(out.body.joined, true);
assert.equal(out.body.merged, false);
assert.equal(out.body.installed, false);

// AZNews standalone and 4DMap standalone paths.
env = { AZIEL_RUNTIME: fakeRuntime((b) => ({ ok: true, op: b.op })) };
for (const [path, op, kind] of [["/v1/aznews", "news_sources", "aznews-standalone"], ["/v1/map", "plot", "4dmap-standalone"]]) {
  out = await handleNewsmap(req(path), new URL("https://h.example" + path), env, HOST);
  assert.equal(calls.at(-1).body.op, op);
  assert.equal(out.body.path, kind);
  assert.equal(out.body.ok, true);
  assert.equal(out.body.live, false);
}
for (const [key, spec] of Object.entries(NEWSMAP_OPS)) {
  out = await handleNewsmap(req("/v1/newsmap/" + key, "POST", {}), new URL("https://h.example/v1/newsmap/" + key), env, HOST);
  assert.equal(calls.at(-1).body.op, spec.op, key);
  assert.equal(out.body.path, spec.path);
}

// Refusals made here.
out = await handleNewsmap(req("/v1/newsmap/delete_all", "POST", {}), new URL("https://h.example/v1/newsmap/delete_all"), env, HOST);
assert.equal(out.status, 404);
assert.equal(out.body.code, "NEWSMAP-UNKNOWN-OP");
out = await handleNewsmap(req("/v1/newsmap/pin", "POST", "{bad"), new URL("https://h.example/v1/newsmap/pin"), env, HOST);
assert.equal(out.status, 400);
assert.equal(out.body.code, "NEWSMAP-BAD-JSON");
assert.equal(await handleNewsmap(req("/v1/other"), new URL("https://h.example/v1/other"), env, HOST), null);

// Runtime down: refused, nothing live.
env = { AZIEL_RUNTIME: fakeRuntime(null, { throws: true }) };
out = await handleNewsmap(req("/v1/newsmap"), new URL("https://h.example/v1/newsmap"), env, HOST);
assert.equal(out.body.code, "NEWSMAP-RUNTIME-UNREACHABLE");
assert.equal(out.body.ok, false);
assert.equal(out.body.live, false);

// newsmapView never raises install flags.
const v = newsmapView(HOST, "plot", { status: 200, body: { ok: true, result: { ok: true, installed: true, engine_installed: true } } });
assert.equal(v.installed, false);
assert.equal(v.engine_installed, false);

// Through the Worker entry point.
env = { AZIEL_RUNTIME: fakeRuntime(absent), AZIEL_RUNTIME_ORIGIN: "https://aziel-runtime.vibelock.workers.dev" };
for (const path of ["/v1/newsmap", "/v1/aznews", "/v1/map"]) {
  const res = await worker.fetch(req(path), env, { waitUntil() {} });
  assert.equal(res.status, 200, path);
  const body = await res.json();
  assert.equal(body.host, HOST);
  assert.equal(body.installed, false);
  assert.equal(body.second_map, false);
}
const res = await worker.fetch(req("/v1/newsmap/pin", "POST", {}), env, { waitUntil() {} });
assert.equal(res.status, 200);
assert.equal(calls.at(-1).body.op, "news_pin");

console.log("NEWSMAP-DOOR-OK", HOST, calls.length, "runtime calls");
