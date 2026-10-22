// USER-SIGNIN-ARK-1.0 §12.3: this leg's /v1/ark/account forwards only hashed/signed logins.
import assert from "node:assert/strict";
import { handleArkAccount, hasCredentialKey } from "../src/ark-door.js";
let n = 0; const ok = (c, m) => { assert.ok(c, m); n++; };
const seen = [];
const env = { AZIEL_RUNTIME: { fetch: async (req) => { const b = await req.json(); seen.push({ ...b, path: new URL(req.url).pathname, vh: req.headers.get("x-azrt-visitor-ip-h") }); return new Response(JSON.stringify({ ok: b.op === "account_challenge", code: b.op === "account_challenge" ? "ARK-OK" : "ARK-ACCOUNTS-OFF", spec: "ARK-ACCOUNT-1.0" }), { status: b.op === "account_challenge" ? 200 : 400 }); } } };
const go = (body, method = "POST") => { const r = new Request("https://leg/v1/ark/account", { method, headers: { "content-type": "application/json" }, body: method === "POST" ? JSON.stringify(body) : undefined }); return handleArkAccount(r, new URL(r.url), env, "azos"); };
ok((await handleArkAccount(new Request("https://leg/other"), new URL("https://leg/other"), env, "azos")) === null, "other paths untouched");
let r = await go({ op: "account_challenge", payload: { vault_pub: "a".repeat(64) } });
ok(r.status === 200 && r.body.code === "ARK-OK" && seen[0].path === "/v1/ark/account" && seen[0].op === "account_challenge", "forwards signed/hashed login to runtime FragGate");
for (const bad of [{ op: "account_open", username: "u" }, { op: "account_open", payload: { Password: "x" } }, { op: "account_open", payload: { deep: [{ PASSPHRASE: "x" }] } }]) {
  const before = seen.length;
  r = await go(bad);
  ok(r.body.code === "ARK-PLAINTEXT-REFUSED" && seen.length === before, "plaintext refused locally, never forwarded");
}
r = await go({ op: "scorch" }); ok(r.body.code === "ARK-INPUT", "only account_* ops");
r = await go(null, "GET"); ok(r.status === 405, "POST only");
r = await go({ op: "account_open", payload: {} }); ok(r.body.code === "ARK-ACCOUNTS-OFF", "runtime flag (default OFF) passes through");
const boom = { AZIEL_RUNTIME: { fetch: async () => new Response("nope") } };
const rq = new Request("https://leg/v1/ark/account", { method: "POST", body: JSON.stringify({ op: "account_open" }) });
r = await handleArkAccount(rq, new URL(rq.url), boom, "azos"); ok(r.body.code === "ARK-FAIL-CLOSED", "bad upstream fails closed");
const rq2 = new Request("https://leg/v1/ark/account", { method: "POST", body: "{}" });
r = await handleArkAccount(rq2, new URL(rq2.url), {}, "azos"); ok(r.status === 503 && r.body.code === "LEG-RUNTIME-ABSENT", "runtime absent → 503");
ok(hasCredentialKey({ a: { b: { c: { d: { e: { f: { g: { h: 1 } } } } } } } }), "too deep fails closed");
for (const k of ["pass_word", "pass-word", "passWord", "PASS_WORD", "user-name", "userName", "pass word"]) {
  const before = seen.length;
  r = await go({ op: "account_open", payload: { [k]: "x" } });
  ok(r.body.code === "ARK-PLAINTEXT-REFUSED" && seen.length === before, "separator variant refused: " + k);
}
{
  const rq3 = new Request("https://leg/v1/ark/account", { method: "POST", headers: { "cf-connecting-ip": "198.51.100.7" }, body: JSON.stringify({ op: "account_challenge", payload: {} }) });
  const before = seen.length;
  await handleArkAccount(rq3, new URL(rq3.url), env, "workers");
  const rq4 = new Request("https://leg/v1/ark/account", { method: "POST", headers: { "cf-connecting-ip": "198.51.100.8" }, body: JSON.stringify({ op: "account_challenge", payload: {} }) });
  await handleArkAccount(rq4, new URL(rq4.url), env, "workers");
  const a = seen[before].vh, b2 = seen[before + 1].vh;
  ok(/^[a-f0-9]{16,64}$/.test(a || "") && a !== b2 && !String(a).includes("198.51"), "visitor IP forwarded hashed, per visitor");
}
console.log(`verify-ark-door: ${n} checks ok`);
