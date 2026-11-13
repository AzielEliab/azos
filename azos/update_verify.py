"""AZ-UPDATE-MANIFEST-1.0 decision twin.

This is the AZ-OS adoption of aziel-runtime ``tools/auto_update_verify.py``
(the Python twin of ``src/auto-update/manifest.js``). Same canonical bytes,
same manifest hash, same refusal codes. Fail closed.

The published pin vouches for product ``aziel-runtime`` only. AZ-OS does not
generate a release key and does not print the private half (that half is not
in this repository).

Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any

SPEC = "AZ-UPDATE-MANIFEST-1.0"
# Published release pin. Private half stays in the GitHub Actions secret on
# AzielEliab/aziel-runtime. fingerprint = sha256(raw 32-byte key).
RELEASE_PUBLIC_KEY = "_3mc9CfQWexUWcyqDadNoQLjb6fFFPRv_XfWirwuH9s"
RELEASE_KEY_FINGERPRINT = "822b409723b81a0dc3fe3f132a2cb95b72b1ec2b2b16c055c526b627132a4ce8"
RELEASE_KEY_PRODUCTS = ("aziel-runtime",)
ACCEPTED_CHANNELS = ("stable",)
ARTIFACT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
WIN_RESERVED = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.I)
HEX64 = re.compile(r"^[a-f0-9]{64}$")
HEX40 = re.compile(r"^[a-f0-9]{40}$")
KEYS = sorted(
    [
        "artifact",
        "channel",
        "git_sha",
        "issued_at",
        "prev_manifest_hash",
        "product",
        "spec",
        "version",
        "version_seq",
    ]
)
MAXI = 2**53 - 1
_NON_INTEGER = re.compile(r"[0-9][.eE]|[.eE][0-9+-]")
_JSON_STRING = re.compile(r'"(?:[^"\\]|\\.)*"')


def artifact_name_ok(name: object) -> bool:
    return (
        isinstance(name, str)
        and ARTIFACT_NAME.fullmatch(name) is not None
        and ".." not in name
        and not name.endswith(".")
        and WIN_RESERVED.fullmatch(name) is None
    )


def canon(value: Any) -> str:
    """Canonical JSON. Same rules as the runtime Python twin."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite")
        return str(int(value)) if value.is_integer() and abs(value) < 1e21 else json.dumps(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(canon(item) for item in value) + "]"
    if isinstance(value, dict):
        return (
            "{"
            + ",".join(
                json.dumps(key, ensure_ascii=False) + ":" + canon(value[key]) for key in sorted(value)
            )
            + "}"
        )
    raise ValueError("cannot canonicalize")


def sint(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and abs(value) <= MAXI


def shape_ok(manifest: object) -> bool:
    if not isinstance(manifest, dict) or sorted(manifest) != KEYS:
        return False
    artifact = manifest["artifact"]
    return (
        manifest["spec"] == SPEC
        and isinstance(manifest["product"], str)
        and re.fullmatch(r"[a-z0-9-]{1,64}", manifest["product"]) is not None
        and isinstance(manifest["version"], str)
        and len(manifest["version"]) <= 40
        and sint(manifest["version_seq"])
        and manifest["version_seq"] > 0
        and isinstance(manifest["git_sha"], str)
        and HEX40.match(manifest["git_sha"]) is not None
        and manifest["channel"] in ("stable", "rc")
        and isinstance(manifest["issued_at"], str)
        and (
            manifest["prev_manifest_hash"] is None
            or (
                isinstance(manifest["prev_manifest_hash"], str)
                and HEX64.match(manifest["prev_manifest_hash"]) is not None
            )
        )
        and isinstance(artifact, dict)
        and sorted(artifact) == ["name", "sha256", "size"]
        and isinstance(artifact["name"], str)
        and artifact_name_ok(artifact["name"])
        and sint(artifact["size"])
        and artifact["size"] >= 0
        and isinstance(artifact["sha256"], str)
        and HEX64.match(artifact["sha256"]) is not None
    )


def b64u(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sig_ok(public_key: str, manifest: dict[str, Any], signature: str) -> bool:
    """Ed25519 over the canonical manifest. Missing library fails closed."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        Ed25519PublicKey.from_public_bytes(b64u(public_key)).verify(
            b64u(signature), canon(manifest).encode()
        )
        return True
    except Exception:
        return False


def manifest_hash(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canon(manifest).encode()).hexdigest()


def parse_manifest_text(text: object) -> dict[str, Any] | None:
    """Strict manifest parse. Non-integer numbers (``5.0``, ``1e0``) are refused.

    Matches ``parseManifestJson`` in the runtime manifest module: a float must
    not sneak through as an integer sequence.
    """
    if not isinstance(text, str):
        return None
    bare = _JSON_STRING.sub('""', text)
    bare = bare.replace("true", "").replace("false", "").replace("null", "")
    if _NON_INTEGER.search(bare):
        return None
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def verify_manifest(
    manifest: object,
    signature: object,
    state: object,
    public_key: str | None = RELEASE_PUBLIC_KEY,
) -> dict[str, Any]:
    """Decide whether a manifest may be applied. Pure aside from signature math."""
    if not public_key:
        return {"ok": False, "code": "UPDATE-NO-KEY"}
    if not shape_ok(manifest):
        return {"ok": False, "code": "UPDATE-MANIFEST-SHAPE"}
    if not isinstance(manifest, dict):
        return {"ok": False, "code": "UPDATE-MANIFEST-SHAPE"}
    if not isinstance(state, dict) or manifest["product"] != state.get("product"):
        return {"ok": False, "code": "UPDATE-PRODUCT"}
    if public_key == RELEASE_PUBLIC_KEY and manifest["product"] not in RELEASE_KEY_PRODUCTS:
        return {"ok": False, "code": "UPDATE-NO-KEY"}
    if manifest["channel"] not in ACCEPTED_CHANNELS:
        return {"ok": False, "code": "UPDATE-CHANNEL-REFUSED"}
    if not isinstance(signature, str) or not sig_ok(public_key, manifest, signature):
        return {"ok": False, "code": "UPDATE-SIG"}

    def seq_ok(value: object) -> bool:
        return value is None or (sint(value) and value >= 0)

    if not seq_ok(state.get("installed_seq")) or not seq_ok(state.get("floor_seq")):
        return {"ok": False, "code": "UPDATE-STATE"}
    if state.get("installed_seq") is None and state.get("floor_seq") is None:
        return {"ok": False, "code": "UPDATE-STATE"}
    installed = state.get("installed_seq") or 0
    floor = state.get("floor_seq") or 0
    if manifest["version_seq"] <= max(installed, floor):
        return {"ok": False, "code": "UPDATE-DOWNGRADE"}
    return {"ok": True, "code": "UPDATE-OK", "manifest_hash": manifest_hash(manifest)}


def fingerprint(public_key: str) -> str | None:
    """sha256 of the raw key. None when the text is not a 32-byte key."""
    try:
        raw = b64u(public_key)
    except Exception:
        return None
    if len(raw) != 32:
        return None
    return hashlib.sha256(raw).hexdigest()
