/**
 * AZNews ↔ 4DMap honesty for the hosted probe.
 * The Worker has no standing feed. GET passes no store, so the join stays refused.
 * A fetched item can mark the join live only when that item is also pinned.
 * 4DMap is not installed. Author: Aziel Eliab.
 */

export const ABSENT_CODE = "AZNEWS-SOURCE-ABSENT";
export const LANDED_CODE = "AZNEWS-ITEM-LANDED";

const ABSENT_PLAIN =
  "News and the map have a joined path and two standalone paths. " +
  "On the joined path, a news item can become a map pin (date, event, and place), " +
  "or a pin can open the matching news. AZNews can stand alone, and 4DMap can stand alone. " +
  "That join is the runtime 4DMap engine on the FragGate door. " +
  "This page does not claim the aziel-runtime side is done. " +
  "AZ-OS does not install 4DMap and does not keep a second map. " +
  "azos.news_source is the fetch door and it has no standing feed, so the news source is absent. " +
  "The probe refuses until a fetched item lands. Nothing here is live or merged.";

const LIVE_PLAIN =
  "A fetched news item has landed as a map pin, so the join is marked live. " +
  "AZNews can still stand alone, and 4DMap can still stand alone. " +
  "4DMap is not installed. The join is not merged. " +
  "This page does not claim the aziel-runtime side is done.";

function fetchedRow(rows) {
  for (const row of rows) {
    const document = row && row.document;
    if (!document || document.kind !== "aznews_item") continue;
    if (document.fixture === true || document.fetched !== true || document.live === true) continue;
    if (!document.wording) continue;
    return row;
  }
  return null;
}

export function fetchedItemLanded(stored) {
  const rows = stored && Array.isArray(stored.rows) ? stored.rows : [];
  const pins = stored && Array.isArray(stored.pins) ? stored.pins : [];
  const row = fetchedRow(rows);
  if (!row) return false;
  const digest = row.content_hash;
  if (!digest) return false;
  return pins.some((pin) => pin && pin.news_content_hash === digest);
}

export function assertJoinHonest(record) {
  const body = record && typeof record === "object" ? record : {};
  const joined = body.paths && body.paths.joined ? body.paths.joined : {};
  const refused = body.refused === true || body.source_present !== true || body.code === ABSENT_CODE;
  if (refused && (body.live === true || joined.live === true)) {
    throw new Error("join flag is true while the news source is absent");
  }
  if (body.live === true && body.item_landed !== true) {
    throw new Error("join flag is true without a fetched item");
  }
  if (body.installed === true || body.engine_installed === true) {
    throw new Error("4DMap is marked installed");
  }
  return body;
}

export function joinStatus(stored) {
  const landed = fetchedItemLanded(stored) === true;
  const record = {
    ok: landed,
    refused: !landed,
    code: landed ? LANDED_CODE : ABSENT_CODE,
    absent: landed ? null : "azos.news_source",
    source: "aznews",
    source_present: landed,
    join: "aznews-4dmap",
    engine_slug: "4dmap",
    engine_name: "4DMap",
    engine_copy: false,
    second_app: false,
    installed: false,
    engine_installed: false,
    merged: false,
    live: landed,
    lattice_live: false,
    item_landed: landed,
    runtime_done: false,
    runtime_claimed: false,
    cross_tether: true,
    internet_live: false,
    mail_live: false,
    kernel_live: false,
    one_click_install_live: false,
    mesh_node_live: false,
    paths: {
      joined: { present: true, id: "aznews-4dmap", live: landed },
      aznews_standalone: { present: true, live: false, installed: false },
      fourdmap_standalone: { present: true, installed: false, engine_installed: false, live: false },
    },
    door: "https://aziel-runtime.vibelock.workers.dev/v1/fraggate/call",
    pin_op: "news_pin",
    open_op: "news_open",
    author: "Aziel Eliab",
    plain: landed ? LIVE_PLAIN : ABSENT_PLAIN,
  };
  return assertJoinHonest(record);
}

export function aznewsStatus() {
  return {
    ok: false,
    refused: true,
    path: "standalone",
    standalone: true,
    live: false,
    installed: false,
    source_present: false,
    code: ABSENT_CODE,
    absent: "azos.news_source",
    author: "Aziel Eliab",
    plain: "AZNews can stand alone. This Worker has no standing news feed, so AZNews is not live. 4DMap is not installed.",
  };
}

export function mapStatus() {
  return {
    ok: true,
    refused: false,
    path: "standalone",
    standalone: true,
    installed: false,
    engine_installed: false,
    live: false,
    author: "Aziel Eliab",
    plain: "4DMap can stand alone in full AZ-OS. This Worker does not install 4DMap and does not keep pins.",
  };
}
