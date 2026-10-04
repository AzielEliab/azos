"""Install AZ-OS into a directory this process chooses.

The copy stays under the destination. It does not install 4DMap, it does
not replace the host operating system, and it does not spawn a shell.
The one-click path is this same copy. The remote curl command is not run.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_PACKAGE = Path(__file__).resolve().parent
_SCRIPT = _PACKAGE.parent / "install.sh"
_SKIP = frozenset({"__pycache__"})


def _files() -> list[Path]:
    found: list[Path] = []
    for path in _PACKAGE.rglob("*"):
        if not path.is_file():
            continue
        if _SKIP.intersection(path.parts) or path.suffix == ".pyc":
            continue
        found.append(path)
    return sorted(found)


def place(dest: Path | str) -> dict[str, Any]:
    """Copy this package into ``dest / azos`` and read the hashes back."""
    root = Path(dest)
    target = root / "azos"
    copied: list[tuple[str, str]] = []
    for path in _files():
        rel = path.relative_to(_PACKAGE).as_posix()
        data = path.read_bytes()
        out = target / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        copied.append((rel, hashlib.sha256(data).hexdigest()))
    mismatch = [
        rel
        for rel, digest in copied
        if hashlib.sha256((target / rel).read_bytes()).hexdigest() != digest
    ]
    marker = root / "INSTALLED"
    receipt = {
        "placed": not mismatch and len(copied) > 0,
        "files": len(copied),
        "mismatch": mismatch,
        "fourdmap_installed": False,
        "host_os": False,
        "os_yet": False,
    }
    receipt_path = root / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    marker.write_text("Installed AZ-OS.\n", encoding="utf-8")
    try:
        loaded = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = {}
    ok = (
        isinstance(loaded, dict)
        and loaded.get("placed") is True
        and loaded.get("fourdmap_installed") is False
        and loaded.get("host_os") is False
        and int(loaded.get("files") or 0) == len(copied)
        and not mismatch
        and marker.read_text(encoding="utf-8") == "Installed AZ-OS.\n"
        and (target / "__init__.py").is_file()
        and (target / "fourdmap.py").is_file()
    )
    return {
        "ok": False,
        "refused": True,
        "placed": ok,
        "files": len(copied) if ok else 0,
        "fourdmap_installed": False,
        "host_os": False,
        "installed": False,
        "os_yet": False,
        "dest": str(root),
    }


def one_click(dest: Path | str) -> dict[str, Any]:
    """Run the in-process install path. Do not run curl or pip."""
    if not _SCRIPT.is_file():
        return {
            "ok": False,
            "refused": True,
            "placed": False,
            "remote_curl": False,
            "pip_ran": False,
            "host_shell": False,
            "code": "ONE-CLICK-NOT-LIVE",
            "plain": "One-click install is not live.",
        }
    script = _SCRIPT.read_text(encoding="utf-8")
    if "Installed AZ-OS." not in script or "pip install -e ." not in script:
        return {
            "ok": False,
            "refused": True,
            "placed": False,
            "remote_curl": False,
            "pip_ran": False,
            "host_shell": False,
            "code": "ONE-CLICK-NOT-LIVE",
            "plain": "One-click install is not live.",
        }
    placed = place(dest)
    return {
        "ok": False,
        "refused": True,
        "placed": placed.get("placed") is True,
        "installed": False,
        "os_yet": False,
        "files": placed.get("files"),
        "remote_curl": False,
        "pip_ran": False,
        "host_shell": False,
        "fourdmap_installed": False,
        "code": "ONE-CLICK-NOT-LIVE",
        "plain": "One-click install is not live.",
    }
