"""Runtime dual-lattice parity (AZRT-DUAL-LATTICE-1.0), additive.

These recompute the aziel-runtime lattice rules byte for byte so AZ-OS can
check a runtime receipt offline. ``azos.chains`` keeps its own news-chain
formula unchanged; this module does not replace it.

    primary           = H(canon({document, prev}))
    offline secondary = H(canon({primary: document_hash, username}))
    online secondary  = H(canon({offline: false, prev, primary}))

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
