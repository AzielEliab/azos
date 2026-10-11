/** BUILD-STAMP-1.0: /v1/health carries git_sha + version_id from env, null when unset. */
import assert from "node:assert/strict";
import { buildStamp, stampHealth } from "../src/build-stamp.js";
import worker from "../src/index.js";
const sha = "a".repeat(40);
let n = 0;
assert.deepEqual(buildStamp({ GIT_SHA: sha, CF_VERSION_METADATA: { id: "v-1" } }).git_sha, sha); n++;
assert.equal(buildStamp({ GIT_SHA: "main" }).git_sha, null); n++;
assert.equal(buildStamp({}).version_id, null); n++;
assert.match(buildStamp({}).git_sha_source, /unset/); n++;
const j = new Response(JSON.stringify({ ok: true }), { headers: { "content-type": "application/json" } });
const out = await (await stampHealth("/v1/health", new Request("https://h/v1/health"), j, { GIT_SHA: sha })).json();
assert.equal(out.ok, true); assert.equal(out.git_sha, sha); n++;
const other = new Response("x", { headers: { "content-type": "text/plain" } });
assert.equal(await (await stampHealth("/v1/health", new Request("https://h/v1/health"), other, {})).text(), "x"); n++;
// Through the real Worker entry.
const env = { GIT_SHA: sha, CF_VERSION_METADATA: { id: "ver-9" }, DOWNLOADS: { get: async () => null, put: async () => {}, list: async () => ({ keys: [] }) } };
const res = await worker.fetch(new Request("https://h.example/v1/health"), env, { waitUntil() {} });
const body = await res.json();
assert.equal(body.git_sha, sha); assert.equal(body.version_id, "ver-9"); assert.equal(body.ok, true); n++;
console.log(`test_worker_build_stamp: ${n} passed`);
