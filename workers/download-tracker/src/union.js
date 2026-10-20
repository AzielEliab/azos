/**
 * AZ-LOCKSTEP-1.0 feature union, AZ-OS side. Features the runtime or AZInterface had and this leg
 * lacked, added with real wiring. Each one stands alone or fails closed when the runtime is absent:
 *   GET  /aznews, /newsmap   the AZNews + 4DMap human page (same page as AZInterface), read through
 *                            this leg's own newsmap door and verified copies
 *   GET  /v1/fraggate, /v1/fraggate/{list,describe,software,software.json,verify}, POST /v1/fraggate/call
 *   POST /mcp, GET /v1/runtime, /v1/runtime.json, /v1/azpipe/arch, /v1/software, /workspace, /v1/anchor/heads,
 *   receipts tip, memory, qns, uses, update manifest, catalog, about, 4DMap globe, MCP install cards
 *                            read through the runtime over AZIEL_RUNTIME. FragGate stays the one door: the
 *                            call runs on the runtime, never here. Absent -> 503 LEG-RUNTIME-ABSENT.
 * Proxy reads time out after LEG_RUNTIME_TIMEOUT_MS (default 4000) with 503 LEG-RUNTIME-TIMEOUT and abort the upstream
 * request; the caller IP rides as X-Azrt-Client-IP (LEG-CLIENT-IP-1.0; the runtime trusts it over the binding only).
 * Known limit (follow-up): the tether tip write is a KV read-modify-write, not compare-and-set. Concurrent valid
 * packets or a stale KV read can store an older tip; the next push re-links from the runtime tip (TETHER-LINK on a
 * fork). Same as AZ-OS src/tether.js, kept byte for byte.
 * Nothing here flips a live flag. Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
 */
import { runtimeBinding } from "./lockstep.js";
import { NEWSMAP_PAGE_PATHS, newsmapPageHtml } from "./newsmap-page.js";

const LEG = "azos";
const H = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "Access-Control-Allow-Origin": "*" };
const honest = { live: false, alt_internet_live: false, packet_path_live: false, mesh_node_live: false, kernel_live: false };
const MAX_BODY = 262144;

export const RUNTIME_GET_PATHS = Object.freeze([
  "/v1/fraggate", "/v1/fraggate/list", "/v1/fraggate/describe", "/v1/fraggate/software", "/v1/fraggate/software.json", "/v1/fraggate/verify",
  "/v1/runtime", "/v1/runtime.json", "/v1/azpipe/arch", "/v1/software", "/workspace", "/v1/anchor/heads", "/mcp",
  "/v1/receipts/tip", "/v1/memory", "/v1/qns", "/v1/uses", "/v1/update/manifest", "/v1/catalog.json", "/about", "/4dmap/globe", "/install/cursor.json",
]);
export const RUNTIME_POST_PATHS = Object.freeze(["/v1/fraggate/call", "/mcp"]);

function runtimeOrigin(env) {
  const raw = env && (env.AZIEL_RUNTIME_ORIGIN || env.RUNTIME_ORIGIN);
  return raw ? String(raw).replace(/\/+$/, "") : "https://aziel-runtime.vibelock.workers.dev";
}

/** Proxy timeout (ms). LEG_RUNTIME_TIMEOUT_MS clamps to 250..10000; default 4000. */
export function runtimeTimeoutMs(env) {
  const n = Number(env && env.LEG_RUNTIME_TIMEOUT_MS);
  return Number.isFinite(n) && n > 0 ? Math.min(10000, Math.max(250, Math.floor(n))) : 4000;
}

/** Read the body with an early abort: Content-Length first, then a streamed byte count. null = over the cap. */
async function cappedBody(request) {
  const declared = Number(request.headers.get("content-length"));
  if (Number.isFinite(declared) && declared > MAX_BODY) return null;
  if (!request.body) return new Uint8Array(0);
  const reader = request.body.getReader();
  const parts = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > MAX_BODY) {
      try { await reader.cancel("LEG-BODY-TOO-LARGE"); } catch {}
      return null;
    }
    parts.push(value);
  }
  const out = new Uint8Array(total);
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.byteLength; }
  return out;
}

async function viaRuntime(request, env, path) {
  const bind = runtimeBinding(env);
  const absent = { ok: false, code: "LEG-RUNTIME-ABSENT", leg: LEG, path, standalone: true, plain: "The runtime is not reachable from AZ-OS right now. Nothing ran and nothing was shown as live.", ...honest };
  const refuse = (b, s) => new Response(JSON.stringify(b, null, 2), { status: s, headers: b.code === "LEG-RUNTIME-ABSENT" || b.code === "LEG-RUNTIME-TIMEOUT" ? { ...H, "X-Leg-Runtime": "down" } : H });
  if (!bind) return refuse(absent, 503);
  let body;
  if (request.method === "POST") {
    body = await cappedBody(request);
    if (body === null) return refuse({ ok: false, code: "LEG-BODY-TOO-LARGE", leg: LEG, limit_bytes: MAX_BODY, written: false, ...honest }, 413);
  }
  const ms = runtimeTimeoutMs(env);
  const ctl = new AbortController();
  let timer;
  let timedOut = false;
  // R5: one deadline covers headers AND body. A runtime that sends headers then stalls the body is a timeout too.
  const late = new Promise((r) => { timer = setTimeout(() => { timedOut = true; ctl.abort(); r(null); }, ms); });
  const timeoutResponse = () => refuse({ ...absent, code: "LEG-RUNTIME-TIMEOUT", timeout_ms: ms, plain: `The runtime did not answer within ${ms} ms. Nothing was shown as live.` }, 503);
  try {
    const u = new URL(request.url);
    const headers = { accept: request.headers.get("accept") || "*/*" };
    const ct = request.headers.get("content-type");
    if (ct) headers["content-type"] = ct;
    const auth = request.headers.get("authorization");
    if (auth) headers.authorization = auth;
    // LEG-CLIENT-IP-1.0: name the caller so the runtime keys its rate limits per client (trusted over the binding only).
    const ip = request.headers.get("CF-Connecting-IP");
    if (ip && ip.trim()) headers["X-Azrt-Client-IP"] = ip.trim();
    const call = bind.fetch(new Request("https://aziel-runtime.internal" + path + u.search, { method: request.method === "HEAD" ? "GET" : request.method, headers, body, signal: ctl.signal }));
    const r = await Promise.race([call, late]);
    if (!r) {
      call.catch(() => null);
      return timeoutResponse();
    }
    let out_body = null;
    if (request.method !== "HEAD") {
      const read = r.arrayBuffer().then((b) => ({ b }), () => null);
      const got = await Promise.race([read, late]);
      if (!got) return timedOut ? timeoutResponse() : refuse(absent, 503);
      out_body = got.b;
    }
    const out = new Headers(r.headers);
    out.set("X-Served-Through", "AZIEL_RUNTIME");
    out.delete("content-length");
    return new Response(out_body, { status: r.status, headers: out });
  } catch {
    return timedOut ? timeoutResponse() : refuse(absent, 503);
  } finally {
    clearTimeout(timer);
  }
}

/** Returns a Response for a union route, or null. */
export async function handleUnionRoute(request, env) {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  const m = request.method;
  const get = m === "GET" || m === "HEAD";
  if (NEWSMAP_PAGE_PATHS.includes(path) && get) {
    const headers = { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "public, max-age=60", "X-Look-Rule": "page JS reads /v1/newsmap/globe?view=1 once" };
    return new Response(m === "HEAD" ? null : newsmapPageHtml(runtimeOrigin(env), url.searchParams.get("mode") || "combined"), { status: 200, headers });
  }
  // /mcp GET is the existing runtime discovery card; POST is JSON-RPC.
  if (get && RUNTIME_GET_PATHS.includes(path)) return viaRuntime(request, env, path);
  if (m === "POST" && RUNTIME_POST_PATHS.includes(path)) return viaRuntime(request, env, path);
  return null;
}
