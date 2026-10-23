/** KERNEL-FIELD-1.0 (AZ-OS mesh): every `kernel` key is exactly false; the mesh spec name is kernel_profile. */
import assert from "node:assert/strict";
import * as M from "../src/mesh.js";
let n = 0;
function bad(o, p = "", out = []) {
  if (!o || typeof o !== "object") return out;
  if (Object.prototype.hasOwnProperty.call(o, "kernel") && o.kernel !== false) out.push(p + ".kernel=" + JSON.stringify(o.kernel));
  for (const [k, v] of Object.entries(o)) bad(v, p + "." + k, out);
  return out;
}
const views = { emptyMesh: M.emptyMesh(), publicMesh: M.publicMesh(M.emptyMesh()), alignLiveNodes: M.alignLiveNodes({ mesh: M.emptyMesh() }), meshPointer: M.meshPointer() };
for (const [name, v] of Object.entries(views)) { assert.deepEqual(bad(v), [], name); n++; }
assert.equal(views.emptyMesh.kernel_profile, M.MESH_KERNEL); n++;
assert.equal(views.emptyMesh.kernel, false); n++;
assert.equal(M.MESH_DEFAULT_OFF, false); n++;
assert.equal(M.MESH_ENABLED, true); n++;
assert.equal(M.MESH_RADIOS, "on"); n++;
assert.equal(views.emptyMesh.enabled, true); n++;
assert.equal(views.emptyMesh.mesh_node_live, true); n++;
assert.equal(views.emptyMesh.alt_internet_live, true); n++;
assert.equal(views.emptyMesh.packet_path_live, true); n++;
assert.equal(views.emptyMesh.public_bind, false); n++;
assert.equal(views.emptyMesh.cap7_public_icann, false); n++;
assert.equal(views.publicMesh.mesh_node_live, true); n++;
assert.equal(views.meshPointer.enabled_default, true); n++;
console.log(`mesh kernel field: ${n} passed`);
