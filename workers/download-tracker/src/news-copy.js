/**
 * AZ-OS standalone AZNews copy (AZRT-AZOS-NEWS-1.0, AZOS-NEWS-COPY-1.0).
 *
 * aziel-runtime's AzNewsStore SENDS its ledger rows (news items, 4DMap pins, pull
 * and view receipts, weather, sky), in order from genesis, signed with the runtime
 * tether key. This tracker CHECKS every packet inside its own Durable Object
 * (SQLite): the Ed25519 signature against the pinned RUNTIME_TETHER_PUBKEY, every
 * document hash, both lattice links from the tip it already stored (genesis on first
 * contact), and that the packet tips are the last row. Only then are the rows kept.
 * No KV and no D1 writes.
 *
 * Reads: when the runtime is unreachable (or ?source=local), /v1/aznews, /v1/map and
 * /v1/newsmap/* serve from this copy. Each read re-verifies the served window against
 * the stored signed tips. standalone is true only when the answer came from this copy
 * AND that check passed. Reads from the copy mint no receipts (the copy is read-only).
 * Old rows keep their hashes; documents older than DOC_KEEP rows are dropped.
 * Author: Aziel Eliab. Identity is Aziel Eliab only.
 */
import { GENESIS, canonicalize, sha256Hex, primaryOf, offlineSecondaryOf, onlineSecondaryOf, verifySignature, pinnedKey } from "./tether.js";

export const NEWS_TETHER_SPEC = "AZRT-AZOS-NEWS-1.0";
export const NEWS_TETHER_KIND = "aznews-rows";
export const COPY_SPEC = "AZOS-NEWS-COPY-1.0";
export const COPY_DO_NAME = "azos-news-copy-v1";
export const MAX_PACKET_BYTES = 2_000_000;
export const MAX_PACKET_ROWS = 400;
export const DOC_KEEP = 6000;
export const READ_WINDOW = 3000;
const HEX64 = /^[a-f0-9]{64}$/;
const USER_RE = /^[a-zA-Z0-9._-]{1,80}$/;

export const COPY_FACTS = Object.freeze({
  copy_spec: COPY_SPEC,
  tether_spec: NEWS_TETHER_SPEC,
  storage: "durable-object-sqlite",
  kv_writes: false,
  d1_writes: false,
  copy_is_read_only: true,
  mints_receipts: false,
  author: "Aziel Eliab",
});

export const COPY_RULE =
  "standalone is true only when this answer was served from AZ-OS's own copy and the served rows re-verified, up to the stored signed tip: " +
  "every document hash recomputes, each primary = H(document, primary_prev), each secondary recomputes, the links are unbroken, and the last row equals the signed tips. " +
  "The copy was checked from genesis on the way in (signature against the pinned runtime key, every row). A copy is not a live feed: live stays false when the runtime is unreachable.";

function refuse(code, message, status = 400, extra = {}) {
  return { status, body: { ok: false, refused: true, stored: false, code, message, ...extra, ...COPY_FACTS } };
}

/** Check one row's hashes against the expected previous tips. Returns null when good, else a reason. */
export async function checkRow(row, expected, { docHash = true } = {}) {
  const lat = row && row.lattice;
  if (!lat || !HEX64.test(String(lat.document_hash)) || !HEX64.test(String(lat.primary)) || !HEX64.test(String(lat.secondary))) return "row hashes missing";
  if (lat.primary_prev !== expected.primary || lat.secondary_prev !== expected.secondary) return "row does not link to the previous tip";
  if (docHash && row.doc !== undefined && row.doc !== null) {
    if ((await sha256Hex(canonicalize(row.doc))) !== lat.document_hash) return "document hash does not recompute";
  }
  if ((await primaryOf(lat.document_hash, lat.primary_prev)) !== lat.primary) return "primary hash does not recompute";
  if (lat.offline === true) {
    if (!USER_RE.test(String(lat.username || ""))) return "offline row without a viewer handle";
    if ((await offlineSecondaryOf(lat.document_hash, lat.username)) !== lat.secondary) return "offline secondary does not recompute";
  } else if ((await onlineSecondaryOf(lat.primary, lat.secondary_prev)) !== lat.secondary) {
    return "online secondary does not recompute";
  }
  return null;
}

/** Pure packet check. state = { tip_seq, tips } or null. hasOffline(secondary) -> bool. */
export async function checkNewsPacket(packet, { pinned, state, hasOffline }) {
  if (!packet || typeof packet !== "object" || Array.isArray(packet)) return refuse("NEWS-COPY-SHAPE", "The body must be one JSON object.");
  if (packet.spec !== NEWS_TETHER_SPEC || packet.kind !== NEWS_TETHER_KIND || packet.chain !== "aznews") return refuse("NEWS-COPY-SPEC", "Unknown spec, kind, or chain.");
  if (!pinned) return refuse("NEWS-COPY-KEY-UNPINNED", "No pinned runtime public key, so nothing can be verified or stored.", 503);
  if (packet.public_key !== pinned) return refuse("NEWS-COPY-KEY-MISMATCH", "The packet key is not the pinned runtime key.", 403);
  if (!(await verifySignature(pinned, packet))) return refuse("NEWS-COPY-SIG", "The Ed25519 signature does not verify against the pinned runtime key.", 403);
  const rows = Array.isArray(packet.rows) ? packet.rows : null;
  if (!rows || rows.length < 1 || rows.length > MAX_PACKET_ROWS) return refuse("NEWS-COPY-ROWS", "A packet carries between 1 and " + MAX_PACKET_ROWS + " rows.");
  const tipSeq = state && state.tip_seq ? Number(state.tip_seq) : 0;
  if (Number(packet.after_seq) !== tipSeq) return refuse("NEWS-COPY-LINK", "The packet does not start after the tip this copy already stored.", 409, { tip_seq: tipSeq });
  let expected = tipSeq && state.tips ? { primary: state.tips.primary, secondary: state.tips.secondary } : { primary: GENESIS, secondary: GENESIS };
  const seenOffline = new Set();
  for (let i = 0; i < rows.length; i++) {
    const row = rows[i] || {};
    if (Number(row.seq) !== tipSeq + i + 1) return refuse("NEWS-COPY-SEQ", "Row " + i + " is out of order.");
    if (typeof row.kind !== "string" || !row.kind) return refuse("NEWS-COPY-ROW-SHAPE", "Row " + i + " has no kind.");
    if (row.doc === undefined || row.doc === null) return refuse("NEWS-COPY-ROW-SHAPE", "Row " + i + " has no document.");
    const why = await checkRow(row, expected);
    if (why) return refuse("NEWS-COPY-HASH", "Row " + row.seq + ": " + why + ".", 409);
    if (row.lattice.offline === true) {
      if (seenOffline.has(row.lattice.secondary) || (hasOffline && (await hasOffline(row.lattice.secondary)))) return refuse("NEWS-COPY-DOUBLE", "Row " + row.seq + " is an offline view already stored.", 409);
      seenOffline.add(row.lattice.secondary);
    }
    expected = { primary: row.lattice.primary, secondary: row.lattice.secondary };
  }
  const last = rows[rows.length - 1];
  if (!packet.tips || packet.tips.primary !== expected.primary || packet.tips.secondary !== expected.secondary || Number(packet.tips.seq) !== Number(last.seq)) {
    return refuse("NEWS-COPY-TIPS", "The packet tips are not the last row's hashes.");
  }
  return { ok: true, rows, tips: { ...expected, seq: Number(last.seq) } };
}

/* ---------------------------------------------------------------- repos */

function rowRecord(row) {
  const d = row.doc || {};
  return {
    seq: Number(row.seq),
    kind: row.kind,
    at: row.at || null,
    item_id: row.kind === "news" ? d.item_id || null : null,
    doc: row.doc == null ? null : row.doc,
    lattice: row.lattice,
  };
}

/** In-memory repo (tests). Same surface as sqlCopyRepo. */
export function memCopyRepo() {
  const rows = new Map();
  let meta = {};
  const off = new Set();
  return {
    kind: "memory",
    async meta() { return meta.state || null; },
    async hasOffline(sec) { return off.has(sec); },
    async put(recs, state) {
      for (const r of recs) {
        rows.set(r.seq, JSON.parse(JSON.stringify(r)));
        if (r.lattice.offline === true) off.add(r.lattice.secondary);
      }
      meta.state = state;
    },
    async get(seq) { return rows.get(Number(seq)) || null; },
    async range(from, to) { const out = []; for (let s = from; s <= to; s++) if (rows.has(s)) out.push(rows.get(s)); return out; },
    async newest(kind, limit, minSeq = 0) { return [...rows.values()].filter((r) => (!kind || (Array.isArray(kind) ? kind.includes(r.kind) : r.kind === kind)) && r.seq >= minSeq).sort((a, b) => b.seq - a.seq).slice(0, limit); },
    async byItem(id) { return [...rows.values()].find((r) => r.item_id === id) || null; },
    async counts() { const c = {}; for (const r of rows.values()) c[r.kind] = (c[r.kind] || 0) + 1; return c; },
    async prune(belowSeq) { for (const r of rows.values()) if (r.seq < belowSeq) r.doc = null; },
  };
}

export function sqlCopyRepo(storage) {
  const sql = storage.sql;
  sql.exec("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL) WITHOUT ROWID");
  sql.exec("CREATE TABLE IF NOT EXISTS rows (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, at TEXT, item_id TEXT, doc TEXT, lattice TEXT NOT NULL, offline_secondary TEXT)");
  sql.exec("CREATE INDEX IF NOT EXISTS rows_kind ON rows (kind, seq)");
  sql.exec("CREATE INDEX IF NOT EXISTS rows_item ON rows (item_id)");
  sql.exec("CREATE INDEX IF NOT EXISTS rows_off ON rows (offline_secondary)");
  const parse = (r) => (r ? { seq: Number(r.seq), kind: r.kind, at: r.at, item_id: r.item_id, doc: r.doc == null ? null : JSON.parse(r.doc), lattice: JSON.parse(r.lattice) } : null);
  const one = (q, ...a) => { const x = sql.exec(q, ...a).toArray(); return x.length ? x[0] : null; };
  return {
    kind: "durable-object-sqlite",
    async meta() { const r = one("SELECT v FROM meta WHERE k = 'state'"); return r ? JSON.parse(r.v) : null; },
    async hasOffline(sec) { return Boolean(one("SELECT seq FROM rows WHERE offline_secondary = ?", sec)); },
    async put(recs, state) {
      storage.transactionSync(() => {
        for (const r of recs) {
          sql.exec("INSERT INTO rows (seq, kind, at, item_id, doc, lattice, offline_secondary) VALUES (?, ?, ?, ?, ?, ?, ?)",
            r.seq, r.kind, r.at, r.item_id, r.doc == null ? null : JSON.stringify(r.doc), JSON.stringify(r.lattice), r.lattice.offline === true ? r.lattice.secondary : null);
        }
        sql.exec("INSERT INTO meta (k, v) VALUES ('state', ?) ON CONFLICT(k) DO UPDATE SET v = excluded.v", JSON.stringify(state));
      });
    },
    async get(seq) { return parse(one("SELECT * FROM rows WHERE seq = ?", Number(seq))); },
    async range(from, to) { return sql.exec("SELECT * FROM rows WHERE seq >= ? AND seq <= ? ORDER BY seq", Number(from), Number(to)).toArray().map(parse); },
    async newest(kind, limit, minSeq = 0) {
      const kinds = kind ? (Array.isArray(kind) ? kind : [kind]) : null;
      const q = kinds
        ? "SELECT * FROM rows WHERE kind IN (" + kinds.map(() => "?").join(",") + ") AND seq >= ? ORDER BY seq DESC LIMIT ?"
        : "SELECT * FROM rows WHERE seq >= ? ORDER BY seq DESC LIMIT ?";
      return sql.exec(q, ...(kinds || []), Number(minSeq), Number(limit)).toArray().map(parse);
    },
    async byItem(id) { return parse(one("SELECT * FROM rows WHERE item_id = ? ORDER BY seq DESC LIMIT 1", String(id))); },
    async counts() { const c = {}; for (const r of sql.exec("SELECT kind, COUNT(*) AS n FROM rows GROUP BY kind").toArray()) c[r.kind] = Number(r.n); return c; },
    async prune(belowSeq) { sql.exec("UPDATE rows SET doc = NULL WHERE seq < ? AND doc IS NOT NULL", Number(belowSeq)); },
  };
}

/* ---------------------------------------------------------------- ingest */

export async function copyIngest(repo, packet, { pinned, now = new Date().toISOString() } = {}) {
  const state = await repo.meta();
  const checked = await checkNewsPacket(packet, { pinned, state, hasOffline: (s) => repo.hasOffline(s) });
  if (!checked.ok) return checked;
  const next = {
    spec: COPY_SPEC,
    from_genesis: true,
    tip_seq: checked.tips.seq,
    tips: { primary: checked.tips.primary, secondary: checked.tips.secondary },
    rows: (state ? state.rows || 0 : 0) + checked.rows.length,
    packets: (state ? state.packets || 0 : 0) + 1,
    first_at: (state && state.first_at) || now,
    updated_at: now,
    runtime_store_tip: packet.store_tip && Number.isFinite(Number(packet.store_tip.seq)) ? { seq: Number(packet.store_tip.seq), primary: packet.store_tip.primary || null } : null,
    runtime_git_sha: typeof packet.git_sha === "string" ? packet.git_sha.slice(0, 64) : null,
    packet_hash: typeof packet.packet_hash === "string" ? packet.packet_hash.slice(0, 64) : null,
    packet_t: typeof packet.t === "string" ? packet.t.slice(0, 40) : null,
    public_key: packet.public_key,
  };
  await repo.put(checked.rows.map(rowRecord), next);
  if (next.tip_seq > DOC_KEEP) await repo.prune(next.tip_seq - DOC_KEEP);
  return { status: 200, body: { ok: true, stored: true, verified: true, tip_seq: next.tip_seq, tips: next.tips, rows_accepted: checked.rows.length, rows: next.rows, ...COPY_FACTS } };
}

export async function copyState(repo, env) {
  const st = await repo.meta();
  return {
    ok: true,
    ...COPY_FACTS,
    pinned_public_key: pinnedKey(env),
    tip_seq: st ? st.tip_seq : 0,
    tips: st ? st.tips : null,
    rows: st ? st.rows : 0,
    from_genesis: Boolean(st && st.from_genesis),
    updated_at: st ? st.updated_at : null,
    runtime_store_tip: st ? st.runtime_store_tip : null,
    lag_rows_at_sync: st && st.runtime_store_tip ? Math.max(0, st.runtime_store_tip.seq - st.tip_seq) : null,
  };
}

/* ---------------------------------------------------------------- reads */

/** Re-verify rows fromSeq..tip against the stored signed tips. Bounded by READ_WINDOW. */
export async function verifyWindow(repo, st, fromSeq) {
  if (!st || !st.tip_seq) return { ok: false, reason: "the copy is empty" };
  const from = Math.max(1, Math.min(st.tip_seq, Number(fromSeq) || st.tip_seq));
  if (st.tip_seq - from + 1 > READ_WINDOW) return { ok: false, reason: "window larger than " + READ_WINDOW + " rows" };
  const rows = await repo.range(from, st.tip_seq);
  if (rows.length !== st.tip_seq - from + 1) return { ok: false, reason: "rows missing from the copy" };
  let expected = { primary: rows[0].lattice.primary_prev, secondary: rows[0].lattice.secondary_prev };
  if (from > 1) {
    const before = await repo.get(from - 1);
    if (!before || before.lattice.primary !== expected.primary || before.lattice.secondary !== expected.secondary) return { ok: false, reason: "window does not link to the row before it" };
  } else if (expected.primary !== GENESIS || expected.secondary !== GENESIS) return { ok: false, reason: "row 1 does not start at genesis" };
  let docs = 0;
  for (const row of rows) {
    const why = await checkRow(row, expected);
    if (why) return { ok: false, reason: "row " + row.seq + ": " + why, at_seq: row.seq };
    if (row.doc != null) docs += 1;
    expected = { primary: row.lattice.primary, secondary: row.lattice.secondary };
  }
  if (expected.primary !== st.tips.primary || expected.secondary !== st.tips.secondary) return { ok: false, reason: "the last row is not the stored signed tip" };
  return { ok: true, from, to: st.tip_seq, rows: rows.length, documents_rehashed: docs, tips: st.tips };
}

function newsView(r) {
  const d = r.doc || {};
  return {
    seq: r.seq, item_id: d.item_id, outlet: d.outlet && d.outlet.name, outlet_id: d.outlet && d.outlet.id, title: d.title,
    link: d.canonical_url || d.link, published: d.published, wording: String(d.wording || "").slice(0, 600), images: d.images,
    reported_location: d.reported_location, event_location: d.event_location,
    lattice: { primary: r.lattice.primary, secondary: r.lattice.secondary, document_hash: r.lattice.document_hash },
  };
}

function pinView(r) {
  const d = r.doc || {};
  return {
    pin_id: "pin-" + r.seq, seq: r.seq, added_at: r.at, pin_type: d.pin_type, color: d.color, color_hex: d.color_hex, role: d.role,
    event: d.event, date: d.date, geo: d.geo, report_location_source: d.role === "report" ? (d.report_location_source || (d.geo && d.geo.report_location_source) || null) : null,
    report_seq: d.report_seq || null, report_document_hash: d.report_document_hash || null, pull_receipt_seq: d.pull_receipt_seq || null,
    source: d.source, permalink: "/aznews?pin=pin-" + r.seq,
    lattice: { primary: r.lattice.primary, secondary: r.lattice.secondary },
  };
}

function colorKey(pins) {
  const key = {};
  for (const p of pins) if (p.pin_type && !key[p.pin_type]) key[p.pin_type] = { color: p.color, hex: p.color_hex };
  return key;
}

/** Local join on the copy: newest items -> their pins name the item's hash; pull receipt points back. */
async function localJoin(repo, minSeq) {
  const items = await repo.newest("news", 10, minSeq);
  if (!items.length) return { joined: false, checked: 0, linked: 0, reason: "no items in the copy window" };
  const pins = await repo.newest("pin", 400, items[items.length - 1].seq);
  let linked = 0;
  for (const it of items) {
    const mine = pins.filter((p) => p.doc && p.doc.report_seq === it.seq && p.doc.report_document_hash === it.lattice.document_hash);
    const rc = mine.length && mine[0].doc.pull_receipt_seq ? await repo.get(mine[0].doc.pull_receipt_seq) : null;
    if (mine.length && rc && rc.doc && rc.doc.report_seq === it.seq) linked += 1;
  }
  return { joined: linked === items.length, checked: items.length, linked, reason: linked === items.length ? null : (items.length - linked) + " item(s) did not round-trip in the copy" };
}

/** Serve one read from the copy. Returns the body (with standalone and the verify evidence). */
export async function copyRead(repo, op, payload = {}) {
  const st = await repo.meta();
  const base = { ...COPY_FACTS, source: "azos-local-copy", standalone: false, standalone_rule: COPY_RULE, live: false, live_reason: "Served from AZ-OS's copy, not the live runtime feed." };
  if (!st || !st.tip_seq) return { ok: false, code: "NEWS-COPY-EMPTY", message: "AZ-OS has no verified copy yet.", ...base };
  const minSeq = Math.max(1, st.tip_seq - READ_WINDOW + 1);
  const lim = (n, d, max) => Math.max(1, Math.min(max, Number(n) || d));
  let body;
  let from = st.tip_seq;
  const low = (rows) => { for (const r of rows) if (r && r.seq < from) from = r.seq; };
  if (op === "feed") {
    const rows = await repo.newest("news", lim(payload.limit, 20, 50), minSeq); low(rows);
    body = { ok: true, op, items: rows.map(newsView) };
  } else if (op === "pins" || op === "plot") {
    let rows = await repo.newest("pin", lim(payload.limit, 200, 200), minSeq);
    if (payload.type) rows = rows.filter((r) => r.doc && r.doc.pin_type === payload.type);
    low(rows);
    const pins = rows.map(pinView);
    body = { ok: true, op, pins, last10: pins.slice(0, 10), colors: colorKey(pins) };
  } else if (op === "sky") {
    const rows = await repo.newest("sky", 1, minSeq); low(rows);
    body = rows.length ? { ok: true, op, seq: rows[0].seq, sky: rows[0].doc } : { ok: false, code: "NEWS-COPY-SKY-ABSENT" };
  } else if (op === "weather") {
    const rows = await repo.newest("weather", 60, minSeq); low(rows);
    const seen = new Set();
    const regions = [];
    for (const r of rows) { const a = r.doc && r.doc.anchor && (r.doc.anchor.name || r.doc.anchor.id || JSON.stringify(r.doc.anchor)); if (seen.has(a)) continue; seen.add(a); regions.push({ seq: r.seq, anchor: r.doc.anchor, reading: r.doc.reading, conditions: r.doc.conditions, severe: r.doc.severe }); }
    body = { ok: true, op, regions };
  } else if (op === "receipts") {
    const rows = await repo.newest(["pull_receipt", "view_receipt"], lim(payload.limit, 20, 50), minSeq); low(rows);
    body = { ok: true, op, receipts: rows.map((r) => ({ seq: r.seq, kind: r.kind, at: r.at, doc: r.doc, lattice: { primary: r.lattice.primary, secondary: r.lattice.secondary } })) };
  } else if (op === "item") {
    const r = await repo.byItem(String(payload.item_id || ""));
    if (!r || r.seq < minSeq || !r.doc) return { ok: false, code: "NEWS-COPY-NO-MATCH", ...base };
    low([r]);
    body = { ok: true, op, item: newsView(r) };
  } else if (op === "pin_open") {
    const m = /^pin-(\d+)$/.exec(String(payload.pin_id || ""));
    const p = m ? await repo.get(Number(m[1])) : null;
    if (!p || p.kind !== "pin" || p.seq < minSeq || !p.doc) return { ok: false, code: "NEWS-COPY-PIN-ABSENT", ...base };
    const rep = p.doc.report_seq ? await repo.get(p.doc.report_seq) : null;
    low([p, rep].filter(Boolean));
    body = { ok: true, op, pin: pinView(p), linked: Boolean(rep && rep.lattice.document_hash === p.doc.report_document_hash), item: rep && rep.kind === "news" && rep.doc ? newsView(rep) : null };
  } else if (op === "globe") {
    const pinRows = await repo.newest("pin", 200, minSeq);
    const newsRows = await repo.newest("news", 10, minSeq);
    const sky = await repo.newest("sky", 1, minSeq);
    low(pinRows); low(newsRows); low(sky);
    const pins = pinRows.map(pinView);
    const weather = await copyRead(repo, "weather", {});
    body = { ok: true, op, pins, last10: pins.slice(0, 10), colors: colorKey(pins), items: newsRows.map(newsView), sky: sky[0] ? sky[0].doc : null, weather: { regions: weather.regions || [] } };
  } else if (op === "status" || op === "verify" || op === "sources") {
    from = minSeq;
    body = { ok: true, op, counts: await repo.counts() };
  } else {
    return { ok: false, code: "NEWS-COPY-UNKNOWN-OP", ...base };
  }
  const check = await verifyWindow(repo, st, from);
  const join = await localJoin(repo, minSeq);
  return {
    ...base,
    ...body,
    standalone: check.ok === true && Boolean(st.from_genesis),
    copy: { tip_seq: st.tip_seq, tips: st.tips, rows: st.rows, from_genesis: Boolean(st.from_genesis), updated_at: st.updated_at, runtime_store_tip: st.runtime_store_tip, lag_rows_at_sync: st.runtime_store_tip ? Math.max(0, st.runtime_store_tip.seq - st.tip_seq) : null, public_key: st.public_key },
    copy_verify: check,
    joined: check.ok === true && join.joined === true,
    merged: false,
    merged_reason: "merged needs the runtime's full-walk lattice check; the copy reports joined only.",
    join_check: join,
  };
}

/* ---------------------------------------------------------------- DO */

export class AzosNewsCopy {
  constructor(ctx, env) {
    this.ctx = ctx;
    this.env = env;
    this.repo = null;
    this.queue = Promise.resolve();
  }

  repoOf() {
    if (!this.repo) this.repo = sqlCopyRepo(this.ctx.storage);
    return this.repo;
  }

  async fetch(request) {
    let body = {};
    try { body = await request.json(); } catch { body = {}; }
    const run = this.queue.then(async () => {
      const repo = this.repoOf();
      if (body.op === "ingest") return copyIngest(repo, body.packet, { pinned: pinnedKey(this.env) });
      if (body.op === "state") return { status: 200, body: await copyState(repo, this.env) };
      if (body.op === "export") {
        const st = await repo.meta();
        const after = Math.max(0, Number(body.after) || 0);
        const n = Math.max(1, Math.min(500, Number(body.limit) || 200));
        const rows = st && st.tip_seq > after ? await repo.range(after + 1, Math.min(st.tip_seq, after + n)) : [];
        return { status: 200, body: { ok: true, ...COPY_FACTS, tip_seq: st ? st.tip_seq : 0, tips: st ? st.tips : null, from_genesis: Boolean(st && st.from_genesis), after, rows: rows.map((r) => ({ seq: r.seq, kind: r.kind, at: r.at, doc: r.doc, lattice: r.lattice })) } };
      }
      return { status: 200, body: await copyRead(repo, String(body.op || ""), body.payload || {}) };
    });
    this.queue = run.catch(() => null);
    try {
      const out = await run;
      return new Response(JSON.stringify(out.body), { status: out.status, headers: { "content-type": "application/json" } });
    } catch (err) {
      return new Response(JSON.stringify({ ok: false, code: "NEWS-COPY-ERROR", message: String((err && err.message) || err).slice(0, 200) }), { status: 500, headers: { "content-type": "application/json" } });
    }
  }
}

function stubOf(env) {
  const ns = env && env.AZOS_NEWS_COPY;
  if (!ns) return null;
  if (typeof ns.getByName === "function") return ns.getByName(COPY_DO_NAME);
  if (typeof ns.idFromName === "function") return ns.get(ns.idFromName(COPY_DO_NAME));
  return null;
}

/** Call the copy object. Never throws. Returns { status, body }. */
export async function newsCopyCall(env, msg) {
  const stub = stubOf(env);
  if (!stub) return { status: 503, body: { ok: false, code: "NEWS-COPY-UNBOUND", message: "This Worker has no AZOS_NEWS_COPY Durable Object binding.", ...COPY_FACTS } };
  try {
    const res = await stub.fetch(new Request("https://azos-news-copy.internal/", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(msg) }));
    let body = null;
    try { body = await res.json(); } catch { body = null; }
    return { status: res.status, body: body || { ok: false, code: "NEWS-COPY-ERROR" } };
  } catch (err) {
    return { status: 503, body: { ok: false, code: "NEWS-COPY-UNAVAILABLE", message: String((err && err.message) || err).slice(0, 200), ...COPY_FACTS } };
  }
}

/** Routes: GET/POST /v1/tether/aznews, GET /v1/aznews/copy (export for the local CLI). Returns null otherwise. */
export async function handleNewsCopyRoute(request, url, env) {
  const path = url.pathname.replace(/\/+$/, "");
  if (path === "/v1/tether/aznews" && request.method === "GET") return newsCopyCall(env, { op: "state" });
  if (path === "/v1/tether/aznews" && request.method === "POST") {
    const text = await request.text();
    if (text.length > MAX_PACKET_BYTES) return refuse("NEWS-COPY-SIZE", "The packet is too large.", 413);
    let packet;
    try { packet = JSON.parse(text); } catch { return refuse("NEWS-COPY-JSON", "The body is not JSON."); }
    return newsCopyCall(env, { op: "ingest", packet });
  }
  if (path === "/v1/aznews/copy" && request.method === "GET") {
    return newsCopyCall(env, { op: "export", after: url.searchParams.get("after"), limit: url.searchParams.get("limit") });
  }
  return null;
}
