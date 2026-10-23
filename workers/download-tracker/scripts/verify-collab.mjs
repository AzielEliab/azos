/**
 * AZBOT-NODE-COLLAB-1.0: session tip read is share-only.
 * Rewrite is refused. GET mesh is not enabled from this module.
 * Author: Aziel Eliab.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const src = readFileSync(root + "src/collab.js", "utf8");
assert.equal(/\/v1\/mesh\/enable|AZIEL_RUNTIME\.fetch|receiveTether|mesh\.js/.test(src), false, "collab does not enable mesh or exec a tether write");
assert.equal(src.includes("get_mesh_enables: GET_MESH_ENABLES"), true);
assert.equal(src.includes("OPERATOR-OVERRIDE lives"), true);
assert.equal(src.includes("not ICANN"), true);

const { handleCollabRoute, GET_MESH_ENABLES, REWRITES_QNM_FLAGS, PUBLIC_MESH_ENABLE_INVENTED, sessionTipView } = await import("../src/collab.js");
assert.equal(GET_MESH_ENABLES, false);
assert.equal(REWRITES_QNM_FLAGS, false);
assert.equal(PUBLIC_MESH_ENABLE_INVENTED, false);

const kv = new Map();
const env = {
  DOWNLOADS: {
    get: async (k) => kv.get(k) ?? null,
    put: async (k, v) => { kv.set(k, v); },
  },
  RUNTIME_TETHER_PUBKEY: "test-key",
};
const call = (path, method = "GET") => handleCollabRoute(
  new Request("https://leg.example" + path, { method, headers: { "user-agent": "Mozilla/5.0" } }),
  new URL("https://leg.example" + path),
  env,
);

let out = await call("/v1/collab/tip");
assert.equal(out.status, 200);
assert.equal(out.body.ok, true);
assert.equal(out.body.tip, null);
assert.equal(out.body.rewrite, false);
assert.equal(out.body.written, false);
assert.equal(out.body.parties_can_rewrite, false);
assert.equal(out.body.get_mesh_enables, false);
assert.equal(out.body.public_mesh_enable_invented, false);
assert.equal(out.body.rewrites_qnm_flags, false);
assert.equal(out.body.mesh_node_live, true);
assert.equal(out.body.alt_internet_live, true);
assert.equal(out.body.packet_path_live, true);
assert.equal(out.body.public_bind, false);
assert.equal(out.body.public_exec, "refused");
assert.equal(out.body.public_shell, "refused");
assert.equal(out.body.public_lattice, "refused");
assert.equal(out.body.vault_wipe, "local-only");
assert.equal(out.body.vault_scorch, "local-only");
assert.equal(out.body.vault_unlock, "local-only");
assert.equal(out.body.vault_public, "FG-STUB");
assert.equal(out.body.public_door, "FG-STUB");
assert.equal(out.body.cap7_is_path, false);
assert.equal(out.body.public_icann, false);
assert.equal(out.body.bgp, false);
assert.equal(Object.hasOwn(out.body, "auto_heal"), false);
assert.equal(Object.hasOwn(out.body, "node_gate"), false);
assert.match(out.body.cap7_note, /not ICANN or BGP/);

const primary = "a".repeat(64);
const secondary = "b".repeat(64);
const view = sessionTipView({
  chains: [{
    chain: "session",
    tips: { primary, secondary, document: "must-not-leak" },
    rows: 4,
    verified: true,
  }, {
    chain: "other",
    tips: { primary: "c".repeat(64), secondary: "d".repeat(64) },
    rows: 9,
    verified: true,
  }],
});
assert.deepEqual(view.tip, { chain: "session", primary, secondary, seq: 4, verified: true });
assert.equal(JSON.stringify(view).includes("must-not-leak"), false);
assert.equal(JSON.stringify(view).includes("c".repeat(64)), false);
assert.equal(JSON.stringify(view).includes("d".repeat(64)), false);

out = await call("/v1/collab/tip", "POST");
assert.equal(out.status, 403);
assert.equal(out.body.ok, false);
assert.equal(out.body.code, "COLLAB-REWRITE-REFUSED");
assert.equal(out.body.written, false);
assert.equal(out.body.rewrite, false);
assert.equal(out.body.live, false);

out = await call("/v1/collab/handoff", "POST");
assert.equal(out.status, 403);
assert.equal(out.body.code, "COLLAB-REWRITE-REFUSED");

const worker = (await import("../src/index.js")).default;
const res = await worker.fetch(
  new Request("https://leg.example/v1/collab/tip", { headers: { "user-agent": "Mozilla/5.0", accept: "application/json" } }),
  env,
  { waitUntil() {} },
);
assert.equal(res.status, 200);
const body = await res.json();
assert.equal(body.ok, true);
assert.equal(body.tip, null);
assert.equal(body.mesh_node_live, true);
assert.equal(body.alt_internet_live, true);
assert.equal(body.packet_path_live, true);
assert.equal(body.public_bind, false);
assert.equal(body.get_mesh_enables, false);
assert.equal(body.rewrite, false);

const refused = await worker.fetch(
  new Request("https://leg.example/v1/collab/tip", { method: "POST", headers: { "user-agent": "Mozilla/5.0" } }),
  env,
  { waitUntil() {} },
);
assert.equal(refused.status, 403);
const refusedBody = await refused.json();
assert.equal(refusedBody.code, "COLLAB-REWRITE-REFUSED");
assert.equal(refusedBody.written, false);

console.log("ok azos collab: session tip is share-only; rewrite refused; mesh enable not invented");
