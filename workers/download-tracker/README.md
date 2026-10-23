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
`/v1/mesh/*` PROXY to aziel-runtime suite mesh (`AZIEL_RUNTIME` / `https://aziel-runtime.vibelock.workers.dev`). The proxy forwards the runtime document and does not rewrite its mode flags. AZ-OS health keeps mesh_node_live true. The local fallback node mesh is on (`enabled: true`, mesh radios on). QNM-BUILD-1.0 live|locked|isolated. QNS-CD-1.0 photon QNS1 packet transfer is a hub cite / Worker mesh cross-map only (local qnsd in https://github.com/AzielEliab/qnm-node; runtime cites + catalog field in https://github.com/AzielEliab/aziel-runtime; AZInterface pair custody). Not a Softwares-tab product. No Node Gate. No public qnsd proxy. No auto-heal. Not anonymity. Those fallback words are not applied to a proxied body. Human UI Live Nodes strip polls `GET /v1/mesh`.

Verify: `curl -sS -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/mesh/status` returns the runtime document. AZ-OS health keeps `mesh_node_live` true. A local fallback uses code MESH-OK and `enabled: true`.

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


## Runtime cross-tether (AZRT-AZOS-TETHER-1.0)

`POST /v1/tether/tip` receives signed dual-lattice tips from aziel-runtime. The tracker checks the Ed25519 signature against the pinned runtime public key (`RUNTIME_TETHER_PUBKEY` in `wrangler.toml`), recomputes every row's primary and secondary hash, checks the link to the tip it already stored (genesis on first contact), and refuses an offline double. Only then does it write the new tip to KV. Any failure refuses and nothing is stored.

`GET /v1/tether` lists the stored tips. `azos_updated` is true only for tips this tracker verified against the pinned key.

The runtime does not exec into AZ-OS. The runtime FragGate `azos` `exec`, `shell`, and `lattice` refusal stays (REMAIN-OFF item 8). This is not the TemporalLock `/v1/lattice` route. Not mesh membership, not a second device, not a public ledger.

Test: `node scripts/verify-tether.mjs` (uses `scripts/fixtures/azos-tether-vector.json`, copied from aziel-runtime `fixtures/azos-tether-vector.json`, signed with a public test-only seed).

## AZ-LOCKSTEP-1.0 (shared design + contract with aziel-runtime)

This leg is independent and optional. `vendor/lockstep/` is a byte-for-byte copy of aziel-runtime's
design tokens, contract, and consumer check, pinned by SHA-256 in `LOCKSTEP.pin.json`.

- `GET /v1/lockstep`: `agree` / `drift` / `absent` against the runtime over the `AZIEL_RUNTIME` binding. When the runtime is absent this leg keeps running standalone and shows every flag as false.
- `GET /design/tokens.css`, `/design/tokens.json`: the shared design source, the same bytes as the runtime's.
- `npm test` fails if a vendored file changed, a lock moved, a flag is true, the tether key, chains, or mesh differ from the contract, or a feature this leg claims in the contract's union stops answering. `npm run lockstep:remote` also compares the pin with runtime `main`.
- To re-vendor after a runtime contract change, run `node scripts/lockstep-vendor.mjs <this checkout>` from an aziel-runtime checkout.
- There is no GitHub workflow here. Adding one that runs `npm test` needs a token with `workflow` scope.
