/**
 * AGENT-SUBNET-1.0, peer side (read-only viewer). The runtime keeps the one `agentcomms` chain
 * (hash-only agent communication receipts, dual lattice). This tracker shows it two ways:
 *   GET  /v1/agents/receipts  public aggregate counts + the runtime tip, compared with this side's copy
 *   POST /v1/agents/receipts  forwards a signed agent-view statement (public key + signature only) to the
 *                             runtime over the AZIEL_RUNTIME service binding; only rows that involve the
 *                             proved agent or owner come back.
 * Every runtime call has a timeout (AGENTS_RUNTIME_TIMEOUT_MS, 250..10000, default 4000) and answers
 * AGENTS-RUNTIME-TIMEOUT when it runs out, never a hang. The visitor's IP is forwarded only as a hash
 * (x-azrt-visitor-ip-h = sha256("agent-ip|"+ip)[:32], the runtime's own spec) so the runtime's
 * limiters key per visitor instead of one shared "binding" bucket; the raw IP never leaves here.
 * Nothing here writes, signs, or holds a key. A body with a private-key-shaped field is refused here and
 * never forwarded. Fails closed: no binding or an unreachable runtime gives ok:false and no claims.
 * live stays false (runtime rule: two real independent agents, verified end to end, operator-checked).
 * Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
 */
export const AGENTS_SPEC = "AGENT-SUBNET-1.0";
export const AGENTS_RUNTIME = "https://aziel-runtime.vibelock.workers.dev";
export const AGENTS_BODY_MAX = 8192;
const VIEW_KEYS = ["v", "kind", "scope", "subject_public_key", "challenge", "t", "nonce", "sig"];
const HONEST = Object.freeze({ live: false, writes: false, holds_keys: false, relay_sees_plaintext: false });
export const AGENTS_TIMEOUT_DEFAULT_MS = 4000;

/** Timeout (ms). AGENTS_RUNTIME_TIMEOUT_MS clamps to 250..10000; default 4000. */
export function agentsTimeoutMs(env) {
  const v = Number(env && env.AGENTS_RUNTIME_TIMEOUT_MS);
  if (!Number.isFinite(v) || v <= 0) return AGENTS_TIMEOUT_DEFAULT_MS;
  return Math.min(10000, Math.max(250, Math.floor(v)));
}

/** sha256("agent-ip|"+ip)[:32] of the visitor's cf-connecting-ip, or null. Same spec as the runtime. */
export async function visitorIpHash(request) {
  const ip = request && request.headers ? String(request.headers.get("cf-connecting-ip") || "").trim() : "";
  if (!ip) return null;
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("agent-ip|" + ip));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 32);
}

/** One runtime call: abort + race against the budget. Returns { r } or { timeout: true } or { error: true }. */
async function callRuntime(bind, req, ms) {
  const ctl = typeof AbortController === "function" ? new AbortController() : null;
  let timer;
  const late = new Promise((res) => { timer = setTimeout(() => { if (ctl) ctl.abort(); res({ timeout: true }); }, ms); });
  try {
    const call = (async () => {
      const r = await bind.fetch(ctl ? new Request(req, { signal: ctl.signal }) : req);
      const j = await r.json().catch(() => null);
      return { r, j };
    })().catch(() => ({ error: true }));
    return await Promise.race([call, late]);
  } finally {
    clearTimeout(timer);
  }
}

function bindOf(env) {
  const b = env && env.AZIEL_RUNTIME;
  return b && typeof b.fetch === "function" ? b : null;
}

export async function agentsPublic(env, { surface, localTip = null } = {}) {
  const bind = bindOf(env);
  if (!bind) return { status: 503, body: { ok: false, code: "AGENTS-RUNTIME-UNBOUND", spec: AGENTS_SPEC, surface, fail_closed: true, ...HONEST } };
  const ms = agentsTimeoutMs(env);
  const got = await callRuntime(bind, new Request(AGENTS_RUNTIME + "/v1/mesh/agents/receipts", { headers: { accept: "application/json" } }), ms);
  if (got.timeout) return { status: 503, body: { ok: false, code: "AGENTS-RUNTIME-TIMEOUT", timeout_ms: ms, spec: AGENTS_SPEC, surface, fail_closed: true, ...HONEST } };
  const j = got.r && got.r.ok ? got.j : null;
  if (!j || !j.ok) return { status: 503, body: { ok: false, code: "AGENTS-RUNTIME-UNREACHABLE", spec: AGENTS_SPEC, surface, fail_closed: true, ...HONEST } };
  const rt = j.tip ? { seq: j.tip.seq, primary: j.tip.lattice && j.tip.lattice.primary, secondary: j.tip.lattice && j.tip.lattice.secondary } : null;
  const tip_state = localTip && rt ? (localTip.primary === rt.primary ? "agree" : "lagging") : (localTip === null ? "no-local-copy" : "unknown");
  return {
    status: 200,
    body: {
      ok: true, spec: AGENTS_SPEC, surface, chain: "agentcomms", scope: "public",
      total: j.total, by_kind: j.by_kind, e2e_verified_observed: j.e2e_verified_observed,
      counts: j.counts || "bucketed", k_min: j.k_min, refresh: j.refresh || "hourly", as_of: j.as_of || null,
      runtime_tip: rt, local_tip: localTip, tip_state,
      verify: 'chainlock_verify {"c":"agentcomms"} on aziel-runtime', owner_view: "POST a signed agent-view statement here (scripts/agent-subnet-client.mjs view <agent> --print)",
      source: AGENTS_RUNTIME + "/v1/mesh/agents/receipts", ...HONEST,
    },
  };
}

export async function agentsScoped(env, request, { surface } = {}) {
  const bind = bindOf(env);
  const refuse = (status, code, message) => ({ status, body: { ok: false, code, message, spec: AGENTS_SPEC, surface, ...HONEST } });
  let text = "";
  try { text = await request.text(); } catch { text = ""; }
  if (!text || text.length > AGENTS_BODY_MAX) return refuse(400, "AGENTS-BAD-VIEW", "Send one signed agent-view statement as JSON.");
  let body;
  try { body = JSON.parse(text); } catch { return refuse(400, "AGENTS-BAD-VIEW", "Send one signed agent-view statement as JSON."); }
  if (!body || typeof body !== "object" || Array.isArray(body)) return refuse(400, "AGENTS-BAD-VIEW", "Send one signed agent-view statement as JSON.");
  if (Object.keys(body).some((k) => /private|seed|secret/i.test(k))) return refuse(400, "AGENTS-PRIVATE-KEY", "Private keys stay on the agent. Nothing was forwarded.");
  if (body.kind !== "agent-view" || Object.keys(body).some((k) => !VIEW_KEYS.includes(k))) return refuse(400, "AGENTS-BAD-VIEW", "Only a signed agent-view statement is forwarded.");
  if (!bind) return refuse(503, "AGENTS-RUNTIME-UNBOUND", "The AZIEL_RUNTIME binding is absent. Nothing was forwarded.");
  const headers = { "content-type": "application/json", accept: "application/json" };
  const vh = await visitorIpHash(request).catch(() => null);
  if (vh) headers["x-azrt-visitor-ip-h"] = vh;
  const ms = agentsTimeoutMs(env);
  const got = await callRuntime(bind, new Request(AGENTS_RUNTIME + "/v1/mesh/agents/receipts", { method: "POST", headers, body: JSON.stringify(body) }), ms);
  if (got.timeout) return { status: 503, body: { ok: false, code: "AGENTS-RUNTIME-TIMEOUT", timeout_ms: ms, message: `The runtime did not answer within ${ms} ms. Nothing was shown.`, spec: AGENTS_SPEC, surface, fail_closed: true, ...HONEST } };
  if (got.error) return refuse(503, "AGENTS-RUNTIME-UNREACHABLE", "The runtime could not be reached.");
  if (!got.j) return refuse(503, "AGENTS-RUNTIME-UNREACHABLE", "The runtime did not answer with JSON.");
  return { status: got.r.status, body: { ...got.j, surface, via: "AZIEL_RUNTIME binding" } };
}

/** Panel markup + script (text nodes only; no key input). Mount inside a page; `api` is this tracker's route. */
export function agentsPanelHtml({ api = "/v1/agents/receipts", idPrefix = "ag" } = {}) {
  const p = idPrefix;
  return `<div id="${p}-panel">
<p class="note">AGENT-SUBNET-1.0 is designed to let AI agents talk to other agents with signed messages that are sealed on the agent. Each message, grant, and refusal is designed to leave a hash-only receipt (hashed, not encrypted) on the runtime's <code>agentcomms</code> chain, one lattice shared with this side. Public counts are bucketed (under 10 shows as &lt;10) and refresh hourly. live: false: not yet proven between two real, independent agents.</p>
<pre id="${p}-pub">Loading public counts…</pre>
<p class="note">See your own agents' rows: run <code>node scripts/agent-subnet-client.mjs view &lt;agent&gt; --print</code> on your machine and paste the signed statement (its challenge is bound to your key and scope, and works once). It has a public key and a signature, never a private key. Do not paste keys.</p>
<textarea id="${p}-stmt" rows="6" style="width:100%" placeholder='{"v":"AGENT-SUBNET-1.0","kind":"agent-view",...}'></textarea>
<div class="row"><button type="button" class="act" id="${p}-go">Show my receipts</button></div>
<p id="${p}-msg"></p><table style="width:100%;font-size:.8rem"><thead><tr><th>seq</th><th>time</th><th>kind</th><th>ct sha256</th><th>verdict</th><th>carrier</th></tr></thead><tbody id="${p}-rows"></tbody></table>
<script>(function(){var A=${JSON.stringify(api)},P=${JSON.stringify(p)};function $(s){return document.getElementById(P+"-"+s)}
fetch(A).then(function(r){return r.json()}).then(function(j){$("pub").textContent=j.ok?JSON.stringify({live:j.live,total:j.total,by_kind:j.by_kind,e2e_verified_observed:j.e2e_verified_observed,refresh:j.refresh,as_of:j.as_of,tip_state:j.tip_state,runtime_tip:j.runtime_tip},null,2):((j.code||"unavailable")+" (fail closed: no claim)")}).catch(function(){$("pub").textContent="unreachable (fail closed: no claim)"});
$("go").onclick=function(){var tb=$("rows");tb.textContent="";var b;try{b=JSON.parse($("stmt").value)}catch(e){$("msg").textContent="That is not JSON.";return}
fetch(A,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(b)}).then(function(r){return r.json()}).then(function(j){if(!j.ok){$("msg").textContent=(j.code||"refused")+": "+(j.message||"");return}
$("msg").textContent=j.matched+" receipt(s) involve you.";(j.receipts||[]).forEach(function(row){var a=row.agentcomm||{},tr=document.createElement("tr");[row.seq,row.t,a.kind,a.ct_sha256||"",a.recipient_verdict||a.sig_verdict||a.code||"",a.carrier||""].forEach(function(v){var td=document.createElement("td");td.textContent=String(v==null?"":v);tr.appendChild(td)});tb.appendChild(tr)})})}})();</script>
</div>`;
}
