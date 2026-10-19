/**
 * AGENT-SUBNET-1.0, peer side (read-only viewer). The runtime keeps the one `agentcomms` chain
 * (hash-only agent communication receipts, dual lattice). This tracker shows it two ways:
 *   GET  /v1/agents/receipts  public aggregate counts + the runtime tip, compared with this side's copy
 *   POST /v1/agents/receipts  forwards a signed agent-view statement (public key + signature only) to the
 *                             runtime over the AZIEL_RUNTIME service binding; only rows that involve the
 *                             proved agent or owner come back.
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

function bindOf(env) {
  const b = env && env.AZIEL_RUNTIME;
  return b && typeof b.fetch === "function" ? b : null;
}

export async function agentsPublic(env, { surface, localTip = null } = {}) {
  const bind = bindOf(env);
  if (!bind) return { status: 503, body: { ok: false, code: "AGENTS-RUNTIME-UNBOUND", spec: AGENTS_SPEC, surface, fail_closed: true, ...HONEST } };
  let j = null;
  try {
    const r = await bind.fetch(new Request(AGENTS_RUNTIME + "/v1/mesh/agents/receipts", { headers: { accept: "application/json" } }));
    j = r.ok ? await r.json() : null;
  } catch { j = null; }
  if (!j || !j.ok) return { status: 503, body: { ok: false, code: "AGENTS-RUNTIME-UNREACHABLE", spec: AGENTS_SPEC, surface, fail_closed: true, ...HONEST } };
  const rt = j.tip ? { seq: j.tip.seq, primary: j.tip.lattice && j.tip.lattice.primary, secondary: j.tip.lattice && j.tip.lattice.secondary } : null;
  const tip_state = localTip && rt ? (localTip.primary === rt.primary ? "agree" : "lagging") : (localTip === null ? "no-local-copy" : "unknown");
  return {
    status: 200,
    body: {
      ok: true, spec: AGENTS_SPEC, surface, chain: "agentcomms", scope: "public",
      total: j.total, by_kind: j.by_kind, e2e_verified_observed: j.e2e_verified_observed,
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
  try {
    const r = await bind.fetch(new Request(AGENTS_RUNTIME + "/v1/mesh/agents/receipts", { method: "POST", headers: { "content-type": "application/json", accept: "application/json" }, body: JSON.stringify(body) }));
    const j = await r.json().catch(() => null);
    if (!j) return refuse(503, "AGENTS-RUNTIME-UNREACHABLE", "The runtime did not answer with JSON.");
    return { status: r.status, body: { ...j, surface, via: "AZIEL_RUNTIME binding" } };
  } catch {
    return refuse(503, "AGENTS-RUNTIME-UNREACHABLE", "The runtime could not be reached.");
  }
}

/** Panel markup + script (text nodes only; no key input). Mount inside a page; `api` is this tracker's route. */
export function agentsPanelHtml({ api = "/v1/agents/receipts", idPrefix = "ag" } = {}) {
  const p = idPrefix;
  return `<div id="${p}-panel">
<p class="note">AI agents talk to other agents with signed, end-to-end sealed messages (AGENT-SUBNET-1.0). Every message, grant, and refusal leaves a hash-only receipt on the runtime's <code>agentcomms</code> chain, one lattice shared with this side. live: false until two real, independent agents exchange a verified message end to end.</p>
<pre id="${p}-pub">Loading public counts…</pre>
<p class="note">See your own agents' rows: run <code>node scripts/agent-subnet-client.mjs view &lt;agent&gt; --print</code> on your machine and paste the signed statement. It has a public key and a signature, never a private key. Do not paste keys.</p>
<textarea id="${p}-stmt" rows="6" style="width:100%" placeholder='{"v":"AGENT-SUBNET-1.0","kind":"agent-view",...}'></textarea>
<div class="row"><button type="button" class="act" id="${p}-go">Show my receipts</button></div>
<p id="${p}-msg"></p><table style="width:100%;font-size:.8rem"><thead><tr><th>seq</th><th>time</th><th>kind</th><th>ct sha256</th><th>verdict</th><th>carrier</th></tr></thead><tbody id="${p}-rows"></tbody></table>
<script>(function(){var A=${JSON.stringify(api)},P=${JSON.stringify(p)};function $(s){return document.getElementById(P+"-"+s)}
fetch(A).then(function(r){return r.json()}).then(function(j){$("pub").textContent=JSON.stringify({live:j.live,total:j.total,by_kind:j.by_kind,e2e_verified_observed:j.e2e_verified_observed,tip_state:j.tip_state,runtime_tip:j.runtime_tip},null,2)}).catch(function(){$("pub").textContent="unreachable (fail closed: no claim)"});
$("go").onclick=function(){var tb=$("rows");tb.textContent="";var b;try{b=JSON.parse($("stmt").value)}catch(e){$("msg").textContent="That is not JSON.";return}
fetch(A,{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify(b)}).then(function(r){return r.json()}).then(function(j){if(!j.ok){$("msg").textContent=(j.code||"refused")+": "+(j.message||"");return}
$("msg").textContent=j.matched+" receipt(s) involve you.";(j.receipts||[]).forEach(function(row){var a=row.agentcomm||{},tr=document.createElement("tr");[row.seq,row.t,a.kind,a.ct_sha256||"",a.recipient_verdict||a.sig_verdict||a.code||"",a.carrier||""].forEach(function(v){var td=document.createElement("td");td.textContent=String(v==null?"":v);tr.appendChild(td)});tb.appendChild(tr)})})}})();</script>
</div>`;
}
