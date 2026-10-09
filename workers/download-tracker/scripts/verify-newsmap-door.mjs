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
assert.deepEqual(Object.values(NEWSMAP_OPS).map((s) => s.op).sort(), ["lattice_tip", "library_pin", "news_feed", "news_globe", "news_ingest", "news_item", "news_open", "news_pin", "news_pin_open", "news_pins", "news_receipts", "news_sky", "news_sources", "news_status", "news_verify", "news_weather", "plot"]);
assert.deepEqual([...new Set(Object.values(NEWSMAP_OPS).map((s) => s.path))].sort(), ["4dmap-standalone", "aznews-live", "aznews-standalone", "joined"]);

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

// A runtime claim alone is not relayed: the door's own round trip fails here (no stored item), so flags stay false.
env = { AZIEL_RUNTIME: fakeRuntime({ ok: true, op: "news_pin", live: true, joined: true, merged: false, source_present: true, outlets_live: 1 }) };
out = await handleNewsmap(req("/v1/newsmap/pin", "POST", { item: { url: "https://example.org/a" } }), new URL("https://h.example/v1/newsmap/pin"), env, HOST);
assert.equal(calls.at(-2).body.op, "news_pin");
assert.deepEqual(calls.at(-2).body.payload, { item: { url: "https://example.org/a" }, dry_run: true });
assert.deepEqual(calls.at(-1).body.payload, { dry_run: true });
assert.equal(out.body.live, false);
assert.equal(out.body.joined, false);
assert.equal(out.body.merged, false);
assert.equal(out.body.runtime_claims.joined, true);
assert.equal(out.body.door_join_check.ok, false);
assert.equal(out.body.installed, false);

// The door's own round trip (news_pin -> news_open -> same item) passes: joined shows; merged needs lattice_live too.
{
  const store = (b) => {
    if (b.op === "news_status") return { ok: true, live: true, joined: true, merged: true, lattice_live: true, outlets_live: 30 };
    if (b.op === "news_pin") return { ok: true, item: { item_id: "n-1" }, pins: [{ pin_id: "pin-2" }, { pin_id: "pin-3" }], pull_receipt_seq: 4 };
    if (b.op === "news_open") return { ok: true, linked: b.payload.pin_id === "pin-2", item: { item_id: "n-1" } };
    return { ok: true };
  };
  env = { AZIEL_RUNTIME: fakeRuntime(store) };
  out = await handleNewsmap(req("/v1/newsmap"), new URL("https://h.example/v1/newsmap"), env, HOST);
  assert.equal(calls.at(-1).body.op, "news_open");
  assert.equal(calls.at(-1).body.payload.dry_run, true);
  assert.equal(out.body.door_join_check.ok, true);
  assert.equal(out.body.joined, true);
  assert.equal(out.body.merged, true);
  assert.equal(out.body.live, true);
  assert.equal(out.body.installed, false);
  // A pin that opens a different item fails the door check.
  env = { AZIEL_RUNTIME: fakeRuntime((b) => (b.op === "news_open" ? { ok: true, linked: true, item: { item_id: "n-9" } } : store(b))) };
  out = await handleNewsmap(req("/v1/newsmap"), new URL("https://h.example/v1/newsmap"), env, HOST);
  assert.equal(out.body.joined, false);
  assert.equal(out.body.merged, false);
  assert.match(out.body.join_reason, /different item/);
}

// AZNews standalone and 4DMap standalone paths.
env = { AZIEL_RUNTIME: fakeRuntime((b) => ({ ok: true, op: b.op })) };
for (const [path, op, kind] of [["/v1/aznews", "news_sources", "aznews-standalone"]]) {
  out = await handleNewsmap(req(path), new URL("https://h.example" + path), env, HOST);
  assert.equal(calls.at(-1).body.op, op);
  assert.equal(out.body.path, kind);
  assert.equal(out.body.ok, true);
  assert.equal(out.body.live, false);
}
{
  // GET /v1/map is 4DMap on its own; with no local copy registered it reads the runtime 4DMap store.
  const seen = [];
  const rt = { fetch: async (r) => { seen.push(r.url); return new Response(JSON.stringify({ ok: true, spec: "4DMAP-STORE-1.0", pins: [] })); } };
  const m = await handleNewsmap(req("/v1/map"), new URL("https://h.example/v1/map"), { AZIEL_RUNTIME: rt }, HOST);
  assert.match(seen[0], /\/v1\/4dmap\/pins\?layers=corpus%2Creference$/);
  assert.equal(m.body.source, "runtime");
  assert.equal(m.body.standalone, false);
  assert.equal(m.body.live, false);
}
for (const [key, spec] of Object.entries(NEWSMAP_OPS)) {
  out = await handleNewsmap(req("/v1/newsmap/" + key, "POST", {}), new URL("https://h.example/v1/newsmap/" + key), env, HOST);
  assert.equal(calls.at(-1).body.op, spec.op, key);
  assert.equal(out.body.path, spec.path);
}

// AZNews live store paths (runtime AzNewsStore through the same door).
for (const [path, op] of [["/v1/newsmap/feed", "news_feed"], ["/v1/newsmap/sky", "news_sky"], ["/v1/newsmap/pins", "news_pins"], ["/v1/newsmap/globe", "news_globe"], ["/v1/newsmap/verify", "news_verify"], ["/v1/newsmap/receipts", "news_receipts"]]) {
  out = await handleNewsmap(req(path + "?limit=500"), new URL("https://h.example" + path + "?limit=500"), env, HOST);
  assert.equal(calls.at(-1).body.op, op, path);
  assert.equal(calls.at(-1).body.payload.limit, 200, "limit is capped");
  assert.equal(out.body.path, "aznews-live");
  assert.match(out.body.globe_url, /\/aznews$/);
  assert.equal(out.body.installed, false);
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
  // /v1/map with no copy bound here reads GET /v1/4dmap/pins on the runtime (no JSON body).
  const e = path === "/v1/map" ? { ...env, AZIEL_RUNTIME: { fetch: async () => new Response(JSON.stringify({ ok: true, pins: [] })) } } : env;
  const res = await worker.fetch(req(path), e, { waitUntil() {} });
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
