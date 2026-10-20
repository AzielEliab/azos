/**
 * AZRT-REFUSAL-RECEIPT-1.0 addendum (RIB-018 gaps), peer side. Additive, fail closed.
 *
 * When this tracker refuses (status >= 400, JSON body with a stable `code` or `refuse`), the refusal
 * is reported over the AZIEL_RUNTIME service binding to the runtime's peer door
 * (POST https://peer.aziel.internal/v1/refusals/peer). The runtime seals it with the same
 * sealRefusal path onto its internal `refusals` ChainLock chain (dual lattice, append-only), so all
 * This tracker keeps no refusal chain of its own: there is one chain, on the runtime. AZ-OS holds a verified
 * copy of its tip from the signed tether (TETHER-REFUSALS-1.0); azinterface has no local copy and reads the
 * runtime's tip. Uncoded 4xx refusals under /v1/ get the fixed code HTTP-<status>-UNCODED. Reason text
 * is never sent: only the sha256 hex of the full reason is.
 *
 * The refusal itself never changes: same status, same fields, plus `refusal_receipt` and the header
 * X-Azrt-Refusal-Receipt. No binding, a failed call, or a slow call gives sealed:false with status
 * unavailable or receipt_pending, never an invented receipt. Auth refusals (401, token codes,
 * signature/key refusals) and 429s stay unrecorded. A tether packet for the `refusals` chain itself
 * is never sealed again (no feedback loop). The runtime dedupes per minute and caps per isolate.
 * Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
 */
export const REFUSAL_PEER_URL = "https://peer.aziel.internal/v1/refusals/peer";
export const REFUSAL_PEER_BUDGET_MS = 2500;
const CODE_RE = /^[A-Za-z][A-Za-z0-9_-]{1,63}$/;
const AUTH_CODES = ["token_required", "token_mismatch", "token_not_configured", "TOKEN-QUERY-REFUSED", "CL-NOT-ISSUER", "TETHER-SIG", "TETHER-KEY-MISMATCH", "TETHER-KEY-UNPINNED"];

/**
 * RIB-018 follow-up (AZBot pre-merge review): never send reason text. A message can repeat caller input
 * from the path, query or body, and a cut message hides the repeat from any substring check. Only the
 * sha256 hex of the full, uncut reason is sent. Defense in depth: the runtime peer door hashes any text too.
 */
export async function safeReason(reason, _url) {
  const r = reason == null ? "" : String(reason);
  if (!r) return { reason: null };
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(r));
  return { reason: null, reason_sha256: [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("") };
}

export function isAuthRefusal(status, code) {
  if (Number(status) === 401) return true;
  return AUTH_CODES.includes(code) || /token/i.test(String(code || ""));
}

export async function withPeerRefusalReceipt(request, response, env, { surface, ctx, budgetMs = REFUSAL_PEER_BUDGET_MS, tetherChain = null } = {}) {
  try {
    if (!response || Number(response.status) < 400 || Number(response.status) === 429) return response;
    // R5: a refusal proxied from the runtime is the runtime's own. It seals its refusals itself; never seal twice.
    if (response.headers.get("X-Served-Through") === "AZIEL_RUNTIME" || response.headers.has("X-Azrt-Refusal-Receipt")) return response;
    const method = String((request && request.method) || "GET").toUpperCase();
    if (method === "OPTIONS" || method === "HEAD") return response;
    const ct = response.headers.get("content-type") || "";
    if (!/json/i.test(ct)) return response;
    const text = await response.clone().text();
    if (text.length > 65536) return response;
    let body;
    try { body = JSON.parse(text); } catch { return response; }
    if (!body || typeof body !== "object" || Array.isArray(body)) return response;
    if (body.refusal_receipt != null || body.refused_receipt != null) return response; // sealed upstream
    const reqUrl = new URL(request.url);
    const path = reqUrl.pathname;
    let code = typeof body.code === "string" ? body.code : (typeof body.refuse === "string" ? body.refuse : null);
    if (!code) {
      const st = Number(response.status);
      if (st >= 400 && st < 500 && path.startsWith("/v1/") && (body.ok === false || typeof body.error === "string")) code = `HTTP-${st}-UNCODED`;
    }
    if (!code || !CODE_RE.test(code) || isAuthRefusal(response.status, code)) return response;
    if (tetherChain === "refusals") return response; // never re-seal a refusals-chain tether packet
    const sr = await safeReason(String(body.message || body.error || body.reason || ""), reqUrl);
    let view;
    const bind = env && env.AZIEL_RUNTIME;
    if (!bind || typeof bind.fetch !== "function") {
      view = { kind: "refusal", sealed: false, status: "unavailable", reason: "AZIEL_RUNTIME binding absent", surface };
    } else {
      const call = bind.fetch(new Request(REFUSAL_PEER_URL, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ surface, code, reason: sr.reason, ...(sr.reason_sha256 ? { reason_sha256: sr.reason_sha256 } : {}), method, route: path, status: response.status }) }))
        .then(async (r) => { const j = await r.json().catch(() => null); return j && j.refusal_receipt ? j.refusal_receipt : { kind: "refusal", sealed: false, status: "unavailable", reason: "peer door answered " + r.status + (j && j.code ? " " + j.code : ""), surface }; })
        .catch((e) => ({ kind: "refusal", sealed: false, status: "unavailable", reason: String((e && e.message) || e).slice(0, 120), surface }));
      let timer;
      const timeout = new Promise((r) => { timer = setTimeout(() => r(null), budgetMs); });
      view = await Promise.race([call, timeout]);
      clearTimeout(timer);
      if (!view) {
        if (ctx && typeof ctx.waitUntil === "function") ctx.waitUntil(call);
        view = { kind: "refusal", sealed: false, status: "receipt_pending", reason: `runtime peer door still writing after ${budgetMs} ms; find it at /v1/refusals`, surface };
      }
    }
    const headers = new Headers(response.headers);
    headers.set("X-Azrt-Refusal-Receipt", view.sealed ? `sealed; chain=${view.chain}; seq=${view.seq}; h=${view.h}` : `${view.status || "unavailable"}; sealed=false`);
    headers.delete("content-length");
    return new Response(JSON.stringify({ ...body, refusal_receipt: view }, null, /\n  "/.test(text) ? 2 : 0), { status: response.status, statusText: response.statusText, headers });
  } catch {
    return response; // fail closed: the refusal stands unchanged
  }
}

/** GET /v1/refusals — this surface's refusal receipts, read from the shared runtime chain (read-only). */
export async function peerRefusals(env, { surface, localTip = null } = {}) {
  const bind = env && env.AZIEL_RUNTIME;
  if (!bind || typeof bind.fetch !== "function") return { status: 503, body: { ok: false, code: "REFUSALS-RUNTIME-UNBOUND", surface } };
  let j = null;
  try {
    const r = await bind.fetch(new Request("https://aziel-runtime.vibelock.workers.dev/v1/receipts/refusals?limit=50", { headers: { accept: "application/json" } }));
    j = r.ok ? await r.json() : null;
  } catch { j = null; }
  if (!j || !j.ok) return { status: 503, body: { ok: false, code: "REFUSALS-RUNTIME-UNREACHABLE", surface, fail_closed: true } };
  const mine = (j.receipts || []).filter((x) => x.refusal && x.refusal.surface === surface);
  const rt = j.tip ? { seq: j.tip.seq, primary: j.tip.lattice && j.tip.lattice.primary, secondary: j.tip.lattice && j.tip.lattice.secondary } : null;
  const agree = localTip && rt ? (localTip.primary === rt.primary ? "agree" : "lagging") : (localTip === null ? "no-local-copy" : "unknown");
  return { status: 200, body: { ok: true, spec: "AZRT-REFUSAL-RECEIPT-1.0", surface, chain: "refusals", runtime_tip: rt, local_tip: localTip, tip_state: agree, total: j.total, mine_recent: mine, find_all: "https://aziel-runtime.vibelock.workers.dev/v1/receipts/refusals", verify: "chainlock_verify {\"c\":\"refusals\"} on aziel-runtime", signed: false } };
}
