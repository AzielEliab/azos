/**
 * AZNews and 4DMap paths on this hosted Worker, served through the one
 * aziel-runtime FragGate door (`4dmap` slug). Three paths:
 *   joined            GET /v1/newsmap         → news_status
 *                     POST /v1/newsmap/pin    → news_pin   (a news item lands as a map pin)
 *                     POST /v1/newsmap/open   → news_open  (a pin opens the matching news)
 *   AZNews standalone GET /v1/aznews          → news_sources
 *                     POST /v1/newsmap/ingest → news_ingest (stores a story with no pin)
 *   4DMap standalone  GET /v1/map             → plot
 *                     POST /v1/newsmap/library_pin, /lattice_tip
 *   AZNews live store GET /v1/newsmap/feed, /sky, /pins, /globe, /verify, /receipts
 *                     POST /v1/newsmap/pin_open {pin_id}, /item {item_id}
 *                     (runtime AzNewsStore: real RSS headlines, Open-Meteo weather,
 *                     computed sky, colored pins, last-10 list; globe page at
 *                     NEWSMAP_RUNTIME_ORIGIN + "/aznews")
 * This Worker keeps no second map, no engine copy, and no news store. It reads the
 * runtime store and checks the join itself (NEWSMAP-DOOR-JOIN-1.0): it asks for the
 * newest stored item's pins (news_pin), opens one pin (news_open), and confirms the
 * pin opens that same item with a matching report hash. Top-level live / joined /
 * merged are this door's own result: true only when the runtime says so AND the
 * door's round trip passed. The runtime's raw claims are shown apart under
 * runtime_claims and are never relayed as this door's flags. Both round-trip reads
 * are dry_run, so they mint no receipt. A refusal keeps everything false.
 * Not a second door. Not an installed app. Author: Aziel Eliab.
 */

export const NEWSMAP_RUNTIME_ORIGIN = "https://aziel-runtime.vibelock.workers.dev";

export const NEWSMAP_OPS = Object.freeze({
  status: { op: "news_status", path: "joined" },
  pin: { op: "news_pin", path: "joined" },
  open: { op: "news_open", path: "joined" },
  sources: { op: "news_sources", path: "aznews-standalone" },
  ingest: { op: "news_ingest", path: "aznews-standalone" },
  weather: { op: "news_weather", path: "aznews-standalone" },
  plot: { op: "plot", path: "4dmap-standalone" },
  library_pin: { op: "library_pin", path: "4dmap-standalone" },
  lattice_tip: { op: "lattice_tip", path: "4dmap-standalone" },
  feed: { op: "news_feed", path: "aznews-live" },
  item: { op: "news_item", path: "aznews-live" },
  sky: { op: "news_sky", path: "aznews-live" },
  pins: { op: "news_pins", path: "aznews-live" },
  pin_open: { op: "news_pin_open", path: "aznews-live" },
  globe: { op: "news_globe", path: "aznews-live" },
  verify: { op: "news_verify", path: "aznews-live" },
  receipts: { op: "news_receipts", path: "aznews-live" },
});

/** The runtime AZNews globe page (real news, weather, sky, colored pins, last-10, color key). */
export const NEWSMAP_GLOBE_URL = NEWSMAP_RUNTIME_ORIGIN + "/aznews";

const GET_ROUTES = Object.freeze({
  "/v1/newsmap": "status",
  "/v1/aznews": "sources",
  "/v1/map": "plot",
  "/v1/newsmap/feed": "feed",
  "/v1/newsmap/sky": "sky",
  "/v1/newsmap/pins": "pins",
  "/v1/newsmap/globe": "globe",
  "/v1/newsmap/verify": "verify",
  "/v1/newsmap/receipts": "receipts",
});

const MAX_BODY = 65536;

function runtimeOrigin(env) {
  const raw = env && (env.AZIEL_RUNTIME_ORIGIN || env.RUNTIME_ORIGIN);
  return raw ? String(raw).replace(/\/+$/, "") : NEWSMAP_RUNTIME_ORIGIN;
}

async function callRuntime(env, op, payload) {
  const url = runtimeOrigin(env) + "/v1/fraggate/call";
  const init = {
    method: "POST",
    headers: { "content-type": "application/json", accept: "application/json", "user-agent": "Mozilla/5.0 (newsmap-door)" },
    body: JSON.stringify({ name: "4dmap", op, payload: payload || {} }),
  };
  const binding = env && env.AZIEL_RUNTIME && typeof env.AZIEL_RUNTIME.fetch === "function" ? env.AZIEL_RUNTIME : null;
  const res = binding ? await binding.fetch(new Request(url, init)) : await fetch(url, init);
  let body = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  return { status: res.status, body };
}

function plainOf(path, view) {
  const base =
    "AZNews can stand alone. 4DMap can stand alone. On the joined path a news item can land as a map pin, or a pin can open the matching news. " +
    "This page reads the aziel-runtime 4DMap engine through the one FragGate door. It keeps no second map and installs nothing.";
  if (view.refused) {
    return base + " The runtime refused this call (" + (view.code || "refused") + "). Nothing is live or merged.";
  }
  if (view.joined) return base + " This door opened the newest stored item's pin and it led back to the same item, and the runtime's own join check agrees, so the join reads " + (view.merged ? "joined and merged" : "joined, not merged") + (view.live ? " and live" : ", not live") + ". 4DMap is not installed here. Globe: " + NEWSMAP_GLOBE_URL + ".";
  return base + " This door has not confirmed the join on this request, so live, joined and merged read false here, whatever the runtime claims (see runtime_claims).";
}

export const DOOR_JOIN_SPEC = "NEWSMAP-DOOR-JOIN-1.0";

function resultOf(runtime) {
  const outer = runtime && runtime.body && typeof runtime.body === "object" ? runtime.body : null;
  return outer && outer.ok !== false && outer.result && typeof outer.result === "object" ? outer.result : null;
}

/**
 * The door's own join check against the runtime AzNewsStore: item -> pins -> open the
 * pin -> same item, matching report hash, pull receipt present. Two dry_run reads.
 * `call(op, payload)` returns a runtime answer ({status, body}).
 */
export async function doorJoinCheck(call, at = new Date().toISOString()) {
  const out = { spec: DOOR_JOIN_SPEC, checked_at: at, reads_store: true, store_copy: false, ok: false, item_id: null, pin_id: null, pins_on_item: 0, reason: null };
  let a = null;
  try { a = resultOf(await call("news_pin", { dry_run: true })); } catch { a = null; }
  if (!a || a.ok !== true || !a.item) { out.reason = "news_pin (item -> pins) did not return a stored item" + (a && a.code ? " (" + a.code + ")" : ""); return out; }
  out.item_id = a.item.item_id || null;
  const pins = Array.isArray(a.pins) ? a.pins.filter((p) => p && p.pin_id) : [];
  out.pins_on_item = pins.length;
  out.pull_receipt_seq = a.pull_receipt_seq || null;
  if (!out.item_id || !pins.length) { out.reason = "the newest stored item has no pins"; return out; }
  if (!out.pull_receipt_seq) { out.reason = "the newest stored item has no pull receipt"; return out; }
  const pin = pins[0];
  out.pin_id = pin.pin_id;
  let b = null;
  try { b = resultOf(await call("news_open", { pin_id: pin.pin_id, dry_run: true })); } catch { b = null; }
  if (!b || b.ok !== true) { out.reason = "news_open (pin -> item) refused" + (b && b.code ? " (" + b.code + ")" : ""); return out; }
  if (b.linked !== true) { out.reason = "the pin's report hash does not match the stored item"; return out; }
  if (!b.item || b.item.item_id !== out.item_id) { out.reason = "the pin opened a different item"; return out; }
  out.ok = true;
  return out;
}

const CLAIM_KEYS = ["live", "joined", "merged", "lattice_live"];

/** Shape one runtime answer. Flags are this door's own result; runtime claims sit apart. */
export function newsmapView(host, key, runtime, check = null) {
  const spec = NEWSMAP_OPS[key];
  const outer = runtime && runtime.body && typeof runtime.body === "object" ? runtime.body : null;
  const result = outer && outer.result && typeof outer.result === "object" ? outer.result : null;
  const reachable = Boolean(outer);
  const refused = !reachable || !result || outer.ok === false || result.ok === false || result.refused === true || result.code === "AZNEWS-SOURCE-ABSENT";
  const view = {
    ok: reachable && outer.ok !== false && Boolean(result) && result.ok !== false,
    refused,
    host,
    path: spec.path,
    op: spec.op,
    code: !reachable ? "NEWSMAP-RUNTIME-UNREACHABLE" : (result && result.code) || outer.code || null,
    door: "aziel-runtime FragGate /v1/fraggate/call (4dmap)",
    second_door: false,
    second_map: false,
    engine_copy: false,
    installed: false,
    engine_installed: false,
    live: false,
    merged: false,
    joined: false,
    source_present: Boolean(result && result.source_present === true),
    outlets_live: result && Number.isFinite(Number(result.outlets_live)) ? Number(result.outlets_live) : 0,
    lattice_live: false,
    field_1_0: false,
    pilot_started: false,
    live_backends: false,
    alt_internet_live: false,
    mesh_node_live: false,
    paths: {
      joined: { present: true, ops: ["news_pin", "news_open"], route: "POST /v1/newsmap/pin | /v1/newsmap/open" },
      aznews_standalone: { present: true, ops: ["news_ingest", "news_sources"], route: "POST /v1/newsmap/ingest, GET /v1/aznews" },
      fourdmap_standalone: { present: true, ops: ["plot", "library_pin", "lattice_tip"], route: "GET /v1/map, POST /v1/newsmap/library_pin" },
      aznews_live: { present: true, ops: ["news_feed", "news_item", "news_sky", "news_pins", "news_pin_open", "news_globe", "news_verify", "news_receipts"], route: "GET /v1/newsmap/feed|sky|pins|globe|verify|receipts, POST /v1/newsmap/pin_open|item" },
    },
    globe_url: NEWSMAP_GLOBE_URL,
    door_join_check: check,
    flag_rule: "live / joined / merged / lattice_live here are true only when the runtime reports them AND this door's own round trip (" + DOOR_JOIN_SPEC + ") passed on this request. runtime_claims shows what the runtime said.",
    runtime_status: runtime ? runtime.status : null,
    runtime: result,
    author: "Aziel Eliab",
  };
  // Runtime claims, shown apart (status: the result itself; globe: result.status).
  const src = result && result.status && typeof result.status === "object" ? result.status : result;
  const claims = {};
  for (const k of CLAIM_KEYS) claims[k] = Boolean(src && src[k] === true);
  view.runtime_claims = claims;
  const doorOk = Boolean(check && check.ok === true);
  if (!refused && doorOk) {
    view.joined = claims.joined;
    view.lattice_live = claims.lattice_live;
    view.merged = claims.joined && claims.merged && claims.lattice_live;
    view.live = claims.live && claims.lattice_live;
  }
  view.join_reason = refused ? "the runtime refused" : !check ? "no runtime claim to check on this path" : doorOk ? (view.joined ? null : "the runtime itself reports joined false") : "door round trip failed: " + (check.reason || "unknown");
  view.plain = plainOf(spec.path, view);
  return assertNewsmapHonest(view);
}

export function assertNewsmapHonest(view) {
  if (view.refused && (view.live || view.merged || view.joined)) throw new Error("a refused newsmap call is marked live, merged, or joined");
  if ((view.live || view.merged || view.joined) && !(view.door_join_check && view.door_join_check.ok === true)) throw new Error("newsmap flags raised without this door's own join check");
  if (view.installed || view.engine_installed || view.second_map || view.second_door) throw new Error("newsmap claims an install, a second map, or a second door");
  return view;
}

/** Route one request. Returns { status, body } or null when the path is not a newsmap path. */
export async function handleNewsmap(request, url, env, host) {
  const path = url.pathname.replace(/\/+$/, "") || "/";
  let key = null;
  let payload = {};
  if ((request.method === "GET" || request.method === "HEAD") && GET_ROUTES[path]) {
    key = GET_ROUTES[path];
    const lim = Number(url.searchParams.get("limit"));
    if (Number.isFinite(lim) && lim > 0) payload.limit = Math.min(200, Math.floor(lim));
    if (NEWSMAP_OPS[key].path === "aznews-live") payload.via = String(host || "door").slice(0, 40);
  } else if (request.method === "POST" && path.startsWith("/v1/newsmap/")) {
    key = path.slice("/v1/newsmap/".length);
    if (!Object.prototype.hasOwnProperty.call(NEWSMAP_OPS, key)) {
      return { status: 404, body: { ok: false, refused: true, code: "NEWSMAP-UNKNOWN-OP", ops: Object.keys(NEWSMAP_OPS), live: false, merged: false, installed: false } };
    }
    const text = await request.text();
    if (text.length > MAX_BODY) return { status: 413, body: { ok: false, refused: true, code: "NEWSMAP-BODY-SIZE", live: false } };
    if (text.trim()) {
      try {
        payload = JSON.parse(text);
      } catch {
        return { status: 400, body: { ok: false, refused: true, code: "NEWSMAP-BAD-JSON", live: false } };
      }
    }
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) payload = {};
  } else {
    return null;
  }
  let runtime = null;
  try {
    runtime = await callRuntime(env, NEWSMAP_OPS[key].op, payload);
  } catch {
    runtime = null;
  }
  // Check the join here only when the runtime claims a flag (two dry_run reads).
  const r = resultOf(runtime);
  const src = r && r.status && typeof r.status === "object" ? r.status : r;
  let check = null;
  if (src && CLAIM_KEYS.some((k) => src[k] === true)) {
    check = await doorJoinCheck((op, p) => callRuntime(env, op, p));
  }
  return { status: 200, body: newsmapView(host, key, runtime, check) };
}
