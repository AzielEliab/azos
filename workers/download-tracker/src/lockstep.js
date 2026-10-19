/**
 * AZ-LOCKSTEP-1.0 (leg side). GET /v1/lockstep, GET /design/tokens.css, GET /design/tokens.json.
 * This leg is independent and optional: it serves its own vendored, hash-pinned copy of the shared
 * design and contract, and compares the pin with the runtime over the AZIEL_RUNTIME service binding.
 * Runtime absent -> state "absent", standalone true, every displayed flag false. Never writes.
 * Same file on AZInterface and AZ-OS. Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
 */
import { verifyLockstep, LOCKSTEP_PATH } from "../vendor/lockstep/consumer.js";
import { tokensCss } from "../vendor/lockstep/tokens-css.js";
import { PINNED } from "../vendor/lockstep/pinned.js";
import { TOKENS } from "../vendor/lockstep/tokens.js";

export const DESIGN_CSS = tokensCss(TOKENS);
export { PINNED, TOKENS };

const JSON_HEADERS = { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "Access-Control-Allow-Origin": "*" };

export function runtimeBinding(env) {
  return env && env.AZIEL_RUNTIME && typeof env.AZIEL_RUNTIME.fetch === "function" ? env.AZIEL_RUNTIME : null;
}

export async function lockstepStatus(env, { leg, legProof = {}, local = {}, timeoutMs = 4000 } = {}) {
  const bind = runtimeBinding(env);
  const fetchDoc = async () => {
    if (!bind) return null;
    const r = await bind.fetch(new Request("https://aziel-runtime.internal" + LOCKSTEP_PATH, { headers: { accept: "application/json" } }));
    return r && r.ok ? r.json() : null;
  };
  const out = await verifyLockstep({ leg, pinned: PINNED, fetchDoc, legProof, local, timeoutMs });
  return { ...out, binding: bind ? "AZIEL_RUNTIME" : "absent", features: PINNED.contract.features.map((f) => ({ id: f.id, here: f.legs[leg] })) };
}

/** Returns a Response for a lockstep route, or null when the path is not one. */
export async function handleLockstepRoute(request, env, opts) {
  if (request.method !== "GET" && request.method !== "HEAD") return null;
  const path = new URL(request.url).pathname.replace(/\/+$/, "") || "/";
  const head = request.method === "HEAD";
  if (path === "/design/tokens.css") {
    return new Response(head ? null : DESIGN_CSS, { status: 200, headers: { "Content-Type": "text/css; charset=utf-8", "Cache-Control": "public, max-age=300", "Access-Control-Allow-Origin": "*" } });
  }
  if (path === "/design/tokens.json") {
    return new Response(head ? null : JSON.stringify(TOKENS, null, 2), { status: 200, headers: JSON_HEADERS });
  }
  if (path === LOCKSTEP_PATH) {
    const out = await lockstepStatus(env, opts);
    // 200 on agree; 503 when absent or drifted, so a monitor sees it. The leg keeps serving everything else.
    return new Response(head ? null : JSON.stringify(out, null, 2), { status: out.state === "agree" ? 200 : 503, headers: JSON_HEADERS });
  }
  return null;
}
