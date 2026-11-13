"""Overlay note. The userspace base is not a boot.

``boot_overlay`` writes a receipt that says this has not booted. A
process receipt and a userspace file are not a boot, and this module
does not boot hardware.

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
    """Record that this has not booted. Fail closed on any other reading."""
    root_path = Path(root)
    entered = enter(root_path)
    userspace = root_path / "userspace-proof" / "proof.txt"
    userspace_text = userspace.read_text(encoding="utf-8") if userspace.is_file() else ""
    home = session_dir(root_path) / "boot"
    home.mkdir(parents=True, exist_ok=True)
    from azos.install import adopt_signed
    from azos.measure import self_measure

    update = adopt_signed(root_path)
    measured = self_measure()
    measure_status = measured.get("status") if measured.get("status") in {"verified", "mismatch", "unknown"} else "unknown"
    if measure_status == "verified" and not (measured.get("signed") is True and measured.get("match") is True):
        measure_status = "unknown"
    body = {
        "booted": False,
        "hardware": False,
        "userspace_is_boot": False,
        "process_receipt_is_boot": False,
        "kernel_base": False,
        "entry_hash": entered.get("content_hash"),
        "update_code": update.get("code") if isinstance(update.get("code"), str) else "UPDATE-STATE",
        "update_applied": update.get("applied") is True,
        "update_live": False,
        "self_measure": measure_status,
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
        and loaded.get("booted") is False
        and loaded.get("hardware") is False
        and loaded.get("userspace_is_boot") is False
        and loaded.get("process_receipt_is_boot") is False
        and loaded.get("kernel_base") is False
        and loaded.get("update_live") is False
        and loaded.get("update_applied") is body["update_applied"]
        and loaded.get("content_hash") == digest
        and sha_bytes(canon(checked)) == digest
        and userspace_text != "booted"
    )
    return {
        "ok": False,
        "refused": True,
        "booted": False,
        "hardware": False,
        "userspace_is_boot": False,
        "kernel_base": False,
        "process_receipt_is_boot": False,
        "receipt": receipt_ok,
        "code": "BOOT-ABSENT",
        "content_hash": digest if receipt_ok else None,
        "plain": "This has not booted.",
        "update": update,
        "self_measure": measure_status,
    }
