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

async function viaRuntime(request, env, path) {
  const bind = runtimeBinding(env);
  const absent = { ok: false, code: "LEG-RUNTIME-ABSENT", leg: LEG, path, standalone: true, plain: "The runtime is not reachable from AZ-OS right now. Nothing ran and nothing was shown as live.", ...honest };
  const refuse = (b, s) => new Response(JSON.stringify(b, null, 2), { status: s, headers: H });
  if (!bind) return refuse(absent, 503);
  let body;
  if (request.method === "POST") {
    const buf = await request.arrayBuffer();
    if (buf.byteLength > MAX_BODY) return refuse({ ok: false, code: "LEG-BODY-TOO-LARGE", leg: LEG, ...honest }, 413);
    body = buf;
  }
  try {
    const u = new URL(request.url);
    const headers = { accept: request.headers.get("accept") || "*/*" };
    const ct = request.headers.get("content-type");
    if (ct) headers["content-type"] = ct;
    const auth = request.headers.get("authorization");
    if (auth) headers.authorization = auth;
    const r = await bind.fetch(new Request("https://aziel-runtime.internal" + path + u.search, { method: request.method === "HEAD" ? "GET" : request.method, headers, body }));
    const out = new Headers(r.headers);
    out.set("X-Served-Through", "AZIEL_RUNTIME");
    return new Response(request.method === "HEAD" ? null : r.body, { status: r.status, headers: out });
  } catch {
    return refuse(absent, 503);
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
