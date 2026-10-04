import assert from "node:assert/strict";
import { assertJoinHonest, joinStatus, mapStatus, aznewsStatus } from "../src/newsmap.js";

const absent = joinStatus(null);
assert.equal(absent.code, "AZNEWS-SOURCE-ABSENT");
assert.equal(absent.refused, true);
assert.equal(absent.live, false);
assert.equal(absent.merged, false);
assert.equal(absent.installed, false);
assert.equal(absent.engine_installed, false);
assert.equal(absent.source_present, false);
assert.equal(absent.paths.joined.present, true);
assert.equal(absent.paths.joined.live, false);
assert.equal(absent.paths.aznews_standalone.present, true);
assert.equal(absent.paths.fourdmap_standalone.installed, false);
assert.equal(absent.internet_live, false);
assert.equal(absent.mail_live, false);
assert.equal(absent.kernel_live, false);
assert.equal(absent.mesh_node_live, false);
assertJoinHonest(absent);

assert.throws(
  () => assertJoinHonest({ ...absent, live: true }),
  /news source is absent/,
);

const digest = "ab".repeat(32);
const landed = joinStatus({
  rows: [
    {
      content_hash: digest,
      document: {
        kind: "aznews_item",
        fetched: true,
        fixture: false,
        live: false,
        wording: "A fetched sentence about the basin.",
      },
    },
  ],
  pins: [{ news_content_hash: digest }],
});
assert.equal(landed.live, true);
assert.equal(landed.refused, false);
assert.equal(landed.item_landed, true);
assert.equal(landed.source_present, true);
assert.equal(landed.installed, false);
assert.equal(landed.merged, false);
assert.equal(landed.paths.joined.live, true);
assert.equal(landed.paths.fourdmap_standalone.installed, false);
assertJoinHonest(landed);

const unpinned = joinStatus({
  rows: [
    {
      content_hash: digest,
      document: {
        kind: "aznews_item",
        fetched: true,
        fixture: false,
        live: false,
        wording: "A fetched sentence about the basin.",
      },
    },
  ],
  pins: [],
});
assert.equal(unpinned.live, false);
assert.equal(unpinned.code, "AZNEWS-SOURCE-ABSENT");

const fixture = joinStatus({
  rows: [
    {
      content_hash: digest,
      document: {
        kind: "aznews_item",
        fetched: true,
        fixture: true,
        live: false,
        wording: "Fixture wording.",
      },
    },
  ],
  pins: [{ news_content_hash: digest }],
});
assert.equal(fixture.live, false);

const aloneNews = aznewsStatus();
const aloneMap = mapStatus();
assert.equal(aloneNews.live, false);
assert.equal(aloneNews.path, "standalone");
assert.equal(aloneMap.installed, false);
assert.equal(aloneMap.live, false);
assert.equal(aloneMap.path, "standalone");

console.log("join flags ok");
