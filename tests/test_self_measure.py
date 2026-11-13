"""Boot self-measure reports verified, mismatch, or unknown, and does not invent verified."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from azos.boot import boot_overlay
from azos.measure import (
    PINNED_PUBLIC_KEY,
    SPEC,
    installed_files,
    measure_tree,
    self_measure,
    tree_sha256,
)


def _canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign(manifest: dict) -> tuple[str, str]:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    signature = private.sign(_canon(manifest))
    return _b64(public), _b64(signature)


def _install(tmp_path: Path, body: bytes = b"print('azos')\n") -> Path:
    root = tmp_path / "azos"
    root.mkdir()
    (root / "app.py").write_bytes(body)
    return root


def _manifest(root: Path) -> dict:
    files = installed_files(root)
    return {
        "files": files,
        "product": "azos",
        "spec": SPEC,
        "tree_sha256": tree_sha256(files),
    }


def test_signed_tree_verifies_and_a_changed_file_is_a_mismatch(tmp_path: Path) -> None:
    root = _install(tmp_path)
    manifest = json.loads(json.dumps(_manifest(root)))
    public, signature = _sign(manifest)
    verified = measure_tree(root, manifest=manifest, signature=signature, public_key=public)
    assert verified["status"] == "verified"
    assert verified["signed"] is True
    assert verified["match"] is True
    assert verified["pinned"] is True
    assert verified["booted"] is False
    assert verified["live"] is False
    assert verified["installed"] is False
    assert verified["satellite_relay"] == "HELD"
    assert verified["cap7_is_path"] is False
    assert verified["public_icann"] is False

    (root / "app.py").write_bytes(b"print('tampered')\n")
    mismatch = measure_tree(root, manifest=manifest, signature=signature, public_key=public)
    assert mismatch["status"] == "mismatch"
    assert mismatch["signed"] is True
    assert mismatch["match"] is False
    assert mismatch["status"] != "verified"


def test_missing_or_bad_signature_stays_unknown(tmp_path: Path) -> None:
    root = _install(tmp_path)
    manifest = _manifest(root)
    public, signature = _sign(manifest)
    unsigned = measure_tree(root, manifest=manifest, signature=None, public_key=public)
    assert unsigned["status"] == "unknown"
    assert unsigned["signed"] is False
    bad = measure_tree(root, manifest=manifest, signature=signature[:-4] + "AAAA", public_key=public)
    assert bad["status"] == "unknown"
    assert bad["match"] is False
    claimed = dict(manifest)
    claimed["status"] = "verified"
    forged = measure_tree(root, manifest=claimed, signature=signature, public_key=public)
    assert forged["status"] == "unknown"
    assert forged["status"] != "verified"
    unpinned = measure_tree(root, manifest=manifest, signature=signature, public_key="")
    assert unpinned["status"] == "unknown"
    assert unpinned["pinned"] is False


def test_startup_measure_does_not_fake_verified(tmp_path: Path) -> None:
    assert PINNED_PUBLIC_KEY == ""
    report = self_measure()
    assert report["status"] == "unknown"
    assert report["pinned"] is False
    assert report["signed"] is False
    assert report["match"] is False
    assert report["booted"] is False
    assert report["live"] is False
    assert report["satellite_relay"] == "HELD"
    assert report["cap7_is_path"] is False
    booted = boot_overlay(tmp_path)
    assert booted["booted"] is False
    assert booted["self_measure"] == "unknown"
    assert booted["code"] == "BOOT-ABSENT"
