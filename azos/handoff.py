"""PID 1 handoff. The updater stays OFF.

``image/init`` is PID 1. It seals ``AZOS-BOOT-1``, prints the handoff
line, and powers off. It does not exec Python, does not start an
updater, and does not swap the kernel.

A peer may offer a version string. This module compares that string
with the local package version. It does not fetch, apply, or name a
URL. No signing key, release, or release URL is created here.

The updater stays OFF. A claimed key is not verified by this module,
so a claim does not enable an update. ``booted`` and ``live`` stay false.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from azos import __version__
from azos.chains import canon, sha_bytes
from azos.paths import session_dir

SPEC = "AZOS-HANDOFF-1"
CODE = "HANDOFF-ABSENT"
UPDATER = "OFF"
HANDOFF_LINE = (
    "AZOS handoff: updater OFF (no operator signing key) "
    "kernel_swap: absent userspace: absent"
)
SEALED_UPDATER = '"updater":"OFF"'
SEALED_KERNEL_SWAP = '"kernel_swap":false'
SEALED_HANDOFF = '"handoff":"absent"'
SEALED_USERSPACE = '"userspace":"absent"'
# image/init stores the sealed JSON in a double-quoted shell string.
_SEALED_SOURCE = (
    '\\"updater\\":\\"OFF\\"',
    '\\"kernel_swap\\":false',
    '\\"handoff\\":\\"absent\\"',
    '\\"userspace\\":\\"absent\\"',
)

_VERSION_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_BANNED_INIT = ("kexec", "python", "http" + "://", "https" + "://", "wget", "curl")
_PEER_EXTRA = frozenset(
    {
        "url",
        "uri",
        "href",
        "manifest",
        "signature",
        "artifact",
        "key",
        "public_key",
        "fetch",
        "apply",
        "release",
    }
)


def init_markers() -> tuple[str, ...]:
    """Runtime seal fields. The updater token is OFF."""
    return (HANDOFF_LINE, SEALED_UPDATER, SEALED_KERNEL_SWAP, SEALED_HANDOFF, SEALED_USERSPACE)


def design_matches_init(text: str) -> bool:
    """True when ``image/init`` seals the handoff and does not start one."""
    if HANDOFF_LINE not in text or any(marker not in text for marker in _SEALED_SOURCE):
        return False
    code = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    if any(word in code for word in _BANNED_INIT):
        return False
    commands = [line.strip() for line in code.splitlines() if line.strip()]
    return bool(commands) and commands[-1] == "poweroff -f"


def key_reason(claimed_key: object) -> str:
    """Name why the updater stays OFF. The claim itself is not kept."""
    if isinstance(claimed_key, str) and claimed_key.strip() == "":
        return "NO-OPERATOR-KEY"
    if claimed_key is None:
        return "NO-OPERATOR-KEY"
    return "KEY-UNVERIFIED"


def kernel_swap_path() -> dict[str, Any]:
    """The swap path is named and not executed. There is no kexec."""
    return {
        "executed": False,
        "kexec": False,
        "kernel_swapped": False,
        "booted": False,
        "live": False,
        "code": "KERNEL-SWAP-ABSENT",
        "steps": [
            {"name": "verify_signed_artifact", "done": False, "needs": "a real operator signing key"},
            {"name": "stage_kernel", "done": False, "needs": "a verified artifact"},
            {"name": "kexec", "done": False, "needs": "a staged kernel"},
        ],
        "plain": "The kernel was not swapped.",
    }


def pid1_contract() -> dict[str, Any]:
    """What PID 1 is written to do. This process is not PID 1."""
    return {
        "script": "image/init",
        "spec": "AZOS-BOOT-1",
        "guardian": "absent",
        "runs_python": False,
        "starts_updater": False,
        "swaps_kernel": False,
        "next": "poweroff",
        "plain": "PID 1 seals the boot line and powers off. It does not start the updater.",
    }


def _version_tuple(version: str) -> tuple[int, int, int] | None:
    if not isinstance(version, str) or _VERSION_RE.fullmatch(version) is None:
        return None
    major, minor, patch = version.split(".")
    return (int(major), int(minor), int(patch))


def _idle_sync(local: str) -> dict[str, Any]:
    return {
        "asked": False,
        "local": local,
        "peer": None,
        "relation": "not-asked",
        "fetch": False,
        "apply": False,
        "url": None,
        "updater": UPDATER,
        "updater_enabled": False,
        "code": "VERSION-SYNC-IDLE",
    }


def _refused_sync(local: str) -> dict[str, Any]:
    return {
        "asked": True,
        "local": local,
        "peer": None,
        "relation": "refused",
        "fetch": False,
        "apply": False,
        "url": None,
        "updater": UPDATER,
        "updater_enabled": False,
        "code": "VERSION-SYNC-REFUSED",
    }


def compare_version(peer: object = None, *, local: str | None = None) -> dict[str, Any]:
    """Compare a version string. Do not fetch, apply, or store a URL."""
    local_version = __version__ if local is None else local
    if _version_tuple(local_version) is None:
        return _refused_sync(__version__)
    if peer is None:
        return _idle_sync(local_version)
    if isinstance(peer, dict):
        if set(peer) != {"version"} or _PEER_EXTRA.intersection(peer):
            return _refused_sync(local_version)
        offered = peer.get("version")
    elif isinstance(peer, str):
        offered = peer
    else:
        return _refused_sync(local_version)
    if not isinstance(offered, str) or "://" in offered or offered.lower().startswith("http"):
        return _refused_sync(local_version)
    peer_tuple = _version_tuple(offered)
    local_tuple = _version_tuple(local_version)
    if peer_tuple is None or local_tuple is None:
        return _refused_sync(local_version)
    if peer_tuple == local_tuple:
        relation = "same"
    elif peer_tuple > local_tuple:
        relation = "peer-newer"
    else:
        relation = "local-newer"
    return {
        "asked": True,
        "local": local_version,
        "peer": offered,
        "relation": relation,
        "fetch": False,
        "apply": False,
        "url": None,
        "updater": UPDATER,
        "updater_enabled": False,
        "code": "VERSION-COMPARE-ONLY",
    }


def _body(reason: str, sync: dict[str, Any]) -> dict[str, Any]:
    swap = kernel_swap_path()
    pid1 = pid1_contract()
    return {
        "spec": SPEC,
        "author": "Aziel Eliab",
        "booted": False,
        "live": False,
        "hardware": False,
        "updater": UPDATER,
        "updater_enabled": False,
        "operator_key": "absent",
        "key_verified": False,
        "reason": reason,
        "userspace_started": False,
        "python_exec": False,
        "kernel_swapped": False,
        "kexec": False,
        "p2p_fetch": False,
        "applied": False,
        "release_named": False,
        "release_url": None,
        "pid1": {
            "script": pid1["script"],
            "spec": pid1["spec"],
            "guardian": pid1["guardian"],
            "runs_python": pid1["runs_python"],
            "starts_updater": pid1["starts_updater"],
            "swaps_kernel": pid1["swaps_kernel"],
            "next": pid1["next"],
        },
        "kernel_swap": {
            "executed": False,
            "code": swap["code"],
            "steps": swap["steps"],
        },
        "version_sync": sync,
    }


_SYNC_KEYS = frozenset(
    {
        "asked",
        "local",
        "peer",
        "relation",
        "fetch",
        "apply",
        "url",
        "updater",
        "updater_enabled",
        "code",
    }
)
_REASONS = frozenset({"NO-OPERATOR-KEY", "KEY-UNVERIFIED"})
_SWAP_STEPS = ("verify_signed_artifact", "stage_kernel", "kexec")


def _flags_hold(loaded: dict[str, Any], body: dict[str, Any]) -> bool:
    if set(loaded) != set(body) | {"content_hash"}:
        return False
    if loaded.get("reason") not in _REASONS:
        return False
    if loaded.get("updater") != UPDATER or loaded.get("updater_enabled") is not False:
        return False
    if loaded.get("operator_key") != "absent" or loaded.get("key_verified") is not False:
        return False
    if loaded.get("release_url") is not None or loaded.get("release_named") is not False:
        return False
    for name in (
        "booted",
        "live",
        "hardware",
        "userspace_started",
        "python_exec",
        "kernel_swapped",
        "kexec",
        "p2p_fetch",
        "applied",
    ):
        if loaded.get(name) is not False:
            return False
    pid1 = loaded.get("pid1")
    if not isinstance(pid1, dict):
        return False
    if pid1.get("next") != "poweroff" or pid1.get("script") != "image/init":
        return False
    if pid1.get("runs_python") is not False or pid1.get("starts_updater") is not False:
        return False
    if pid1.get("swaps_kernel") is not False or pid1.get("guardian") != "absent":
        return False
    swap = loaded.get("kernel_swap")
    if not isinstance(swap, dict) or swap.get("executed") is not False:
        return False
    if swap.get("code") != "KERNEL-SWAP-ABSENT":
        return False
    steps = swap.get("steps")
    if not isinstance(steps, list) or len(steps) != len(_SWAP_STEPS):
        return False
    for step, name in zip(steps, _SWAP_STEPS):
        if not isinstance(step, dict) or step.get("name") != name or step.get("done") is not False:
            return False
    sync = loaded.get("version_sync")
    if not isinstance(sync, dict) or set(sync) != _SYNC_KEYS:
        return False
    if sync.get("fetch") is not False or sync.get("apply") is not False or sync.get("url") is not None:
        return False
    if sync.get("updater") != UPDATER or sync.get("updater_enabled") is not False:
        return False
    if _version_tuple(str(sync.get("local"))) is None:
        return False
    peer = sync.get("peer")
    if peer is not None and _version_tuple(str(peer)) is None:
        return False
    raw = json.dumps(loaded)
    if "://" in raw or ("http" + "://") in raw or ("https" + "://") in raw:
        return False
    checked = {key: loaded.get(key) for key in body}
    return sha_bytes(canon(checked)) == sha_bytes(canon(body))


def record_handoff(
    root: Path | str,
    *,
    claimed_key: object = None,
    peer: object = None,
    local: str | None = None,
) -> dict[str, Any]:
    """Write the handoff receipt. Flags stay false. The updater stays OFF."""
    reason = key_reason(claimed_key)
    sync = compare_version(peer, local=local)
    body = _body(reason, sync)
    digest = sha_bytes(canon(body))
    stored = dict(body)
    stored["content_hash"] = digest
    home = session_dir(root) / "handoff"
    home.mkdir(parents=True, exist_ok=True)
    path = home / "receipt.json"
    path.write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = {}
    receipt_ok = (
        isinstance(loaded, dict)
        and loaded.get("content_hash") == digest
        and loaded.get("spec") == SPEC
        and _flags_hold(loaded, body)
    )
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    if isinstance(claimed_key, str) and len(claimed_key) >= 16 and claimed_key in text:
        receipt_ok = False
    return _summary(reason, sync, receipt_ok, digest if receipt_ok else None)


def read_handoff(root: Path | str) -> dict[str, Any]:
    """Read a handoff receipt. An altered file stays refused."""
    path = session_dir(root) / "handoff" / "receipt.json"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = {}
    if not isinstance(loaded, dict):
        loaded = {}
    reason = loaded.get("reason") if isinstance(loaded.get("reason"), str) else "NO-OPERATOR-KEY"
    sync = loaded.get("version_sync") if isinstance(loaded.get("version_sync"), dict) else _idle_sync(__version__)
    body = {key: loaded.get(key) for key in _body(reason, sync)}
    digest = loaded.get("content_hash")
    receipt_ok = (
        isinstance(digest, str)
        and _flags_hold(loaded, body)
        and sha_bytes(canon(body)) == digest
    )
    if not receipt_ok:
        sync = _idle_sync(__version__)
        reason = "NO-OPERATOR-KEY"
    return _summary(reason, sync, receipt_ok, digest if receipt_ok else None)


def _summary(reason: str, sync: dict[str, Any], receipt_ok: bool, digest: str | None) -> dict[str, Any]:
    return {
        "ok": False,
        "refused": True,
        "booted": False,
        "live": False,
        "hardware": False,
        "updater": UPDATER,
        "updater_enabled": False,
        "operator_key": "absent",
        "key_verified": False,
        "kernel_swapped": False,
        "kexec": False,
        "userspace_started": False,
        "python_exec": False,
        "p2p_fetch": False,
        "applied": False,
        "release_named": False,
        "release_url": None,
        "reason": reason,
        "version_sync": sync,
        "receipt": receipt_ok,
        "code": CODE,
        "content_hash": digest,
        "plain": "PID 1 does not start the updater. The kernel was not swapped.",
    }
