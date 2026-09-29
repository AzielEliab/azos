# SIDENET-P4 — AZ-OS offline node

Author: **Aziel Eliab**.

## Layer

AZ-OS can sit in three places:

| Layer | Fit for this client |
|---|---|
| Base OS | No. This repository is an overlay. It is not a kernel or a bootloader. |
| Stacked OS | Yes. `azos node` stacks a local node on the ethics-coded shell. |
| Standalone Softwares-style | No. This client does not add a Softwares card and does not invent catalog entries. |

## What it holds

Files live in `.azos/node/` inside the current directory:

- `receipts.jsonl` — append-only local receipts (presence, tip, prev). No mesh body.
- `state.json` — node id, posture, and the last good tip.
- `l0.json` — the last L0 probe. Missing means **unprobed**, which is not LIVE.

`azos purge --confirm` deletes `.azos/`, including this node.

## L0

L0 is aziel-runtime FragGate over HTTPS. Published fronts, same door:

1. `https://aziel-runtime.vibelock.workers.dev`
2. `https://www.azielcorpuslibrary.net/runtime`
3. `https://www.azieleliab.com/runtime`
4. `https://godlock.uk/runtime`

`azos node rejoin` sends `User-Agent: Mozilla/5.0`, probes `GET /v1/health`, then `POST /v1/mesh/join` and `POST /v1/mesh/heartbeat`. The heartbeat carries `node_id`, `presence`, `tip_hash`, and `prev` only. Join uses `product: azos` and `kind: instance` (a downloaded shell, not a human Live Node and not a `{slug}-worker` row). A successful rejoin does not append a second receipt, so the tip on disk stays the tip that was sent.

If no front answers, the local tip stays and the menu says **UNREACHABLE**. A `MESH-OFF` answer means L0 HTTPS answered and the join did not happen. The Softwares desk stays **frozen** either way. This client does not call `GET /v1/software`.

## Phoenix and REHEAL

Phoenix is local wait. The tip does not change, and the client does not hunt a controller or restore a public hostname.

`azos node reseal` appends one receipt that cites this node's own tip. A neighbor tip is not adopted. The same prev with a different tip isolates this node (`SIDENET-EQUIVOCATION`) and does not splice the chain.

`reheal` returns the local tip, or keeps phoenix-wait. `vote` and `neighbor_tip` refuse `SIDENET-NO-VOTE`.

## Multi-survival menu

`azos node menu` is a cite plus this process's probe. It does not paint SLOT as LIVE.

| Item | Status here |
|---|---|
| Local receipts, local presence tip, phoenix, reheal, spore | LIVE (this process) |
| Plane A named fronts | LIVE as the published map (one blast radius, `cf-github`) |
| Cap-7 factory cite | LIVE as a published cite. Not an internet door. Not reached by this client. `icann_tld_az: false`. `radio_phy: false` |
| L0 FragGate/HTTPS | UNPROBED, LIVE, or UNREACHABLE from the last probe |
| Softwares desk | FROZEN. Cards: none |
| Plane B, Plane C, live-node API, DOI | SLOT |
| Radio PHY | ABSENT |
| qnm-node | CITE. Not paired. Not required |

No rewrite key. The node does not lie to survive. No Zenodo DOI is claimed.

## qnm-node

The full local node process (OS radio probes, `qnsd`, phoenix engines) is [qnm-node](https://github.com/AzielEliab/qnm-node). This package does not depend on it and does not fake a Wi-Fi, Bluetooth, RF, or photon PHY.

## Commands

```bash
azos node
azos node menu
azos node seal
azos node phoenix
azos node reseal
azos node reheal
azos node rejoin
```

Writes run the five ethics gates unless an ARC token is passed. Halt refuses writes. Reads (`status`, `menu`) stay available.
