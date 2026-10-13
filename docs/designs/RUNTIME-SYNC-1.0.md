# RUNTIME-SYNC-1.0 and MESH-HINTS-UI-1.0 (AZOS side)

Author: Aziel Eliab. Additive and read-only.

Laws cited: AZRT-AZOS-TETHER-1.0 (the runtime sends, and AZOS verifies and stores; the runtime never runs code here),
REMAIN-OFF-BY-DESIGN-2026-09-10 item 8 (`azos lattice` exec stays refused), and the aziel-runtime FragGate single-door rule.

- `GET /v1/runtime/sync` mirrors the runtime's `lattice_tip`, tether `bases`, mesh bootstrap and install paths, and the
  lattice-learn op name. It compares each tip this tracker verified with the runtime tip: agree, lagging or unknown.
  It writes nothing and signs nothing, and every live flag stays false. If the runtime is unreachable, it returns
  `RUNTIME-SYNC-UNREACHABLE` (fails closed).
- The homepage shows the five first-run hints as a dismissible popup, remembered only in localStorage `azrt.hints.v1`.
