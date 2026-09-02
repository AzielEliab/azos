"""Small JSON import/export for AZ-OS. Author: Aziel Eliab."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from azos import __version__

AUTHOR = "Aziel Eliab"
PRODUCT = "AZ-OS"
STATE_NAME = ".azos-state.json"


def _as_path(path: str | Path) -> Path:
    return Path(path)


def import_json(path: str | Path) -> dict[str, Any]:
    pth = _as_path(path)
    doc = json.loads(pth.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise ValueError("JSON object required")
    dest = Path.cwd() / STATE_NAME
    dest.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "imported": str(pth),
        "stored": str(dest),
        "keys": sorted(str(k) for k in doc.keys()),
        "author": AUTHOR,
        "product": PRODUCT,
        "version": __version__,
    }


def export_json(path: str | Path) -> dict[str, Any]:
    pth = _as_path(path)
    src = Path.cwd() / STATE_NAME
    payload: Any = {}
    if src.exists():
        try:
            payload = json.loads(src.read_text(encoding="utf-8"))
        except Exception:
            payload = {}
    doc = {
        "product": PRODUCT,
        "package": "azos",
        "version": __version__,
        "author": AUTHOR,
        "payload": payload,
    }
    pth.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "exported": str(pth),
        "author": AUTHOR,
        "product": PRODUCT,
        "version": __version__,
    }
