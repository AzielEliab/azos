"""In-process entry note for AZ-OS.

``enter`` writes a receipt and reads it back. The receipt is a file in
the session directory. It is not a host kernel, not a kernel base, not
a bootloader, and not a hypervisor.

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
    """Write the process receipt. A receipt does not make a kernel."""
    home = session_dir(root) / "entry"
    home.mkdir(parents=True, exist_ok=True)
    body = {
        "entry": ENTRY,
        "kernel": False,
        "kernel_base": False,
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
    receipt_ok = (
        isinstance(loaded, dict)
        and loaded.get("entry") == ENTRY
        and loaded.get("kernel") is False
        and loaded.get("kernel_base") is False
        and loaded.get("host_kernel") is False
        and loaded.get("bootloader") is False
        and loaded.get("hypervisor") is False
        and loaded.get("content_hash") == digest
        and sha_bytes(canon(checked)) == digest
    )
    return {
        "ok": False,
        "refused": True,
        "code": "KERNEL-ABSENT",
        "kernel": False,
        "kernel_base": False,
        "entry": ENTRY if receipt_ok else None,
        "host_kernel": False,
        "bootloader": False,
        "hypervisor": False,
        "process_receipt": receipt_ok,
        "content_hash": digest if receipt_ok else None,
        "plain": "There is no kernel.",
    }
