"""One HTTP GET for an existing AZ-OS door.

Cleartext is only accepted for 127.0.0.1 and localhost. Public URLs
must be HTTPS. This module does not bind a socket and does not open
0.0.0.0.

Author: Aziel Eliab.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from urllib.parse import urlparse

from azos.errors import AzosError

USER_AGENT = "Mozilla/5.0"
_LOOPBACK = frozenset({"127.0.0.1", "localhost"})


def get_bytes(url: str, *, limit: int = 2_000_000, timeout: float = 8.0) -> tuple[int, bytes]:
    """Return (status, body). A refused URL raises. A transport error returns (0, b"")."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme == "https" and host:
        allowed = True
    elif parsed.scheme == "http" and host in _LOOPBACK:
        allowed = True
    else:
        allowed = False
    if not allowed:
        raise AzosError("That URL is not on the fetch door.")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read(limit)
    except urllib.error.HTTPError as exc:
        body = exc.read(min(limit, 4096))
        return int(exc.code), body
    except Exception:
        return 0, b""
