/**
 * USER-SIGNIN-ARK-1.0 §12.3: POST /v1/ark/account on this leg's Worker.
 * Forwards ONLY the hashed/signed login (vault_pub, nonce, user_sig, session, ciphertext)
 * to aziel-runtime POST /v1/ark/account (FragGate ark account_*) over the AZIEL_RUNTIME binding. Any username/password-looking
 * key is refused here (ARK-PLAINTEXT-REFUSED) and never forwarded. The runtime still
 * applies ARK_ACCOUNTS (default OFF). Fails closed. Author: Aziel Eliab.
 * SPDX-License-Identifier: Apache-2.0
 */
export const ARK_ROUTE = "/v1/ark/account";
export const ARK_ROUTE_OPS = Object.freeze(["account_open", "account_append", "account_recall", "account_challenge", "account_session"]);
const MAX_BODY = 65536;
const CRED = new Set(["username", "user", "user_name", "login", "uname", "password", "pass", "passphrase", "passwd", "pwd", "pw", "secret"]);
const norm = (k) => String(k).toLowerCase().replace(/[^a-z_]/g, "");

export function hasCredentialKey(v, depth = 0) {
  if (depth > 6) return true; // too deep: fail closed
  if (!v || typeof v !== "object") return false;
  if (Array.isArray(v)) return v.some((x) => hasCredentialKey(x, depth + 1));
  return Object.entries(v).some(([k, x]) => CRED.has(norm(k)) || hasCredentialKey(x, depth + 1));
}

const out = (code, status = 400) => ({ status, body: { ok: false, code, spec: "ARK-ACCOUNT-1.0", door: ARK_ROUTE, written: false } });

export async function handleArkAccount(request, url, env, leg) {
  if (url.pathname !== ARK_ROUTE) return null;
  if (request.method !== "POST") return out("ARK-METHOD", 405);
  const binding = env && env.AZIEL_RUNTIME && typeof env.AZIEL_RUNTIME.fetch === "function" ? env.AZIEL_RUNTIME : null;
  if (!binding) {
    return { status: 503, body: { ok: false, code: "LEG-RUNTIME-ABSENT", leg, path: ARK_ROUTE, standalone: true, live: false, written: false, plain: "The runtime is not reachable from this leg right now. Nothing ran." } };
  }
  try {
    const raw = await request.text();
    if (raw.length > MAX_BODY) return out("ARK-INPUT", 413);
    let body = {};
    if (raw.trim()) {
      try { body = JSON.parse(raw); } catch { return out("ARK-INPUT"); }
    }
    if (!body || typeof body !== "object" || Array.isArray(body)) return out("ARK-INPUT");
    if (hasCredentialKey(body)) return out("ARK-PLAINTEXT-REFUSED");
    const op = body.op === undefined ? undefined : String(body.op);
    if (op !== undefined && !ARK_ROUTE_OPS.includes(op)) return out("ARK-INPUT");
    const payload = body.payload && typeof body.payload === "object" && !Array.isArray(body.payload) ? body.payload : {};
    const fwd = { method: "POST", headers: { "content-type": "application/json", accept: "application/json", "user-agent": `Mozilla/5.0 (${leg}-ark-door)` }, body: JSON.stringify({ op, payload }) };
    const res = await binding.fetch(new Request("https://aziel-runtime" + ARK_ROUTE, fwd));
    let j;
    try { j = await res.json(); } catch { return out("ARK-FAIL-CLOSED", 502); }
    if (!j || typeof j !== "object") return out("ARK-FAIL-CLOSED", 502);
    return { status: res.status, body: { ...j, via: leg } };
  } catch {
    return out("ARK-FAIL-CLOSED", 502);
  }
}
