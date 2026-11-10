"""AZ-AUTO-UPDATE-1.0 apply twin.

Adoption of aziel-runtime ``tools/auto_update_updater.py``. Same codes and the
same lattice primary and secondary tips. Default OFF. ``live`` stays false.
An empty release key refuses ``UPDATE-NO-KEY`` and does not fetch.

Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

import hashlib
from typing import Any, Callable

from azos import update_verify as V

UPDATER_SPEC = "AZ-AUTO-UPDATE-1.0"
GENESIS = "0" * 64
MESH_CARRIER_ORDER = ("lan", "wifi", "bluetooth", "rf", "photon")
C = {
    "off": "UPDATE-OFF",
    "paused": "UPDATE-PAUSED",
    "hash": "UPDATE-HASH",
    "health": "UPDATE-HEALTH",
    "carrier": "UPDATE-CARRIER-ABSENT",
    "ok": "UPDATE-OK",
    "noKey": "UPDATE-NO-KEY",
    "noRelease": "UPDATE-NO-RELEASE",
}


def _h(data: str | bytes) -> str:
    raw = data.encode() if isinstance(data, str) else data
    return hashlib.sha256(raw).hexdigest()


def initial_state(product: str, installed_seq: int = 0) -> dict[str, Any]:
    return {
        "product": product,
        "installed_seq": installed_seq,
        "floor_seq": installed_seq,
        "paused": False,
        "manifest_hash": None,
        "last_check": None,
        "last_applied": None,
        "last_code": None,
        "tips": None,
        "served_manifest": None,
    }


def status(state: dict[str, Any], enabled: bool = False, public_key: str | None = None) -> dict[str, Any]:
    return {
        "enabled": enabled is True,
        "paused": bool(state.get("paused")),
        "key_pinned": bool(public_key),
        "last_check": state.get("last_check"),
        "last_applied": state.get("last_applied"),
        "last_code": state.get("last_code"),
        "live": False,
    }


def plan_lattice(document_hash: str, offline: bool, username: str, tips: object) -> dict[str, str]:
    if (
        isinstance(tips, dict)
        and all(isinstance(tips.get(key), str) and len(tips[key]) == 64 for key in ("primary", "secondary"))
    ):
        current = {"primary": tips["primary"], "secondary": tips["secondary"]}
    else:
        current = {"primary": GENESIS, "secondary": GENESIS}
    primary = _h(V.canon({"document": document_hash, "prev": current["primary"]}))
    if offline is True:
        secondary = _h(V.canon({"primary": document_hash, "username": username}))
    else:
        secondary = _h(V.canon({"offline": False, "prev": current["secondary"], "primary": primary}))
    return {"primary": primary, "secondary": secondary}


def update_receipt(host: Any, state: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    handle = "node-" + _h(str(getattr(host, "node_id", None) or "unknown"))[:16]
    document_hash = _h(V.canon({"kind": "update", "spec": UPDATER_SPEC, **doc}))
    lattice = plan_lattice(document_hash, getattr(host, "offline", False) is True, handle, state.get("tips"))
    state["tips"] = {"primary": lattice["primary"], "secondary": lattice["secondary"]}
    row = {"kind": "update", **doc, "lattice": lattice}
    write = getattr(host, "write_receipt", None)
    if write:
        write(row)
    return row


def _paused_now(host: Any) -> bool:
    try:
        current = host.load()
        return (not current) or current.get("paused") is True
    except Exception:
        return True


def _rollback(host: Any, state: dict[str, Any]) -> str:
    try:
        host.rollback()
        return "rolled_back"
    except Exception:
        state["paused"] = True
        return "rollback_failed"


def apply_offer(
    host: Any,
    offer: object,
    source: str,
    fetch_bytes: Callable[[dict[str, Any]], object],
    public_key: str | None = V.RELEASE_PUBLIC_KEY,
) -> dict[str, Any]:
    """Apply one signed offer. ``source`` is ``online``, ``offline``, or ``mesh:<carrier>``."""
    state = host.load()
    at = host.now()
    state["last_check"] = at
    manifest = offer.get("manifest") if isinstance(offer, dict) else None
    to_seq = manifest["version_seq"] if isinstance(manifest, dict) and V.sint(manifest.get("version_seq")) else None

    def done(code: str, manifest_hash: str | None = None, outcome: str = "refused") -> dict[str, Any]:
        state["last_code"] = code
        row = update_receipt(
            host,
            state,
            {
                "product": state.get("product"),
                "from_seq": state.get("installed_seq"),
                "to_seq": to_seq,
                "manifest_hash": manifest_hash,
                "source": source,
                "outcome": outcome,
                "code": code,
                "at": at,
            },
        )
        host.save(state)
        return {"ok": code == C["ok"], "code": code, "row": row, "live": False}

    if host.enabled is not True:
        return done(C["off"])
    if state.get("paused"):
        return done(C["paused"])
    if not public_key:
        return done(C["noKey"])
    if isinstance(offer, dict) and offer.get("refused") is True and offer.get("code") == C["noRelease"]:
        return done(C["noRelease"])
    try:
        verdict = V.verify_manifest(
            manifest,
            offer.get("signature") if isinstance(offer, dict) else None,
            state,
            public_key,
        )
    except Exception:
        verdict = {"ok": False, "code": "UPDATE-MANIFEST-SHAPE"}
    if not verdict["ok"]:
        return done(verdict["code"])
    try:
        data = fetch_bytes(manifest)
    except Exception:
        data = None
    if (
        not isinstance(data, (bytes, bytearray))
        or len(data) != manifest["artifact"]["size"]
        or _h(bytes(data)) != manifest["artifact"]["sha256"]
    ):
        return done(C["hash"], verdict.get("manifest_hash"))
    if _paused_now(host):
        state["paused"] = True
        return done(C["paused"], verdict.get("manifest_hash"))
    try:
        host.stage(bytes(data), manifest)
        host.swap()
        if not host.health_check():
            raise RuntimeError("health")
        if _paused_now(host):
            state["paused"] = True
            return done(C["paused"], verdict.get("manifest_hash"), _rollback(host, state))
    except Exception:
        return done(C["health"], verdict.get("manifest_hash"), _rollback(host, state))
    state["installed_seq"] = manifest["version_seq"]
    state["floor_seq"] = max(state.get("floor_seq") or 0, state["installed_seq"])
    state["manifest_hash"] = verdict["manifest_hash"]
    state["served_manifest"] = {"manifest": manifest, "signature": offer["signature"]}
    state["last_applied"] = at
    return done(C["ok"], verdict["manifest_hash"], "applied")


def check_online(host: Any, public_key: str | None = V.RELEASE_PUBLIC_KEY) -> dict[str, Any]:
    try:
        offer = host.fetch_release()
    except Exception:
        offer = None
    return apply_offer(host, offer, "online", host.fetch_artifact, public_key)


def on_internet_reach(host: Any, public_key: str | None = V.RELEASE_PUBLIC_KEY) -> dict[str, Any]:
    if getattr(host, "enabled", False) is not True:
        return {
            "ok": False,
            "code": "UPDATE-OFF",
            "trigger": "internet",
            "enabled": False,
            "live": False,
            "applied": False,
        }
    if not public_key:
        return {
            "ok": False,
            "code": "UPDATE-NO-KEY",
            "trigger": "internet",
            "live": False,
            "applied": False,
            "enabled": True,
        }
    probe = getattr(host, "internet_reachable", None)
    if callable(probe):
        try:
            up = probe() is True
        except Exception:
            up = False
        code = "UPDATE-INTERNET-UNREACHABLE"
    else:
        up = False
        code = "UPDATE-NO-REACH-PROBE"
    if not up:
        return {
            "ok": False,
            "code": code,
            "trigger": "internet",
            "live": False,
            "applied": False,
            "enabled": True,
        }
    out = check_online(host, public_key)
    out["trigger"] = "internet"
    out["live"] = False
    return out


def on_peer_contact(host: Any, public_key: str | None = V.RELEASE_PUBLIC_KEY) -> dict[str, Any]:
    """Walk Plane P carriers. Absent hardware refuses. A peer is not trusted."""
    if getattr(host, "enabled", False) is not True:
        return {
            "ok": False,
            "code": "UPDATE-OFF",
            "trigger": "mesh",
            "enabled": False,
            "live": False,
            "applied": False,
        }
    if not public_key:
        return {
            "ok": False,
            "code": "UPDATE-NO-KEY",
            "trigger": "mesh",
            "live": False,
            "applied": False,
            "enabled": True,
        }
    carrier = None
    for cid in MESH_CARRIER_ORDER:
        try:
            if host.carrier_present(cid):
                carrier = cid
                break
        except Exception:
            continue

    def refuse(code: str, source: str) -> dict[str, Any]:
        state = host.load()
        state["last_code"] = code
        update_receipt(
            host,
            state,
            {
                "product": state.get("product"),
                "from_seq": state.get("installed_seq"),
                "to_seq": None,
                "manifest_hash": None,
                "source": source,
                "outcome": "refused",
                "code": code,
                "at": host.now(),
            },
        )
        host.save(state)
        return {
            "ok": False,
            "code": code,
            "carrier": carrier,
            "trigger": "mesh",
            "live": False,
            "applied": False,
            "enabled": True,
            "hardware": False,
            "radio_phy": False,
            "second_device": False,
        }

    if not carrier:
        return refuse(C["carrier"], "mesh:none")
    try:
        hello = host.peer_hello(carrier)
    except Exception:
        hello = None
    if isinstance(hello, dict) and hello.get("refused") is True:
        code = hello.get("code")
        if not isinstance(code, str) or not code.startswith("UPDATE-"):
            code = "UPDATE-PEER-NO-ROUTE"
        return refuse(code, "mesh:" + carrier)
    if not isinstance(hello, dict):
        return refuse("UPDATE-PEER-NO-ROUTE", "mesh:" + carrier)
    state = host.load()
    if (
        hello.get("product") != state.get("product")
        or not V.sint(hello.get("version_seq"))
        or hello["version_seq"] <= (state.get("installed_seq") or 0)
    ):
        return {
            "ok": True,
            "code": "UPDATE-PEER-NOT-NEWER",
            "carrier": carrier,
            "applied": False,
            "trigger": "mesh",
            "live": False,
            "enabled": True,
            "hardware": False,
            "radio_phy": False,
            "second_device": False,
        }
    fetched = host.peer_fetch(carrier, hello.get("manifest"))
    if isinstance(fetched, dict) and fetched.get("refused") is True:
        code = fetched.get("code")
        if not isinstance(code, str) or not code.startswith("UPDATE-"):
            code = "UPDATE-PEER-NO-ARTIFACT"
        return refuse(code, "mesh:" + carrier)
    result = apply_offer(
        host,
        {"manifest": hello.get("manifest"), "signature": hello.get("signature")},
        "mesh:" + carrier,
        lambda _manifest: fetched,
        public_key,
    )
    result.update(
        {
            "carrier": carrier,
            "trigger": "mesh",
            "live": False,
            "enabled": True,
            "hardware": False,
            "radio_phy": False,
            "second_device": False,
        }
    )
    return result
