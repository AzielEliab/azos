"""In-process entry for AZ-OS.

The kernel door calls ``enter``. The call writes a receipt and reads it
back. This is not a host kernel, not a bootloader, and not a hypervisor.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azos.chains import canon, sha_bytes
from azos.paths import session_dir

ENTRY = "azos.entry"


def enter(root: Path | str) -> dict[str, Any]:
    """Run the process entry. The receipt must round-trip before this is ok."""
    home = session_dir(root) / "entry"
    home.mkdir(parents=True, exist_ok=True)
    body = {
        "entry": ENTRY,
        "host_kernel": False,
        "bootloader": False,
        "hypervisor": False,
    }
    digest = sha_bytes(canon(body))
    record = dict(body)
    record["content_hash"] = digest
    path = home / "receipt.json"
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = {}
    checked = {key: loaded.get(key) for key in body}
    ok = (
        isinstance(loaded, dict)
        and loaded.get("entry") == ENTRY
        and loaded.get("host_kernel") is False
        and loaded.get("bootloader") is False
        and loaded.get("hypervisor") is False
        and loaded.get("content_hash") == digest
        and sha_bytes(canon(checked)) == digest
    )
    if not ok:
        return {
            "ok": False,
            "refused": True,
            "code": "KERNEL-ABSENT",
            "entry": None,
            "host_kernel": False,
            "bootloader": False,
            "hypervisor": False,
            "plain": "There is no kernel.",
        }
    return {
        "ok": True,
        "refused": False,
        "code": "KERNEL-ENTERED",
        "entry": ENTRY,
        "host_kernel": False,
        "bootloader": False,
        "hypervisor": False,
        "content_hash": digest,
        "plain": "The AZ-OS entry ran. This is not a host kernel.",
    }
