// AZRT-STORE-CHECKPOINT-1.0 copy side + COPY-WALK-1.0, with tamper refusals. Author: Aziel Eliab.
import assert from "node:assert/strict";
import fs from "node:fs";
import { memCopyRepo, copyIngest, copyState, copyWalkStep } from "../src/news-copy.js";
const fx = JSON.parse(fs.readFileSync(new URL("./fixtures/checkpoint-packets.json", import.meta.url)));
const pinned = fx.public_key;
const clone = (x) => JSON.parse(JSON.stringify(x));
const env = {};
// Happy path from genesis.
const repo = memCopyRepo();
for (const p of fx.packets) { const r = await copyIngest(repo, p, { pinned }); assert.equal(r.status, 200, JSON.stringify(r.body)); }
const st = await copyState(repo, env);
assert.equal(st.cp_n, 2); assert.equal(st.copy_walk.verified_through, st.tip_seq); assert.equal(st.copy_walk.breaks.length, 0);
assert.equal(st.verified_via_checkpoints, true);
// Tamper 1: checkpoint tips changed (packet re-signing impossible without the key -> packet sig fails first).
const idx = fx.packets.findIndex((p) => p.checkpoints && p.checkpoints.length);
const run = async (mutate) => { const r = memCopyRepo(); for (let i = 0; i < idx; i++) await copyIngest(r, fx.packets[i], { pinned }); const p = clone(fx.packets[idx]); mutate(p); return copyIngest(r, p, { pinned }); };
let r = await run((p) => { p.checkpoints[0].tips.primary = "0".repeat(64); });
assert.ok(r.status >= 400); assert.equal(r.body.stored, false);
// Tamper 2: checkpoint dropped from a signed packet -> packet signature fails.
r = await run((p) => { delete p.checkpoints; });
assert.ok(r.status >= 400);
// Tamper 3: a copy row altered at rest is caught when the copy re-walks from genesis.
const r2 = memCopyRepo();
for (const p of fx.packets) await copyIngest(r2, p, { pinned });
const row = await r2.get(5); row.lattice.document_hash = "f".repeat(64);
await r2.kvPut({ cwalk: null });
await copyWalkStep(r2, await r2.meta());
const st2 = await copyState(r2, env);
assert.ok(st2.copy_walk.breaks.length > 0); assert.equal(st2.copy_walk.breaks[0].seq, 5); assert.equal(st2.verified_via_checkpoints, false);
// Tamper 4: a row whose lattice matches but disagrees with a signed checkpoint is caught at the checkpoint.
const r3 = memCopyRepo();
for (const p of fx.packets) await copyIngest(r3, p, { pinned });
const cp1 = await r3.kvGet("cp:1"); cp1.tips.primary = "e".repeat(64); await r3.kvPut({ "cp:1": cp1, cwalk: null });
await copyWalkStep(r3, await r3.meta());
assert.match((await copyState(r3, env)).copy_walk.breaks[0].reason, /checkpoint 1 tips differ/);
console.log("verify-checkpoint-copy: ok", { tip: st.tip_seq, cp_n: st.cp_n });
