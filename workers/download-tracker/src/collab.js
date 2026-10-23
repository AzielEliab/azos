/**
 * AZBOT-NODE-COLLAB-1.0 on the AZ-OS tether (AZRT-AZOS-TETHER-1.0).
 *
 * GET /v1/collab/tip shares the stored session-chain receipt tip only.
 * Parties cannot rewrite that tip from this route. The local package
 * (azos/collab.py) is where an ethics-gated session packages an AZBot
 * FragGate handoff and appends the receipt onto TemporalLock / ChainLock.
 *
 * Remain-OFF: public AZ-OS exec / shell / lattice stay refused, vault
 * wipe / scorch / unlock stay local-only, and GET /v1/mesh does not enable
 * radios. This module does not invent a public enable and does not rewrite
 * runtime mesh mode flags. Cap-7 stays a name, not ICANN.
 *
 * Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
 */
import { tetherState } from "./tether.js";

export const COLLAB_SPEC = "AZBOT-NODE-COLLAB-1.0";
export const TETHER_SPEC = "AZRT-AZOS-TETHER-1.0";
export const GET_MESH_ENABLES = false;
export const REWRITES_QNM_FLAGS = false;
export const PUBLIC_MESH_ENABLE_INVENTED = false;
export const CAP7_SENTENCE = "Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP.";

export function collabFacts() {
  return {
    spec: COLLAB_SPEC,
    tether: TETHER_SPEC,
    author: "Aziel Eliab",
    share: "receipt-tips-only",
    rewrite: false,
    written: false,
    fetched: false,
    second_door: false,
    single_door: true,
    door: "https://aziel-runtime.vibelock.workers.dev/v1/fraggate/call",
    bind: "127.0.0.1",
    public_port: false,
    public_exec: "refused",
    public_shell: "refused",
    public_lattice: "refused",
    remain_off_item: 8,
    vault_wipe: "local-only",
    vault_scorch: "local-only",
    vault_unlock: "local-only",
    vault_public: "FG-STUB",
    deanonymize: "refused",
    invent_mark: "refused",
    backdate: "refused",
    public_rollback: "refused",
    get_mesh_enables: GET_MESH_ENABLES,
    public_mesh_enable_invented: PUBLIC_MESH_ENABLE_INVENTED,
    mesh_need_bearer: "MESH-NEED-BEARER",
    local_qnm_node: "https://github.com/AzielEliab/qnm-node",
    mesh_node_live: true,
    alt_internet_live: true,
    packet_path_live: true,
    public_bind: false,
    rewrites_qnm_flags: REWRITES_QNM_FLAGS,
    qnm_flags_not_rewritten: ["enabled", "mesh_default", "auto_heal", "node_gate", "anonymity_network", "vpn"],
    qnm_note: "Softwares tip publishes mesh_node_live, alt_internet_live, and packet_path_live true. This tether does not flip those flags or other OPERATOR-OVERRIDE lives. GET /v1/mesh does not enable radios. public_bind stays false. This tether does not invent a public enable.",
    cap7: "Cap-7",
    aziel: ".aziel",
    cap7_is_path: false,
    aziel_is_path: false,
    cap7_public_egress: false,
    public_icann: false,
    bgp: false,
    cap7_note: CAP7_SENTENCE,
    public_door: "FG-STUB",
    second_device: false,
    live: false,
  };
}

function refusal(code) {
  return { ok: false, code, ...collabFacts() };
}

/** Session-chain tip only. Row documents are not copied onto this view. */
export function sessionTipView(state) {
  const chains = state && Array.isArray(state.chains) ? state.chains : [];
  const row = chains.find((c) => c && c.chain === "session") || null;
  const tips = row && row.tips && typeof row.tips === "object" ? row.tips : null;
  const tip = tips && typeof tips.primary === "string"
    ? {
      chain: "session",
      primary: tips.primary,
      secondary: typeof tips.secondary === "string" ? tips.secondary : null,
      seq: row.rows,
      verified: row.verified === true,
    }
    : null;
  return {
    ok: true,
    route: "/v1/collab/tip",
    tip,
    parties_can_rewrite: false,
    ...collabFacts(),
  };
}

export async function handleCollabRoute(request, url, env) {
  const path = String(url && url.pathname || "").replace(/\/+$/, "") || "/";
  if (path !== "/v1/collab" && !path.startsWith("/v1/collab/")) return null;
  const method = String(request && request.method || "GET").toUpperCase();
  if (method !== "GET" && method !== "HEAD") {
    return { status: 403, body: refusal("COLLAB-REWRITE-REFUSED") };
  }
  if (path !== "/v1/collab" && path !== "/v1/collab/tip") {
    return { status: 404, body: refusal("COLLAB-UNKNOWN") };
  }
  const state = await tetherState(env).catch(() => null);
  return { status: 200, body: sessionTipView(state) };
}
