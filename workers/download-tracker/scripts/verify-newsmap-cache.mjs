import assert from "node:assert/strict";
import { doorJoinCheckCached, clearJoinCache, JOIN_CACHE_LIVE_MS, JOIN_CACHE_FAIL_MS } from "../src/newsmap-door.js";

const okCall = () => {
  let n = 0;
  const call = async (op) => {
    n++;
    if (op === "news_pin") return { status: 200, body: { ok: true, result: { ok: true, item: { item_id: "n-1" }, pins: [{ pin_id: "p1" }], pull_receipt_seq: 7 } } };
    return { status: 200, body: { ok: true, result: { ok: true, linked: true, item: { item_id: "n-1" } } } };
  };
  return { call, count: () => n };
};
const failCall = () => {
  let n = 0;
  return { call: async () => { n++; throw new Error("down"); }, count: () => n };
};

// pass is reused for 30 s, then re-checked
clearJoinCache();
{
  const env = { AZIEL_RUNTIME: { fetch() {} } };
  const c = okCall();
  const a = await doorJoinCheckCached(env, c.call, 1_000_000);
  assert.equal(a.check.ok, true); assert.equal(a.cached, false); assert.equal(c.count(), 2);
  const b = await doorJoinCheckCached(env, c.call, 1_000_000 + 12_000);
  assert.equal(b.cached, true); assert.equal(b.age_s, 12); assert.equal(c.count(), 2);
  const d = await doorJoinCheckCached(env, c.call, 1_000_000 + JOIN_CACHE_LIVE_MS);
  assert.equal(d.cached, false); assert.equal(c.count(), 4);
}
// fail is cached only 10 s and never as a pass
clearJoinCache();
{
  const env = { AZIEL_RUNTIME: { fetch() {} } };
  const f = failCall();
  const a = await doorJoinCheckCached(env, f.call, 0);
  assert.equal(a.check.ok, false);
  const b = await doorJoinCheckCached(env, f.call, JOIN_CACHE_FAIL_MS - 1);
  assert.equal(b.cached, true); assert.equal(b.check.ok, false);
  const c = okCall();
  const d = await doorJoinCheckCached(env, c.call, JOIN_CACHE_FAIL_MS);
  assert.equal(d.cached, false); assert.equal(d.check.ok, true);
}
// different runtime bindings never share an entry
clearJoinCache();
{
  const c = okCall();
  await doorJoinCheckCached({ AZIEL_RUNTIME: { fetch() {} } }, c.call, 0);
  const f = failCall();
  const x = await doorJoinCheckCached({ AZIEL_RUNTIME: { fetch() {} } }, f.call, 1);
  assert.equal(x.cached, false); assert.equal(x.check.ok, false);
}
console.log("NEWSMAP-CACHE-OK azos");
