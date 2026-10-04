"""Local mailbox. A message is sent when it can be read back.

Both hash chains record the message. There is no public mail server.
The document itself is not marked live.

Author: Aziel Eliab.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from azos.chains import DualLattice, clean_username
from azos.errors import AzosError
from azos.paths import session_dir


def send_local(
    root: Path | str,
    *,
    username: str,
    recipient: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """Deliver one message into the local mailbox and read it back."""
    name = clean_username(username)
    to = str(recipient or "").strip()
    title = str(subject or "").strip()
    text = str(body or "")
    if not to or not title or not text:
        return _refused("A local message needs a recipient, a subject, and a body.")
    document = {
        "kind": "mail",
        "recipient": to,
        "subject": title,
        "body": text,
        "public_mta": False,
        "live": False,
    }
    lattice = DualLattice(session_dir(root) / "mail" / "lattice.json")
    try:
        row = lattice.append(document, name)
    except AzosError as exc:
        return _refused(str(exc))
    if not lattice.verify():
        return _refused("The mail chains did not verify.")
    found = lattice.find(row["content_hash"], name)
    sent = (
        isinstance(found, dict)
        and found.get("document", {}).get("body") == text
        and found.get("document", {}).get("public_mta") is False
        and found.get("live") is False
        and len(lattice.primary_chain()) == len(lattice.secondary_chain()) >= 1
    )
    if not sent:
        return _refused("The message was not read back.")
    return {
        "ok": True,
        "refused": False,
        "sent": True,
        "public_mta": False,
        "code": "MAIL-SENT",
        "username": name,
        "primary_hash": row["primary_hash"],
        "secondary_hash": row["secondary_hash"],
        "plain": "Mail can be sent from here to a local mailbox.",
    }


def _refused(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "refused": True,
        "sent": False,
        "public_mta": False,
        "code": "MAIL-SEND-REFUSED",
        "reason": reason,
        "plain": "Mail is not sent from here.",
    }
