# Refusal receipts on the azos tracker (AZRT-REFUSAL-RECEIPT-1.0 addendum, peer side)

Author: Aziel Eliab. Status: additive. Not a new RIB: this is the peer side of the RIB-018 addendum in
aziel-runtime `docs/designs/AZRT-REFUSAL-RECEIPT-1.0.md` ("Addendum (2026-10-19)"), which cites the law docs
(REFUSAL-CONTRACT, RECEIPT-SCHEMA, COMPATIBILITY / BREAKING-CHANGE policy, AZRT-DUAL-LATTICE-1.0,
AZRT-AZOS-TETHER-1.0 / TETHER-REFUSALS-1.0).

- Code: `workers/download-tracker/src/refusal-peer.js`, wired in `src/index.js`. Test: `scripts/verify-refusal-peer.mjs`.
- A refusal from this tracker (status >= 400 with a stable `code`/`refuse`) is reported over the
  `AZIEL_RUNTIME` service binding to `POST https://peer.aziel.internal/v1/refusals/peer`. The runtime seals it
  with its existing `sealRefusal` onto its internal `refusals` ChainLock chain (both lattice hashes,
  append-only), surface `azos`. One chain for all three sides = one refusal lattice.
- The refusal is unchanged: same status and fields, plus `refusal_receipt` and header `X-Azrt-Refusal-Receipt`.
- Fail closed: no binding, an error, or a write slower than 2.5 s gives `sealed:false` with
  `status: unavailable | receipt_pending`; never an invented hash. Not signed.
- Not recorded: auth refusals (401, token codes, TETHER-SIG / TETHER-KEY-*), 429s, uncoded 4xx (e.g. plain
  404 "not found"), and refusals of a tether packet for the `refusals` chain itself (no feedback loop).
- Flood guard is on the runtime: per-minute dedupe on code + surface + method + status, an in-isolate memo,
  and a 60 seals/min/isolate cap.
- `GET /v1/refusals`: this surface's recent refusal receipts read from the shared chain, the runtime tip, and
  the tip this tracker stored from the signed tether (`tip_state`: agree / lagging; the tether runs every 2 minutes).
