/**
 * Standalone 4DMap on this host: its own verified copy of the runtime 4DMap store
 * (AZRT-MAP-COPY-1.0, chain "4dmap", own Durable Object). GET /v1/map serves map pins
 * from it with no AZNews; ?layers=news adds the AZNews copy's pins. Tamper tests and
 * runtime-unreachable tests. No network.
 */
import assert from "node:assert/strict";
import { canonicalize, sha256Hex, primaryOf, onlineSecondaryOf, GENESIS } from "../src/tether.js";
import { memCopyRepo, copyIngest, copyRead, localMapRead, MAP_TETHER_SPEC, MAP_TETHER_KIND, NEWS_TETHER_SPEC, NEWS_TETHER_KIND, COPY_DO_NAME, MAP_COPY_DO_NAME } from "../src/news-copy.js";
import { handleNewsmap, registerLocalCopy } from "../src/newsmap-door.js";

const b64u = (bytes) => Buffer.from(bytes).toString("base64url");
const pair = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
const pub = b64u(new Uint8Array(await crypto.subtle.exportKey("raw", pair.publicKey)));
const other = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
async function sign(packet, priv = pair.privateKey) {
  const { sig: _s, ...unsigned } = packet;
  return { ...packet, sig: b64u(new Uint8Array(await crypto.subtle.sign("Ed25519", priv, new TextEncoder().encode(canonicalize(unsigned))))) };
}
function chainLedger() {
  const rows = [];
  let tip = { primary: GENESIS, secondary: GENESIS };
  return {
    rows,
    async add(kind, doc) {
      const document_hash = await sha256Hex(canonicalize(doc));
      const primary = await primaryOf(document_hash, tip.primary);
      const secondary = await onlineSecondaryOf(primary, tip.secondary);
      rows.push({ seq: rows.length + 1, kind, at: new Date(Date.UTC(2026, 9, 9, 7, rows.length)).toISOString(), doc, lattice: { document_hash, primary, primary_prev: tip.primary, secondary, secondary_prev: tip.secondary, offline: false, username: null } });
      tip = { primary, secondary };
    },
  };
}
const pinDoc = (layer, pin_type, source_id, event, lat, lon, extra = {}) => ({ kind: "4dmap-pin", spec: "4DMAP-STORE-1.0", layer, pin_type, color: "grey", color_hex: "#9e9e9e", event, date: null, geo: { name: event, lat, lon }, source: { test: true }, source_id, ...extra });

const map = chainLedger();
await map.add("map_pin", pinDoc("reference", "reference-capital", "ref:capital:FR", "Paris, capital of France", 48.85, 2.35));
await map.add("map_pin", pinDoc("reference", "reference-capital", "ref:capital:JP", "Tokyo, capital of Japan", 35.68, 139.69));
await map.add("map_pin", pinDoc("corpus", "library-aziel-event", "corpus:AZEVT-1", "Event one", 10, 20, { date: "1101" }));
await map.add("map_pin", pinDoc("corpus", "corpus-event", "corpus:AZEVT-2", "Event two", -5, 30));
await map.add("map_pin", pinDoc("corpus", "library-aziel-event", "corpus:AZEVT-1", "Event one (confirmed)", 10, 20, { supersedes_seq: 3 }));
const news = chainLedger();
await news.add("news", { item_id: "n-1", title: "Fire in Lagos", outlet: { id: "x", name: "X" } });
await news.add("pin", { pin_type: "news-report", color: "blue", color_hex: "#1e88e5", role: "report", event: "Fire", geo: { name: "Lagos", lat: 6.45, lon: 3.39 }, report_seq: 1, report_document_hash: news.rows[0].lattice.document_hash, pull_receipt_seq: 3 });
await news.add("pull_receipt", { report_seq: 1, document_hash: news.rows[0].lattice.document_hash });

function packetOf(ledger, chain, from, to, extra = {}) {
  const rows = ledger.rows.slice(from, to);
  const last = rows[rows.length - 1];
  const spec = chain === "4dmap" ? { spec: MAP_TETHER_SPEC, kind: MAP_TETHER_KIND } : { spec: NEWS_TETHER_SPEC, kind: NEWS_TETHER_KIND };
  return sign({ ...spec, chain, after_seq: from, rows, tips: { primary: last.lattice.primary, secondary: last.lattice.secondary, seq: last.seq }, public_key: pub, ...extra });
}

// ---- ingest refusals (tamper) ----
const mrepo = memCopyRepo();
const ing = (repo, p, chain = "4dmap") => copyIngest(repo, p, { pinned: pub, chain });
assert.equal((await ing(mrepo, await packetOf(news, "aznews", 0, 3))).body.code, "NEWS-COPY-SPEC", "an AZNews packet is refused by the 4DMap copy");
{
  const p = await packetOf(map, "4dmap", 0, 3);
  assert.equal((await ing(mrepo, await sign({ ...p, sig: undefined }, other.privateKey))).body.code, "NEWS-COPY-SIG", "foreign key");
  const q = JSON.parse(JSON.stringify(p));
  q.rows[1].doc.geo.lat = 0;
  assert.equal((await ing(mrepo, q)).body.code, "NEWS-COPY-SIG", "pin moved after signing");
  const rows = JSON.parse(JSON.stringify(map.rows.slice(0, 3)));
  rows[2].doc.event = "re-signed edit";
  const r = await sign({ spec: MAP_TETHER_SPEC, kind: MAP_TETHER_KIND, chain: "4dmap", after_seq: 0, rows, tips: { primary: rows[2].lattice.primary, secondary: rows[2].lattice.secondary, seq: 3 }, public_key: pub });
  assert.equal((await ing(mrepo, r)).body.code, "NEWS-COPY-HASH", "signed but the document does not match its hash");
  assert.equal((await ing(mrepo, await packetOf(map, "4dmap", 2, 5))).body.code, "NEWS-COPY-LINK", "first contact starts at genesis");
}
assert.equal((await copyRead(mrepo, "map", {})).code, "NEWS-COPY-EMPTY");
// ---- ingest from genesis ----
assert.equal((await ing(mrepo, await packetOf(map, "4dmap", 0, 3))).body.ok, true);
assert.equal((await ing(mrepo, await packetOf(map, "4dmap", 3, 5))).body.ok, true);
assert.equal((await ing(mrepo, await packetOf(map, "4dmap", 3, 5))).body.code, "NEWS-COPY-LINK", "replay refused");
{
  // A copy that holds one chain refuses the other chain's packets, even when signed.
  const nrepo2 = memCopyRepo();
  await ing(nrepo2, await packetOf(news, "aznews", 0, 3), "aznews");
  const p = await packetOf(map, "4dmap", 3, 5);
  assert.equal((await ing(nrepo2, { ...p }, "4dmap")).body.code, "NEWS-COPY-CHAIN");
}
const r = await copyRead(mrepo, "map", {});
assert.equal(r.ok, true);
assert.equal(r.standalone, true);
assert.equal(r.needs_aznews, false);
assert.equal(r.pins.length, 4, "newest row per source id");
assert.equal(r.pins.find((p) => p.source_id === "corpus:AZEVT-1").event, "Event one (confirmed)");
assert.deepEqual(r.layer_counts, { corpus: 2, reference: 2 });
assert.equal((await copyRead(mrepo, "map", { layers: "corpus" })).pins.length, 2);
assert.equal(r.last10.every((p) => p.layer === "corpus"), true);
assert.equal(r.joined, false);
assert.equal((await copyRead(mrepo, "feed", {})).ok, true, "news ops on the 4dmap copy return nothing, not an error");
// Retraction (append-only) and links on the copy.
{
  const m2 = chainLedger();
  await m2.add("map_pin", pinDoc("corpus", "library-aziel-event", "corpus:J1", "HVAC Valve guide", 78.2, 15.6));
  await m2.add("map_pin", pinDoc("corpus", "corpus-event", "corpus:R1", "Rosetta", 31.4, 30.417));
  await m2.add("map_pin", { ...pinDoc("corpus", "library-aziel-event", "corpus:J1", "HVAC Valve guide", 78.2, 15.6), supersedes_seq: 1, retracted: "geoparser_junk", retract_reason: "bare coordinate pair" });
  await m2.add("map_link", { kind: "4dmap-link", spec: "4DMAP-LINK-1.0", link_type: "correspondence", level: "black", news: { item_id: "n-1" }, map: { pin_seq: 2, source_id: "corpus:R1" }, match: { shared: ["rosetta", "stone", "ankara"] } });
  const rr = memCopyRepo();
  assert.equal((await ing(rr, await packetOf(m2, "4dmap", 0, 4))).body.ok, true);
  const v = await copyRead(rr, "map", {});
  assert.equal(v.standalone, true);
  assert.equal(v.pins.length, 1, "retracted pin hidden by default");
  assert.equal(v.retracted.count, 1);
  assert.equal(v.layer_counts.corpus, 1);
  const vr = await copyRead(rr, "map", { include_retracted: "1" });
  assert.equal(vr.pins.find((p) => p.source_id === "corpus:J1").retracted, "geoparser_junk");
  assert.equal((await rr.get(1)).doc.event, "HVAC Valve guide", "the original row is kept");
  const vl = await copyRead(rr, "map", { links: "1" });
  assert.equal(vl.links.length, 1);
  assert.equal(vl.links[0].level, "black");
  // Tampering with the retraction row (un-retracting it in storage) is caught.
  (await rr.get(3)).doc.retracted = null;
  assert.equal((await copyRead(rr, "map", {})).standalone, false);
}
console.log("ok 4dmap copy: refusals, genesis start, newest-per-source, layers, retractions, links");

// ---- door: fake Durable Object namespace holding the two copies ----
const nrepo = memCopyRepo();
const repos = { [MAP_COPY_DO_NAME]: mrepo, [COPY_DO_NAME]: nrepo };
const ns = { getByName: (name) => ({ fetch: async (req) => { const b = await req.json(); const out = b.op === "ingest" ? await copyIngest(repos[name], b.packet, { pinned: pub, chain: b.chain }) : { status: 200, body: await copyRead(repos[name], b.op, b.payload || {}, { host: "azos" }) }; return new Response(JSON.stringify(out.body), { status: out.status }); } }) };
const reqOf = (path) => [new Request("https://h.example" + path), new URL("https://h.example" + path)];
const { newsCopyCall } = await import("../src/news-copy.js");
registerLocalCopy(async (env, op, payload) => (op === "map" ? localMapRead(env, payload) : (await newsCopyCall(env, { op, payload })).body));
let runtimeCalls = 0;
const down = { AZOS_NEWS_COPY: ns, AZIEL_RUNTIME: { fetch: async () => { runtimeCalls += 1; throw new Error("runtime unreachable"); } } };
const rtPins = { ok: true, spec: "4DMAP-STORE-1.0", pins: [{ pin_id: "map-9", layer: "corpus" }], layers: { corpus: { count: 1 } } };
const up = { AZOS_NEWS_COPY: ns, AZIEL_RUNTIME: { fetch: async (req) => { runtimeCalls += 1; const u = new URL(req.url); if (u.pathname === "/v1/4dmap/pins") return new Response(JSON.stringify(rtPins)); return new Response(JSON.stringify({ ok: true, result: { ok: true, pins: [{ pin_id: "pin-1" }] } })); } } };

// Runtime down, AZNews copy EMPTY: 4DMap still serves on its own.
let o = await handleNewsmap(...reqOf("/v1/map"), down, "azos");
assert.equal(o.status, 200);
assert.equal(o.body.standalone, true);
assert.equal(o.body.source, "azos-local-copy");
assert.equal(o.body.pins.length, 4);
assert.equal(o.body.needs_aznews, false);
assert.equal(o.body.live, false);
assert.equal(o.body.receipts_minted, 0);
assert.equal(runtimeCalls, 0, "the default /v1/map read does not call the runtime");
o = await handleNewsmap(...reqOf("/v1/map?layers=corpus,reference,news"), down, "azos");
assert.equal(o.body.standalone, true, "news layer unavailable is reported, map layers still served and verified");
assert.equal(o.body.layer_report.news.code, "NEWS-COPY-EMPTY");
assert.equal(o.body.pins.length, 4);
// AZNews copy filled: ?layers=news adds its pins.
await copyIngest(nrepo, await packetOf(news, "aznews", 0, 3), { pinned: pub, chain: "aznews" });
o = await handleNewsmap(...reqOf("/v1/map?layers=corpus,reference,news"), down, "azos");
assert.equal(o.body.pins.length, 5);
assert.equal(o.body.pins.filter((p) => p.layer === "news").length, 1);
assert.equal(o.body.standalone, true);
o = await handleNewsmap(...reqOf("/v1/map?layers=news"), down, "azos");
assert.equal(o.body.pins.length, 1);
assert.equal(o.body.layer_report.corpus, "not asked");
// Tampered map copy in storage: not served; falls back to the runtime; runtime down -> 503 refusal.
const row = await mrepo.get(4);
row.doc.geo.lat = 55;
o = await handleNewsmap(...reqOf("/v1/map"), down, "azos");
assert.equal(o.status, 503);
assert.equal(o.body.code, "NEWSMAP-MAP-UNAVAILABLE");
assert.equal(o.body.local_copy.code, "NEWS-COPY-VERIFY-FAILED");
assert.equal(o.body.standalone, false);
o = await handleNewsmap(...reqOf("/v1/map?source=local"), down, "azos");
assert.equal(o.body.code, "NEWS-COPY-VERIFY-FAILED");
runtimeCalls = 0;
o = await handleNewsmap(...reqOf("/v1/map"), up, "azos");
assert.equal(o.body.source, "runtime");
assert.equal(o.body.standalone, false);
assert.equal(o.body.local_copy.code, "NEWS-COPY-VERIFY-FAILED");
row.doc.geo.lat = -5;
// Tampered news copy: the news layer is not served, map layers are.
const nrow = await nrepo.get(2);
nrow.doc.event = "edited";
o = await handleNewsmap(...reqOf("/v1/map?layers=corpus,reference,news"), down, "azos");
assert.equal(o.body.standalone, true);
assert.equal(o.body.layer_report.news.code, "NEWS-COPY-VERIFY-FAILED");
assert.equal(o.body.pins.some((p) => p.layer === "news"), false);
nrow.doc.event = "Fire";
// ?source=runtime reads the runtime store.
runtimeCalls = 0;
o = await handleNewsmap(...reqOf("/v1/map?source=runtime"), up, "azos");
assert.equal(o.body.source, "runtime");
assert.equal(o.body.pins.length, 1);
assert.equal(runtimeCalls, 1);
// Empty 4DMap copy + runtime up: runtime; empty + runtime down: refusal.
const emptyNs = { getByName: () => ({ fetch: async (req) => { const b = await req.json(); return new Response(JSON.stringify(await copyRead(memCopyRepo(), b.op, b.payload || {}))); } }) };
o = await handleNewsmap(...reqOf("/v1/map"), { ...up, AZOS_NEWS_COPY: emptyNs }, "azos");
assert.equal(o.body.source, "runtime");
assert.equal(o.body.local_copy.code, "NEWS-COPY-EMPTY");
o = await handleNewsmap(...reqOf("/v1/map"), { ...down, AZOS_NEWS_COPY: emptyNs }, "azos");
assert.equal(o.status, 503);
// AZInterface host label and binding name.
o = await handleNewsmap(...reqOf("/v1/map"), { LOCAL_NEWS_COPY: ns, COPY_HOST: "azinterface", AZIEL_RUNTIME: down.AZIEL_RUNTIME }, "azinterface");
assert.equal(o.body.source, "azinterface-local-copy");
assert.equal(o.body.standalone, true);
registerLocalCopy(null);
console.log("ok /v1/map: standalone without AZNews, layers=news optional, tamper and runtime-unreachable");
console.log("MAP-COPY-OK");
