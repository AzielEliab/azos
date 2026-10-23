"""Runtime dual-lattice parity (AZRT-DUAL-LATTICE-1.0), additive.

These recompute the aziel-runtime lattice rules byte for byte so AZ-OS can
check a runtime receipt offline. ``azos.chains`` keeps its own news-chain
formula unchanged; this module does not replace it.

    primary           = H(canon({document, prev}))
    offline secondary = H(canon({primary: document_hash, username}))
    online secondary  = H(canon({offline: false, prev, primary}))
    tiebreak          = H(canon({chain: "tiebreak", prev, primary, secondary, username}))

Tie-break is the third chain (LATTICE-TIEBREAK-1.0): primary is the synced
online row's primary, secondary is the offline row's secondary, and prev is
the previous tie-break hash (genesis when none). A row with no tiebreak block
is left out of that chain, so its receipt bytes stay as they were.

Sealed, not signed. Not marked live.

Author: Aziel Eliab.
"""

from __future__ import annotations

from azos.chains import GENESIS, canon, sha_bytes

SPEC = "AZRT-DUAL-LATTICE-1.0"


def runtime_primary(document_hash: str, prev: str | None = None) -> str:
    return sha_bytes(canon({"document": document_hash, "prev": prev or GENESIS}))


def runtime_offline_secondary(document_hash: str, username: str) -> str:
    return sha_bytes(canon({"primary": document_hash, "username": str(username)}))


def runtime_online_secondary(primary: str, prev: str | None = None) -> str:
    return sha_bytes(canon({"offline": False, "prev": prev or GENESIS, "primary": primary}))


TIEBREAK_SPEC = "LATTICE-TIEBREAK-1.0"
_HEX64 = set("0123456789abcdef")


def runtime_tiebreak(primary: str, secondary: str, username: str, prev: str | None = None) -> str:
    """H({chain, prev, primary, secondary, username}), keys in that sorted order.

    ``primary`` is the synced online row's primary. ``secondary`` is the offline
    row's secondary. ``prev`` is the previous tie-break hash.
    """
    return sha_bytes(
        canon(
            {
                "chain": "tiebreak",
                "prev": prev or GENESIS,
                "primary": primary,
                "secondary": secondary,
                "username": str(username),
            }
        )
    )


def runtime_tiebreak_index_key(username: str, document_hash: str) -> str:
    """Unique index key (username, document_hash). Repeat sync matches this key."""
    return f"{username}\0{document_hash}"


def runtime_tiebreak_tip(rows: list | None = None, pick=None) -> str:
    """Last synced tie-break hash in ``rows``, or genesis when none are synced."""
    tip = GENESIS
    getter = pick or (lambda row: row.get("lattice") if isinstance(row, dict) else None)
    for row in rows or []:
        lat = getter(row)
        tb = lat.get("tiebreak") if isinstance(lat, dict) else None
        digest = tb.get("hash") if isinstance(tb, dict) and tb.get("status") == "synced" else None
        if isinstance(digest, str) and len(digest) == 64 and all(c in _HEX64 for c in digest):
            tip = digest
    return tip


def runtime_receipt_lattice(primary: str, secondary: str, source: dict | None = None) -> dict:
    """Receipt lattice view. Tie-break is copied only when the row already has one.

    A row without a tiebreak block gets exactly ``primary`` and ``secondary``,
    so its receipt JSON does not gain a key.
    """
    out: dict = {"primary": primary, "secondary": secondary}
    tb = source.get("tiebreak") if isinstance(source, dict) else None
    if isinstance(tb, dict):
        out["tiebreak"] = tb
    return out
