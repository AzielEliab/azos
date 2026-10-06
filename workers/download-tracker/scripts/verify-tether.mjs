/**
 * AZ-OS side of AZRT-AZOS-TETHER-1.0.
 * The tracker verifies and stores signed dual-lattice tips from aziel-runtime.
 * scripts/fixtures/azos-tether-vector.json is copied from the aziel-runtime repo
 * (fixtures/azos-tether-vector.json). It is signed with a public test-only seed.
 * Author: Aziel Eliab. Identity is Aziel Eliab only.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import worker from "../src/index.js";
import { canonicalize, checkPacket, offlineSecondaryOf, onlineSecondaryOf, primaryOf, GENESIS } from "../src/tether.js";

const vector = JSON.parse(readFileSync(new URL("./fixtures/azos-tether-vector.json", import.meta.url), "utf8"));
const TEST_KEY = vector.test_public_key;
const TEST_SEED = "11".repeat(32); // the same public test-only seed the runtime vector uses

function fakeKv() {
  const map = new Map();
  let writes = 0;
  return {
    map,
    get writes() { return writes; },
    async get(k) { return map.has(k) ? map.get(k) : null; },
    async put(k, v) { writes += 1; map.set(k, String(v)); },
    async delete(k) { map.delete(k); },
    async list() { return { keys: [...map.keys()].map((name) => ({ name })) }; },
  };
}

const origin = "https://azos-download-tracker.vibelock.workers.dev";
async function call(env, path, init = {}) {
  const res = await worker.fetch(new Request(origin + path, { headers: { "user-agent": "Mozilla/5.0", ...(init.headers || {}) }, ...init }), env, { waitUntil() {} });
  let body = null;
  try { body = await res.json(); } catch { body = null; }
  return { status: res.status, body };
}
const post = (env, packet) => call(env, "/v1/tether/tip", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(packet) });

const ED_PKCS8_PREFIX = Uint8Array.from([0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x70, 0x04, 0x22, 0x04, 0x20]);
async function signWithTestSeed(packet) {
  const seed = Uint8Array.from(Buffer.from(TEST_SEED, "hex"));
  const pkcs8 = new Uint8Array(48);
  pkcs8.set(ED_PKCS8_PREFIX, 0);
  pkcs8.set(seed, 16);
  const key = await crypto.subtle.importKey("pkcs8", pkcs8, { name: "Ed25519" }, false, ["sign"]);
  const { sig: _omit, ...unsigned } = packet;
  const sig = new Uint8Array(await crypto.subtle.sign("Ed25519", key, new TextEncoder().encode(canonicalize(unsigned))));
  return { ...unsigned, sig: Buffer.from(sig).toString("base64url") };
}

// --- 0. Before any push: nothing stored, not updated ----------------------------
{
  const env = { DOWNLOADS: fakeKv(), RUNTIME_TETHER_PUBKEY: TEST_KEY };
  const st = await call(env, "/v1/tether");
  assert.equal(st.status, 200);
  assert.equal(st.body.stored_chains, 0);
  assert.equal(st.body.azos_updated, false);
  assert.equal(st.body.key_pinned, true);
  assert.equal(st.body.mesh_node_live, false);
  assert.equal(st.body.second_device, false);
  assert.equal(st.body.booted, false);
}

// --- 1. Runtime vector verifies and stores ---------------------------------------
const env = { DOWNLOADS: fakeKv(), RUNTIME_TETHER_PUBKEY: TEST_KEY };
const [p1, p2] = vector.packets;
const r1 = await post(env, p1);
assert.equal(r1.status, 200, JSON.stringify(r1.body));
assert.equal(r1.body.stored, true);
assert.equal(r1.body.verified, true);
assert.equal(r1.body.rows_accepted, 2);
const r2 = await post(env, p2);
assert.equal(r2.status, 200, JSON.stringify(r2.body));
assert.deepEqual(r2.body.tips, vector.final_tips);
assert.equal(r2.body.rows, 3);
const st = await call(env, "/v1/tether");
assert.equal(st.body.azos_updated, true);
assert.equal(st.body.stored_chains, 1);
assert.equal(st.body.chains[0].chain, "evidence");
assert.equal(st.body.chains[0].verified, true);
assert.deepEqual(st.body.chains[0].tips, vector.final_tips);
assert.equal(st.body.public_key, TEST_KEY);
assert.equal(st.body.runtime_exec_into_azos, false);
assert.equal(st.body.azos_lattice_refusal_stays, true);

// Replay of the stored tip: no new writes.
const writes = env.DOWNLOADS.writes;
const replay = await post(env, p2);
assert.equal(replay.body.already, true);
assert.equal(env.DOWNLOADS.writes, writes, "a replay writes nothing");
// An unsigned replay of the stored tip is refused.
const unsignedReplay = await post(env, { ...p2, sig: "A".repeat(86) });
assert.equal(unsignedReplay.body.code, "TETHER-SIG");

// --- 2. Out of order: second packet first does not link to genesis ----------------
{
  const e = { DOWNLOADS: fakeKv(), RUNTIME_TETHER_PUBKEY: TEST_KEY };
  const r = await post(e, p2);
  assert.equal(r.status, 409);
  assert.equal(r.body.code, "TETHER-LINK");
  assert.equal(e.DOWNLOADS.writes, 0, "nothing stored on a broken link");
}

// --- 3. Key checks ------------------------------------------------------------------
{
  const e = { DOWNLOADS: fakeKv() };
  const r = await post(e, p1);
  assert.equal(r.status, 503);
  assert.equal(r.body.code, "TETHER-KEY-UNPINNED");
  assert.equal(e.DOWNLOADS.writes, 0);
  const e2 = { DOWNLOADS: fakeKv(), RUNTIME_TETHER_PUBKEY: "B".repeat(43) };
  const r2b = await post(e2, p1);
  assert.equal(r2b.body.code, "TETHER-KEY-MISMATCH");
  assert.equal(e2.DOWNLOADS.writes, 0);
  const forged = structuredClone(p1);
  forged.git_sha = "f".repeat(40);
  const e3 = { DOWNLOADS: fakeKv(), RUNTIME_TETHER_PUBKEY: TEST_KEY };
  const r3 = await post(e3, forged);
  assert.equal(r3.body.code, "TETHER-SIG");
  assert.equal(e3.DOWNLOADS.writes, 0);
}

// --- 4. Recompute: a re-signed packet with a wrong hash is still refused -------------
{
  const bad = structuredClone(p1);
  bad.rows[0].secondary = "e".repeat(64);
  const signed = await signWithTestSeed(bad);
  const e = { DOWNLOADS: fakeKv(), RUNTIME_TETHER_PUBKEY: TEST_KEY };
  const r = await post(e, signed);
  assert.equal(r.body.code, "TETHER-SECONDARY");
  assert.equal(e.DOWNLOADS.writes, 0);
  const badP = structuredClone(p1);
  badP.rows[0].primary = "d".repeat(64);
  const r2c = await post(e, await signWithTestSeed(badP));
  assert.equal(r2c.body.code, "TETHER-PRIMARY");
}

// --- 5. Offline double: the same document for the same user is not stored twice -------
{
  const offlineRow = p1.rows.find((row) => row.offline === true);
  assert.ok(offlineRow, "vector carries an offline row");
  assert.equal(offlineRow.secondary, await offlineSecondaryOf(offlineRow.document_hash, offlineRow.username));
  const tips = vector.final_tips;
  const document_hash = offlineRow.document_hash;
  const primary = await primaryOf(document_hash, tips.primary);
  const row = {
    seq: 9,
    document_hash,
    primary,
    primary_prev: tips.primary,
    secondary: offlineRow.secondary,
    secondary_prev: tips.secondary,
    offline: true,
    username: offlineRow.username,
    lattices: ["primary", "secondary"],
  };
  const packet = await signWithTestSeed({ ...p2, rows: [row], tips: { primary, secondary: row.secondary } });
  const before = env.DOWNLOADS.writes;
  const r = await post(env, packet);
  assert.equal(r.body.code, "TETHER-DOUBLE");
  assert.equal(env.DOWNLOADS.writes, before);
}

// --- 6. Online secondary rule matches the runtime ------------------------------------
{
  const onlineRow = p1.rows.find((row) => row.offline !== true);
  assert.equal(onlineRow.primary_prev, GENESIS);
  assert.equal(onlineRow.secondary, await onlineSecondaryOf(onlineRow.primary, onlineRow.secondary_prev));
  const res = await checkPacket(p1, { pinned: TEST_KEY, stored: null, hasOffline: async () => false });
  assert.equal(res.ok, true);
}

// --- 7. Other doors unchanged ---------------------------------------------------------
{
  const lat = await call(env, "/v1/lattice");
  assert.equal(lat.body.kind, "temporallock_staticclock_lattice", "the TemporalLock lattice route is separate");
  const src = readFileSync(new URL("../src/tether.js", import.meta.url), "utf8");
  assert.equal(/\/v1\/exec|handleExec|AZIEL_RUNTIME\.fetch/.test(src), false, "tether code does not exec or call back into the runtime");
}

console.log("ok azos tether: runtime vector verified and stored; replay writes nothing; broken link, unpinned or wrong key, forged signature, bad recompute, and offline double refused with nothing stored");
