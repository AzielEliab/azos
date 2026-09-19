# azos download tracker

Isolated Worker `azos-download-tracker`. Project `azos`.
KV namespace `AZOS_DOWNLOADS` bound as `DOWNLOADS`.
Does **not** 302 to GitHub on `/download`. Serves gzip via `ASSETS.fetch`,
`Cache-Control: private, no-store`.

GET `/` is the **AZ-OS — Aziel Eliab** product homepage (SEO, cite.json,
JSON-LD, workspace for public status/invite/prefab/lattice snapshot).
GET `/` increments a **page-view** counter (separate from downloads).
GET `/download` increments **downloads**.
GET `/sigil.png` is the wordless rose-star brand mark (empty alt; no words on the mark). `X-Aziel-Sigil: Everblooming` stays on the image response for verify contracts.
`/v1` never increments DOWNLOADS KV.
GET `/install.sh` one-click install (does not increment; script curls `/download`).
GET `/v1/skill` returns skill markdown (`text/markdown`). Does not increment views or downloads.
GET `/cite.json` citation record. `doi` is `null` — no invented Zenodo DOI.
`/v1/mesh/*` PROXY to aziel-runtime suite mesh (`AZIEL_RUNTIME` / `https://aziel-runtime.vibelock.workers.dev`). Default OFF. QNM-BUILD-1.0 live|locked|isolated. QNS-CD-1.0 photon QNS1 packet transfer is a hub cite / Worker mesh cross-map only (local qnsd in https://github.com/AzielEliab/qnm-node; runtime cites + catalog field in https://github.com/AzielEliab/aziel-runtime; AZInterface pair custody). Not a Softwares-tab product. No Node Gate. No public qnsd proxy. No auto-heal. Not anonymity. Human UI Live Nodes strip polls `GET /v1/mesh`.

Verify: `curl -sS -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/mesh/status` returns MESH-OK style JSON with `enabled: false` by default.

Hosted `/v1` status / invite / health / skill / prefab / lattice GET are
public and session-safe. Session, exec, and lattice bind persist in
product-Worker KV and need full AZ-OS (`azos ui`). The HTTP proxy is not
the full OS.

Host: https://azos-download-tracker.vibelock.workers.dev

## Human / bot schema (`/stats` and `/count`)

Additive dual-count (Whitestone canary). Classification lives in `src/classify.js`
and response shaping in `src/stats-shape.js`.

Invariant: `views === views_human + views_bot` and
`downloads === downloads_human + downloads_bot`.

Legacy strategy (b): existing KV totals are never reset. Pre-split remainder
is shown as bot on read (`views_bot = views - views_human`). Author: Aziel Eliab only.

