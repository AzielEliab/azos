"""Boot self-measure against a signed release manifest.

At startup the process hashes the installed program files and compares
that tree to a signed manifest. The status is one of:

- ``verified`` — the pinned key signed this manifest, and every hashed
  file matches it
- ``mismatch`` — the signature is valid and the tree does not match
- ``unknown`` — there is no pin, no manifest, a bad signature, or the
  tree could not be read

``verified`` is not read from the manifest and is not returned for any
other case. An empty pin stays unknown. This is not a boot, not a live
flag, and not a paid satellite.

Author: Aziel Eliab.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

SPEC = "AZOS-SELF-MEASURE-1"
PRODUCT = "azos"
# Empty on purpose. A key file beside the program is not a pin, and this
# tree does not invent a release signature. Empty stays unknown.
PINNED_PUBLIC_KEY = ""
MANIFEST_NAME = "self-measure.json"
SIGNATURE_NAME = "self-measure.sig"

_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_PATH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,200}$")
_SKIP_DIRS = {"__pycache__", ".git"}
_SKIP_NAMES = {MANIFEST_NAME, SIGNATURE_NAME, "self-measure.pub"}

_CACHE: dict[str, Any] | None = None


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _b64u(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def tree_sha256(files: list[dict[str, str]]) -> str:
    return hashlib.sha256(_canon({"files": files})).hexdigest()


def _blank(*, tree: str | None = None, pinned: bool = False) -> dict[str, Any]:
    return {
        "status": "unknown",
        "spec": SPEC,
        "product": PRODUCT,
        "pinned": pinned,
        "signed": False,
        "match": False,
        "manifest_present": False,
        "tree_sha256": tree,
        "file_count": 0,
        "booted": False,
        "live": False,
        "installed": False,
        "satellite_relay": "HELD",
        "cap7_is_path": False,
        "public_icann": False,
        "bgp": False,
    }


def _path_ok(path: str) -> bool:
    if not isinstance(path, str) or _PATH.fullmatch(path) is None:
        return False
    if path.startswith("/") or "\\" in path or path.endswith("/"):
        return False
    return all(part not in {"", ".", ".."} for part in path.split("/"))


def shape_ok(manifest: object) -> bool:
    if not isinstance(manifest, dict) or set(manifest) != {"files", "product", "spec", "tree_sha256"}:
        return False
    if manifest.get("spec") != SPEC or manifest.get("product") != PRODUCT:
        return False
    tree = manifest.get("tree_sha256")
    files = manifest.get("files")
    if not isinstance(tree, str) or _HEX64.fullmatch(tree) is None:
        return False
    if not isinstance(files, list) or not files:
        return False
    seen: list[str] = []
    for row in files:
        if not isinstance(row, dict) or set(row) != {"path", "sha256"}:
            return False
        path = row.get("path")
        digest = row.get("sha256")
        if not _path_ok(path) or not isinstance(digest, str) or _HEX64.fullmatch(digest) is None:
            return False
        seen.append(path)
    if seen != sorted(seen) or len(set(seen)) != len(seen):
        return False
    return tree == tree_sha256(files)


def sig_ok(public_key: str, manifest: dict[str, Any], signature: str) -> bool:
    """Ed25519 over the canonical manifest. A missing library fails closed."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        raw = _b64u(public_key)
        sig = _b64u(signature)
        if len(raw) != 32 or len(sig) != 64:
            return False
        Ed25519PublicKey.from_public_bytes(raw).verify(sig, _canon(manifest))
        return True
    except Exception:
        return False


def _hash_tree(root: Path) -> list[dict[str, str]]:
    if not root.is_dir() or root.is_symlink():
        raise OSError("install root is not a directory")
    rows: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        parts = rel.split("/")
        if any(part in _SKIP_DIRS for part in parts):
            continue
        if path.name in _SKIP_NAMES or path.suffix == ".pyc":
            continue
        if not _path_ok(rel):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append({"path": rel, "sha256": digest})
    rows.sort(key=lambda row: row["path"])
    return rows


def installed_files(root: Path | str) -> list[dict[str, str]]:
    """Sorted path and sha256 rows for the program files under ``root``."""
    return _hash_tree(Path(root))


def measure_tree(
    root: Path | str,
    *,
    manifest: object = None,
    signature: str | None = None,
    public_key: str | None = None,
) -> dict[str, Any]:
    """Compare ``root`` to a signed manifest. Never reports verified unless both checks pass."""
    pin = PINNED_PUBLIC_KEY if public_key is None else public_key
    pinned = bool(pin)
    try:
        files = _hash_tree(Path(root))
    except OSError:
        return _blank(pinned=pinned)
    tree = tree_sha256(files) if files else None
    report = _blank(tree=tree, pinned=pinned)
    report["file_count"] = len(files)
    if not pinned or not isinstance(signature, str) or not signature:
        return report
    if not shape_ok(manifest):
        return report
    if not isinstance(manifest, dict) or not sig_ok(pin, manifest, signature):
        return report
    report["signed"] = True
    report["manifest_present"] = True
    if manifest["tree_sha256"] != tree or manifest["files"] != files:
        report["status"] = "mismatch"
        report["match"] = False
        return report
    report["status"] = "verified"
    report["match"] = True
    return report


def _read_pair(directory: Path) -> tuple[object, str | None]:
    manifest_path = directory / MANIFEST_NAME
    sig_path = directory / SIGNATURE_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        return None, None
    if not sig_path.is_file() or sig_path.is_symlink():
        return None, None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        signature = sig_path.read_text(encoding="utf-8").strip()
    except (OSError, json.JSONDecodeError):
        return None, None
    return manifest, signature or None


def self_measure() -> dict[str, Any]:
    """Hash this install at startup. An unpinned tree stays unknown."""
    global _CACHE
    if _CACHE is None:
        root = Path(__file__).resolve().parent
        manifest: object = None
        signature: str | None = None
        if PINNED_PUBLIC_KEY:
            manifest, signature = _read_pair(root / "data")
        _CACHE = measure_tree(
            root,
            manifest=manifest,
            signature=signature,
            public_key=PINNED_PUBLIC_KEY,
        )
    return copy.deepcopy(_CACHE)


def reset_cache() -> None:
    """Drop the startup cache. Tests call this after nothing else should."""
    global _CACHE
    _CACHE = None
