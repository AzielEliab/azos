"""Overlay boot. The userspace base is not this boot.

``boot_overlay`` runs the process entry, then writes a boot receipt and
reads it back. It does not boot hardware and it does not treat the
userspace proof file as a boot.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azos.chains import canon, sha_bytes
from azos.entry import enter
from azos.paths import session_dir


def boot_overlay(root: Path | str) -> dict[str, Any]:
    """Boot the overlay session. Fail closed when the entry did not run."""
    root_path = Path(root)
    entered = enter(root_path)
    if entered.get("ok") is not True or entered.get("host_kernel") is True:
        return {
            "ok": False,
            "refused": True,
            "booted": False,
            "hardware": False,
            "userspace_is_boot": False,
            "code": "BOOT-ABSENT",
            "plain": "This has not booted.",
        }
    home = session_dir(root_path) / "boot"
    home.mkdir(parents=True, exist_ok=True)
    body = {
        "booted": True,
        "hardware": False,
        "userspace_is_boot": False,
        "entry_hash": entered.get("content_hash"),
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
    userspace = root_path / "userspace-proof" / "proof.txt"
    userspace_text = userspace.read_text(encoding="utf-8") if userspace.is_file() else ""
    checked = {key: loaded.get(key) for key in body}
    ok = (
        isinstance(loaded, dict)
        and loaded.get("booted") is True
        and loaded.get("hardware") is False
        and loaded.get("userspace_is_boot") is False
        and loaded.get("entry_hash") == entered.get("content_hash")
        and loaded.get("content_hash") == digest
        and sha_bytes(canon(checked)) == digest
        and userspace_text != "booted"
    )
    if not ok:
        return {
            "ok": False,
            "refused": True,
            "booted": False,
            "hardware": False,
            "userspace_is_boot": False,
            "code": "BOOT-ABSENT",
            "plain": "This has not booted.",
        }
    return {
        "ok": True,
        "refused": False,
        "booted": True,
        "hardware": False,
        "userspace_is_boot": False,
        "code": "BOOT-RAN",
        "content_hash": digest,
        "plain": "This has booted. That boot is not the userspace base.",
    }
