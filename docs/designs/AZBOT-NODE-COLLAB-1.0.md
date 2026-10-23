# AZBot node collaborative forensic (AZOS tether, Design 1.0)

Author: Aziel Eliab. Status: additive. AZOS only. AZBot owns the azbot repository.
The Softwares OVERRIDE is a separate change and is not in this tree.

Source: AZBot Design for Node-Based Collaborative Forensic System, Design 1.0
(October 2026). This note is the AZ-OS side of that design. It does not add a
second door and it does not open a public port.

Laws cited: AZRT-AZOS-TETHER-1.0 (the runtime sends signed tips; AZ-OS verifies
and stores; the runtime does not exec into AZ-OS), REMAIN-OFF item 8 (FragGate
`azos` `exec` / `shell` / `lattice` stay refused), and the FragGate single-door
rule. Local handoff receipts use the ChainLock formula AZ-OS already exposes
(`runtime_primary`, `runtime_offline_secondary`) plus TemporalLock × StaticClock
(`IntegrityLattice`). No new hash rule.

## What landed

- `azos/collab.py` — ethics-gated session cooperation with a local AZBot handoff.
  Five gates, a live ARC token, and the closed action `azbot_handoff` (not a new
  shell verb). On pass, the module returns a FragGate envelope (`slug`, `op`,
  payload hash, door `POST /v1/fraggate/call`). `fetched` stays false.
- A returned receipt is appended on the session lattice. `tip(party)` returns
  the TemporalLock gear hash and the ChainLock tip only. `rewrite` raises.
  Party names are append-only.
- `GET /v1/collab/tip` (`workers/download-tracker/src/collab.js`) reads the
  tether-stored `session` chain tip (primary, secondary, seq, verified). It
  does not return row documents. Any other method is `COLLAB-REWRITE-REFUSED`
  and writes nothing.

## Remain-OFF

| Item | This tether |
|---|---|
| AZ-OS public exec / shell / lattice | Refused. `slug=azos` with those ops returns `PUBLIC-AZOS-REFUSED` and packages nothing. |
| Vault wipe / scorch / unlock | Local-only. Public handoff returns `VAULT-LOCAL-ONLY`. Public status stays `FG-STUB`. |
| Deanonymize, invent_mark, backdate, public rollback | Refused (`COLLAB-REMAIN-OFF`). |
| GET /v1/mesh enables radios | No. `get_mesh_enables` is false. A handoff of `slug=mesh` `op=enable` is `COLLAB-MESH-ENABLE-REFUSED`. Operator presence still uses the existing MESH-NEED-BEARER proxy and local qnm-node. This change does not add a public enable. |
| FragGate | Still the only door. |

## QNM OVERRIDE and Cap-7

Proxied `GET /v1/mesh` forwards the runtime document and does not rewrite its
mode flags. The Softwares tip publishes `mesh_node_live`, `alt_internet_live`,
and `packet_path_live` true. This tether does not flip those flags or other
OPERATOR-OVERRIDE lives (`enabled`, `mesh_default`, `auto_heal`, `node_gate`,
`anonymity_network`, `vpn`, when the runtime sends them). `public_bind` stays
false. `GET /v1/mesh` does not enable radios and does not install a mesh node.

Cap-7 and `.aziel` stay names. `cap7_is_path`, `aziel_is_path`,
`cap7_public_egress`, `public_icann`, and `bgp` stay false. Cap-7 is not a
public registrar and not ICANN or BGP.

## Tests

- `tests/test_collab.py`
- `node workers/download-tracker/scripts/verify-collab.mjs`
