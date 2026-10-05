import assert from "node:assert/strict";
import { prefabCatalog, scopeMeta } from "../src/runtime.js";

const locked = [
  "kernel",
  "kernel_base",
  "booted",
  "installed",
  "os_yet",
  "alt_internet_live",
  "packet_path_live",
  "second_device",
  "mail_send",
  "mesh_node_live",
  "one_click_install_live",
  "doors_replaced",
  "app_shells_started",
];

const override = {
  installed: 25,
  booted: true,
  kernel: true,
  kernel_base: true,
  os_yet: true,
  alt_internet_live: true,
  packet_path_live: true,
  second_device: true,
  mail_send: true,
  mesh_node_live: true,
  one_click_install_live: true,
  doors_replaced: true,
  app_shells_started: true,
  userspace_base: false,
  internet_base: { live: true, installed: true, base: false },
};

const beaten = scopeMeta(override);
for (const key of locked) {
  assert.equal(beaten[key], false, key);
  assert.equal(typeof beaten[key], "boolean", key);
}
assert.equal(beaten.userspace_base, true);
assert.equal(beaten.internet_base.live, false);
assert.equal(beaten.internet_base.installed, false);
assert.equal(beaten.internet_base.base, true);
assert.match(beaten.limits_plain, /This is not installed as an operating system\./);
assert.match(beaten.limits_plain, /This has not booted\./);
assert.match(beaten.limits_plain, /There is no kernel\./);
assert.match(beaten.limits_plain, /The kernel base is absent\./);
assert.match(beaten.limits_plain, /This is not a live mesh node\./);
assert.match(beaten.limits_plain, /The userspace base is present\. That is a base, not a boot\./);
assert.doesNotMatch(beaten.limits_plain, /This is installed as an operating system\./);

const counted = scopeMeta({ installed: true, booted: true, kernel: true });
assert.equal(counted.installed, false);
assert.equal(counted.booted, false);
assert.equal(counted.kernel, false);

const prefab = scopeMeta(prefabCatalog());
assert.equal(prefab.installed, false);
assert.equal(typeof prefab.installed, "boolean");
assert.equal(prefab.hook_count >= 25, true);
assert.equal(prefab.mesh_node_live, false);
assert.ok(prefab.apps.length >= 25);
assert.ok(prefab.apps.every((app) => app.installed === false && app.hooked === true && app.hook_record === true));
const raw = JSON.stringify(prefab);
assert.equal(raw.includes('"installed":true'), false);
assert.equal(raw.includes('"installed":25'), false);
assert.match(prefab.limits_plain, /This is not installed as an operating system\./);
assert.match(prefab.note, /not installed as an operating system/);

const health = scopeMeta({ ok: true, product: "azos", version: "0.3.0" });
assert.equal(health.installed, false);
assert.equal(health.booted, false);
assert.equal(health.kernel, false);
assert.equal(health.mesh_node_live, false);
assert.match(health.limits_plain, /This is not installed as an operating system\./);

console.log("prefab flags ok");
