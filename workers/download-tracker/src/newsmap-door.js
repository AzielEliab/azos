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
 * This Worker keeps no second map, no engine copy, and no news store. Flags are
 * read from the runtime answer and are never raised here: a refusal keeps live,
 * merged, and joined false. AZNEWS-SOURCE-ABSENT passes through as-is.
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
  if (view.live) return base + " The runtime reports a fetched news item on a pin, so the join is live there. 4DMap is not installed here. Globe: " + NEWSMAP_GLOBE_URL + ".";
  return base + " The runtime reports no fetched news item on a pin, so nothing is live or merged.";
}

/** Shape one runtime answer. Flags only pass through; they are never raised here. */
export function newsmapView(host, key, runtime) {
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
    live: !refused && result.live === true,
    merged: !refused && result.merged === true,
    joined: !refused && result.joined === true,
    source_present: Boolean(result && result.source_present === true),
    outlets_live: result && Number.isFinite(Number(result.outlets_live)) ? Number(result.outlets_live) : 0,
    lattice_live: !refused && result.lattice_live === true,
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
    runtime_status: runtime ? runtime.status : null,
    runtime: result,
    author: "Aziel Eliab",
  };
  view.plain = plainOf(spec.path, view);
  return assertNewsmapHonest(view);
}

export function assertNewsmapHonest(view) {
  if (view.refused && (view.live || view.merged || view.joined)) throw new Error("a refused newsmap call is marked live, merged, or joined");
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
  return { status: 200, body: newsmapView(host, key, runtime) };
}
