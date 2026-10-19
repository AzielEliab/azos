/**
 * AZ-LOCKSTEP-1.0 (leg). The vendored shared design + contract match LOCKSTEP.pin.json; locks and
 * flags hold; this leg tethers to the same chains, key, and mesh as the contract; /v1/lockstep fails
 * closed (runtime absent -> standalone, flags false; drift -> 503); every non-gap feature this leg
 * claims answers with the runtime absent. LOCKSTEP_REMOTE=1 also compares the pin with runtime main.
 * Same file on AZInterface and AZ-OS. Author: Aziel Eliab.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const wrangler = readFileSync(root + "wrangler.toml", "utf8");
const LEG = /name\s*=\s*"azos-/.test(wrangler) ? "azos" : "azinterface";
const pin = JSON.parse(readFileSync(root + "LOCKSTEP.pin.json", "utf8"));
const { hashOf, sha256Hex, canonicalize } = await import(root + "vendor/lockstep/consumer.js");
const { PINNED, DESIGN_CSS, TOKENS } = await import(root + "src/lockstep.js");
const { HINTS_HTML } = await import(root + "src/hints.js");
let n = 0;
const ok = (c, m) => { assert.ok(c, m); n++; };

// 1. vendored bytes == pin
for (const [file, h] of Object.entries(pin.files)) {
  ok(createHash("sha256").update(readFileSync(root + file)).digest("hex") === h, `${file} changed after vendoring (re-run aziel-runtime scripts/lockstep-vendor.mjs)`);
}
ok(canonicalize(JSON.parse(readFileSync(root + "vendor/lockstep/lockstep.json", "utf8"))) === canonicalize(PINNED), "pinned.js == lockstep.json");
ok((await hashOf(PINNED.contract)) === pin.contract_sha256 && PINNED.contract_sha256 === pin.contract_sha256, "contract hash");
ok((await hashOf(TOKENS)) === pin.tokens_sha256 && PINNED.tokens_sha256 === pin.tokens_sha256, "tokens hash");
ok((await sha256Hex(DESIGN_CSS)) === pin.css_sha256, "design css hash");
ok((await sha256Hex(HINTS_HTML)) === pin.hints_sha256, "hints popup is the runtime's, byte for byte");

// 1b. nothing host-specific in what this leg vendored: no private / link-local / loopback IPs, no interface names
const PRIVATE_IP = /\b(?:10(?:\.\d{1,3}){3}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|192\.168(?:\.\d{1,3}){2}|169\.254(?:\.\d{1,3}){2}|127(?:\.\d{1,3}){3})\b|\b(?:fe80|fc[0-9a-f]{2}|fd[0-9a-f]{2}):[0-9a-f:]*/i;
const IFACE = /\b(?:enp\d+s\d+|enx[0-9a-f]{12}|ens\d+|eno\d+|eth\d+|wlan\d+|wlp\d+s\d+|docker\d+|veth[0-9a-f]{4,}|br-[0-9a-f]{12}|virbr\d+|wg\d+|tailscale\d+|utun\d+)\b/;
ok(PRIVATE_IP.test("LAN interface enp0s3 at 172.30.0.2") && IFACE.test("enp0s3") && PRIVATE_IP.test("fe80::1") && !PRIVATE_IP.test("203.0.113.9"), "host-data scan catches what it should");
for (const file of Object.keys(pin.files)) {
  const text = readFileSync(root + file, "utf8");
  const ip = text.match(PRIVATE_IP), nic = text.match(IFACE);
  ok(!ip && !nic, `${file} carries host-specific data: ${(ip && ip[0]) || (nic && nic[0])}`);
}

// 2. locks + flags
const c = PINNED.contract;
assert.deepEqual(c.locks, { softwares: 42, mcp_tools: 36, stub_op_count: 363, software_count: 33, health_count: 41 }); n++;
ok(c.runtime.version === "2.0.0-rc1", "runtime version");
for (const [k, v] of Object.entries(c.flags)) ok(v === false, `flag ${k} false`);
ok(c.legs[LEG] && c.legs[LEG].independent === true && c.legs[LEG].optional === true, "this leg is independent + optional");

// 3. same chains, key, mesh
const key = (wrangler.match(/RUNTIME_TETHER_PUBKEY\s*=\s*"([^"]+)"/) || [])[1];
ok(key === c.chains.tether_pubkey, "wrangler RUNTIME_TETHER_PUBKEY == contract tether key");
ok(/\[\[services\]\]\s*binding\s*=\s*"AZIEL_RUNTIME"\s*service\s*=\s*"aziel-runtime"/.test(wrangler), "AZIEL_RUNTIME binding to aziel-runtime");
const sync = readFileSync(root + "src/runtime-sync.js", "utf8");
for (const p of [c.chains.lattice_tip_path, c.chains.tether_status_path, c.mesh.bootstrap_path]) ok(sync.includes("${origin}" + p + "`"), `runtime-sync reads ${p}`);
if (LEG === "azos") {
  const t = await import(root + "src/tether.js");
  const d = "a".repeat(64), prev = "b".repeat(64);
  ok((await t.primaryOf(d, prev)) === (await hashOf({ document: d, prev })), "primary rule");
  ok((await t.onlineSecondaryOf(d, prev)) === (await hashOf({ offline: false, prev, primary: d })), "online secondary rule");
  ok((await t.offlineSecondaryOf(d, "aziel")) === (await hashOf({ primary: d, username: "aziel" })), "offline secondary rule");
  ok(t.canonicalize({ b: 1, a: [true, null, "x"] }) === canonicalize({ b: 1, a: [true, null, "x"] }), "same canonical JSON");
}

// 4. handler: fail closed, standalone
globalThis.fetch = async () => { throw new Error("network off in test: runtime absent"); };
const kv = new Map();
const KV = { get: async (k) => kv.get(k) ?? null, put: async (k, v) => { kv.set(k, v); }, list: async () => ({ keys: [], list_complete: true }), delete: async (k) => { kv.delete(k); } };
const ASSETS = { fetch: async () => new Response("asset", { status: 200 }) };
const baseEnv = { DOWNLOADS: KV, ASSETS, RUNTIME_TETHER_PUBKEY: key, AZIEL_RUNTIME_ORIGIN: "https://aziel-runtime.invalid" };
const worker = (await import(root + "src/" + (LEG === "azos" ? "index.js" : "entry.js"))).default;
const call = async (path, env, method = "GET") => worker.fetch(new Request("https://leg.example" + path, { method, headers: { "user-agent": "Mozilla/5.0", accept: "text/html,application/json" } }), env, { waitUntil() {} });
const bindingFor = (body, status = 200) => ({ fetch: async (req) => (new URL(req.url).pathname === "/v1/lockstep" ? new Response(JSON.stringify(body), { status }) : new Response("{}", { status: 503 })) });

let r = await call("/v1/lockstep", baseEnv);
let b = await r.json();
ok(r.status === 503 && b.state === "absent" && b.standalone === true && b.binding === "absent", "no binding -> absent, standalone");
ok(Object.values(b.flags).every((x) => x === false), "absent -> every flag false");
r = await call("/v1/lockstep", { ...baseEnv, AZIEL_RUNTIME: bindingFor(PINNED) });
b = await r.json();
ok(r.status === 200 && b.state === "agree" && b.tether.ok === true, "runtime serves the pinned contract -> agree");
const moved = structuredClone(PINNED); moved.contract.locks.mcp_tools = 37; moved.contract_sha256 = await hashOf(moved.contract);
r = await call("/v1/lockstep", { ...baseEnv, AZIEL_RUNTIME: bindingFor(moved) });
b = await r.json();
ok(r.status === 503 && b.state === "drift" && b.code === "LOCKSTEP-DRIFT", "runtime moved -> drift");
r = await call("/v1/lockstep", { ...baseEnv, AZIEL_RUNTIME: bindingFor({}, 500) });
ok((await r.json()).state === "absent", "runtime error -> absent");
r = await call("/v1/lockstep", { ...baseEnv, RUNTIME_TETHER_PUBKEY: "someone-else", AZIEL_RUNTIME: bindingFor(PINNED) });
b = await r.json();
ok(b.state === "drift" && b.tether.problems.includes("tether_pubkey"), "wrong tether key -> drift");
r = await call("/design/tokens.css", baseEnv);
ok(r.status === 200 && (await r.text()) === DESIGN_CSS, "/design/tokens.css");

// 5. every non-gap feature on this leg answers with the runtime absent
for (const f of c.features) {
  const here = f.legs[LEG];
  if (!here || here.status === "gap") continue;
  const res = await call(here.route, baseEnv, here.method || "GET");
  ok(res.status !== 404, `${LEG} ${f.id} ${here.route} -> ${res.status} (status ${here.status})`);
  if (here.status === "refused") {
    const body = await res.json();
    ok(body.ok === false && typeof body.code === "string" && body.live === false, `${f.id} refuses with a code, not a mock`);
  }
  if (here.status === "proxied") {
    // Runtime absent must never look like success.
    ok(res.status === 502 || res.status === 503, `${f.id} with the runtime absent -> 502/503 (got ${res.status})`);
    const absent = res.status === 503 ? await res.clone().json().catch(() => null) : null;
    if (absent && absent.code === "LEG-RUNTIME-ABSENT") {
      ok(absent.ok === false && absent.standalone === true && absent.live === false, `${f.id} absent body is honest`);
      const seen = [];
      const through = await call(here.route, { ...baseEnv, AZIEL_RUNTIME: { fetch: async (req) => { seen.push(new URL(req.url).pathname); return new Response("{}", { status: 200 }); } } }, here.method || "GET");
      ok(through.status === 200 && seen.includes(here.route), `${f.id} reads through AZIEL_RUNTIME`);
    }
  }
}

// 6. pages use the shared design
const home = await (await call("/", baseEnv)).text();
ok(home.includes("--az-bg:" + TOKENS.color.bg), "home page carries the shared tokens");
ok(home.includes('id="azrt-hints"') && home.includes("var(--az-warm-panel"), "home page carries the shared hints popup");

// 7. cross-repo drift (network)
if (process.env.LOCKSTEP_REMOTE === "1") {
  const res = await (await import("node:https")).default;
  const body = await new Promise((resolve, reject) => res.get("https://raw.githubusercontent.com/AzielEliab/aziel-runtime/main/contract/lockstep.json", (m) => { let s = ""; m.on("data", (d) => (s += d)); m.on("end", () => (m.statusCode === 200 ? resolve(s) : reject(new Error("runtime main has no contract/lockstep.json: " + m.statusCode)))); }).on("error", reject));
  const main = JSON.parse(body);
  assert.equal(main.contract_sha256, pin.contract_sha256, "runtime main moved the contract: re-vendor"); n++;
  assert.equal(main.tokens_sha256, pin.tokens_sha256, "runtime main moved the design tokens: re-vendor"); n++;
}
console.log(`ok ${LEG} lockstep: ${n} checks (contract ${pin.contract_sha256.slice(0, 12)})`);
