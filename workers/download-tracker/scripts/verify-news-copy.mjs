/**
 * AZOS-NEWS-COPY-1.0: AZ-OS keeps its own verified copy of the runtime AZNews store.
 * Signed packets in order from genesis are checked (key, signature, document hashes,
 * both links, tips) before anything is kept; reads re-verify against the stored signed
 * tip; the newsmap door serves from the copy, standalone:true, when the runtime is
 * unreachable; public reads forward dry_run unless they are a real look (?view=1).
 */
import assert from "node:assert/strict";
import { canonicalize, sha256Hex, primaryOf, onlineSecondaryOf, offlineSecondaryOf, GENESIS } from "../src/tether.js";
import { memCopyRepo, copyIngest, copyRead, copyState, checkNewsPacket, NEWS_TETHER_SPEC, NEWS_TETHER_KIND } from "../src/news-copy.js";
import { handleNewsmap, registerLocalCopy, LOOK_RULE } from "../src/newsmap-door.js";

const b64u = (bytes) => Buffer.from(bytes).toString("base64url");
const pair = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
const pub = b64u(new Uint8Array(await crypto.subtle.exportKey("raw", pair.publicKey)));
const other = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);

async function sign(packet, priv = pair.privateKey) {
  const { sig: _s, ...unsigned } = packet;
  const sig = new Uint8Array(await crypto.subtle.sign("Ed25519", priv, new TextEncoder().encode(canonicalize(unsigned))));
  return { ...packet, sig: b64u(sig) };
}

// A small runtime-shaped ledger: news item, two pins, pull receipt, sky, weather, offline view.
const ledger = [];
let tip = { primary: GENESIS, secondary: GENESIS };
async function add(kind, doc, offline = null) {
  const seq = ledger.length + 1;
  const document_hash = await sha256Hex(canonicalize(doc));
  const primary = await primaryOf(document_hash, tip.primary);
  const secondary = offline ? await offlineSecondaryOf(document_hash, offline) : await onlineSecondaryOf(primary, tip.secondary);
  const lattice = { document_hash, primary, primary_prev: tip.primary, secondary, secondary_prev: tip.secondary, offline: Boolean(offline), username: offline || null };
  ledger.push({ seq, kind, at: "2026-10-09T06:00:00.000Z", doc, lattice });
  tip = { primary, secondary };
  return seq;
}
for (let i = 0; i < 6; i++) {
  const item = await add("news", { item_id: "n-" + i, title: "Fire in Lagos " + i, outlet: { id: "x", name: "X" }, wording: "LAGOS — Fire " + i + ". Ünïcode “q”.", published: "2026-10-09T05:00:00Z", score: 0.5 });
  const rc = item + 3;
  const h = ledger[item - 1].lattice.document_hash;
  await add("pin", { pin_type: "news-report", color: "blue", color_hex: "#1e88e5", role: "report", event: "Fire " + i, geo: { name: "Lagos", lat: 6.45, lon: 3.39 }, report_seq: item, report_document_hash: h, pull_receipt_seq: rc, report_location_source: "dateline" });
  await add("pin", { pin_type: "news-event", color: "red", color_hex: "#e53935", role: "event", event: "Fire " + i, geo: null, report_seq: item, report_document_hash: h, pull_receipt_seq: rc });
  await add("pull_receipt", { report_seq: item, document_hash: h, padding: 1.25 });
}
await add("sky", { kind: "aznews-sky", spec: "AZNEWS-SKY-1.1", moon: { phase_name: "Waning Crescent", illuminated_percent: 2.18 } });
await add("weather", { anchor: { id: "lagos", name: "Lagos" }, reading: { temperature_c: 29.5 } });
await add("view_receipt", { report_seq: 1, viewer_basis: "hash" }, "vh-" + "a".repeat(32));

function packetOf(from, to, extra = {}) {
  const rows = ledger.slice(from, to);
  const last = rows[rows.length - 1];
  return sign({ spec: NEWS_TETHER_SPEC, kind: NEWS_TETHER_KIND, chain: "aznews", after_seq: from, rows, tips: { primary: last.lattice.primary, secondary: last.lattice.secondary, seq: last.seq }, store_tip: { seq: ledger.length }, public_key: pub, t: "2026-10-09T06:00:00Z", ...extra });
}

const repo = memCopyRepo();
// Refusals first: nothing is stored.
assert.equal((await copyIngest(repo, await packetOf(0, 5), { pinned: null })).body.code, "NEWS-COPY-KEY-UNPINNED");
assert.equal((await copyIngest(repo, await packetOf(0, 5), { pinned: "z".repeat(43) })).body.code, "NEWS-COPY-KEY-MISMATCH");
{
  const p = await packetOf(0, 5);
  const forged = await sign({ ...p, sig: undefined }, other.privateKey);
  assert.equal((await copyIngest(repo, forged, { pinned: pub })).body.code, "NEWS-COPY-SIG");
}
{
  const p = await packetOf(0, 5);
  p.rows = JSON.parse(JSON.stringify(p.rows));
  p.rows[0].doc.title = "edited after signing";
  assert.equal((await copyIngest(repo, p, { pinned: pub })).body.code, "NEWS-COPY-SIG");
}
{
  // Signed but internally wrong: a document that does not match its hash.
  const rows = JSON.parse(JSON.stringify(ledger.slice(0, 5)));
  rows[2].doc.event = "changed";
  const last = rows[4];
  const p = await sign({ spec: NEWS_TETHER_SPEC, kind: NEWS_TETHER_KIND, chain: "aznews", after_seq: 0, rows, tips: { primary: last.lattice.primary, secondary: last.lattice.secondary, seq: 5 }, public_key: pub });
  const out = await copyIngest(repo, p, { pinned: pub });
  assert.equal(out.body.code, "NEWS-COPY-HASH");
}
assert.equal((await copyIngest(repo, await packetOf(5, 10), { pinned: pub })).body.code, "NEWS-COPY-LINK", "first contact must start at genesis");
assert.equal((await copyState(repo, {})).tip_seq, 0, "nothing stored after refusals");
{
  const empty = await copyRead(repo, "feed", {});
  assert.equal(empty.standalone, false);
  assert.equal(empty.code, "NEWS-COPY-EMPTY");
}

// Good packets, in order from genesis.
let out = await copyIngest(repo, await packetOf(0, 10), { pinned: pub });
assert.equal(out.body.ok, true, JSON.stringify(out.body));
out = await copyIngest(repo, await packetOf(10, ledger.length), { pinned: pub });
assert.equal(out.body.ok, true, JSON.stringify(out.body));
assert.equal(out.body.tip_seq, ledger.length);
assert.equal((await copyIngest(repo, await packetOf(10, ledger.length), { pinned: pub })).body.code, "NEWS-COPY-LINK", "replay refused");

for (const op of ["status", "feed", "pins", "sky", "weather", "receipts", "globe", "verify", "plot"]) {
  const r = await copyRead(repo, op, {});
  assert.equal(r.ok, true, op);
  assert.equal(r.standalone, true, op);
  assert.equal(r.live, false, op);
  assert.equal(r.merged, false, op);
  assert.equal(r.mints_receipts, false);
  assert.equal(r.copy_verify.ok, true, op);
  assert.equal(r.copy.from_genesis, true);
}
const feed = await copyRead(repo, "feed", { limit: 3 });
assert.equal(feed.items.length, 3);
assert.equal(feed.items[0].item_id, "n-5");
const pins = await copyRead(repo, "pins", {});
assert.equal(pins.last10.length, 10);
assert.equal(pins.joined, true);
const opened = await copyRead(repo, "pin_open", { pin_id: pins.pins.find((p) => p.role === "report").pin_id });
assert.equal(opened.linked, true);
assert.equal(opened.item.item_id, "n-5");
console.log("ok news copy: refusals, genesis start, ingest, standalone reads");
{
  // A copy that ends right after an item, before its pins: that item is pending, not a failed join.
  const edge = memCopyRepo();
  assert.equal((await copyIngest(edge, await packetOf(0, 5), { pinned: pub })).body.ok, true);
  const r = await copyRead(edge, "status", {});
  assert.equal(r.join_check.linked, 1);
  assert.equal(r.join_check.pending_at_edge, 1);
  assert.equal(r.joined, true);
}

// A stored row changed afterwards: the read re-check catches it and standalone is false.
{
  const row = await repo.get(2);
  row.doc.event = "tampered in storage";
  const r = await copyRead(repo, "pins", {});
  assert.equal(r.standalone, false);
  assert.equal(r.joined, false);
  assert.match(r.copy_verify.reason, /document hash/);
  row.doc.event = "Fire 0";
  assert.equal((await copyRead(repo, "pins", {})).standalone, true);
}

// Door: runtime marked unreachable -> served from the copy, standalone:true; source=local too.
registerLocalCopy(async (_env, op, payload) => copyRead(repo, op, payload));
const req = (path, method = "GET", body) => new Request("https://h.example" + path, { method, body: body === undefined ? undefined : JSON.stringify(body), headers: { "content-type": "application/json" } });
const down = { AZIEL_RUNTIME: { fetch: async () => { throw new Error("runtime unreachable"); } } };
for (const [path, key] of [["/v1/aznews", "sources"], ["/v1/newsmap", "status"], ["/v1/newsmap/feed", "feed"], ["/v1/newsmap/pins", "pins"], ["/v1/newsmap/globe", "globe"], ["/v1/newsmap/sky", "sky"]]) {
  const o = await handleNewsmap(req(path), new URL("https://h.example" + path), down, "azos");
  assert.equal(o.body.standalone, true, path);
  assert.equal(o.body.source, "azos-local-copy", path);
  assert.equal(o.body.served_because, "the runtime was unreachable");
  assert.equal(o.body.live, false);
  assert.equal(o.body.merged, false);
  assert.equal(o.body.installed, false);
  assert.equal(o.body.receipts_minted, 0);
}
const down500 = { AZIEL_RUNTIME: { fetch: async () => new Response("bad gateway", { status: 502 }) } };
assert.equal((await handleNewsmap(req("/v1/newsmap/feed"), new URL("https://h.example/v1/newsmap/feed"), down500, "azos")).body.standalone, true);
const calls = [];
const up = { AZIEL_RUNTIME: { fetch: async (r) => { const b = await r.json(); calls.push(b); return new Response(JSON.stringify({ ok: true, result: { ok: true, op: b.op, items: [] } })); } } };
let o = await handleNewsmap(req("/v1/newsmap/feed?source=local"), new URL("https://h.example/v1/newsmap/feed?source=local"), up, "azos");
assert.equal(o.body.standalone, true);
assert.equal(calls.length, 0, "source=local does not call the runtime");
// Runtime up: served by the runtime, standalone false.
o = await handleNewsmap(req("/v1/newsmap/feed"), new URL("https://h.example/v1/newsmap/feed"), up, "azos");
assert.equal(o.body.standalone, false);
assert.equal(o.body.source, "runtime");
console.log("ok door: runtime unreachable -> own verified copy, standalone:true");

// Look rule: public reads forward dry_run; only ?view=1 (or POST view:true) is a look; ?dry_run=1 wins.
calls.length = 0;
await handleNewsmap(req("/v1/newsmap/feed?limit=20"), new URL("https://h.example/v1/newsmap/feed?limit=20"), up, "azos");
assert.equal(calls.at(-1).payload.dry_run, true);
assert.equal(calls.at(-1).payload.via, undefined);
await handleNewsmap(req("/v1/newsmap/globe?view=1"), new URL("https://h.example/v1/newsmap/globe?view=1"), up, "azos");
assert.equal(calls.at(-1).payload.dry_run, undefined);
assert.equal(calls.at(-1).payload.via, "azos");
await handleNewsmap(req("/v1/newsmap/globe?view=1&dry_run=1"), new URL("https://h.example/v1/newsmap/globe?view=1&dry_run=1"), up, "azos");
assert.equal(calls.at(-1).payload.dry_run, true);
await handleNewsmap(req("/v1/newsmap/pin_open", "POST", { pin_id: "pin-2" }), new URL("https://h.example/v1/newsmap/pin_open"), up, "azos");
assert.equal(calls.at(-1).payload.dry_run, true);
await handleNewsmap(req("/v1/newsmap/item", "POST", { item_id: "n-1", view: true }), new URL("https://h.example/v1/newsmap/item"), up, "azos");
assert.equal(calls.at(-1).payload.dry_run, undefined);
assert.equal(calls.at(-1).payload.view, undefined);
await handleNewsmap(req("/v1/aznews"), new URL("https://h.example/v1/aznews"), up, "azos");
assert.equal(calls.at(-1).payload.dry_run, true);
assert.match(LOOK_RULE, /view=1/);
registerLocalCopy(null);
o = await handleNewsmap(req("/v1/newsmap/feed?source=local"), new URL("https://h.example/v1/newsmap/feed?source=local"), up, "azinterface");
assert.equal(o.body.code, "NEWSMAP-NO-LOCAL-COPY");
assert.equal(o.body.standalone, false);
console.log("ok look rule: dry_run forwarded unless ?view=1");
console.log("NEWS-COPY-OK");
