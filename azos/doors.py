"""Flag proofs for the existing AZ-OS doors.

A flag is true only when that door performed its function. A refusing
door keeps its flag false. This module does not replace those doors.

Author: Aziel Eliab.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from azos.ethics import SCOPE


def require_flag(flag: bool, door: Mapping[str, Any]) -> None:
    """Fail when a flag is true while its door still refuses."""
    refused = door.get("refused") is True or door.get("ok") is not True
    if refused and flag is True:
        raise AssertionError("flag is true while the path still refuses")
    if not refused and flag is not True:
        raise AssertionError("the door performed and the flag is not true")


def kernel_door() -> dict[str, Any]:
    """No kernel entry point ships in this package."""
    return {
        "ok": False,
        "refused": True,
        "code": "KERNEL-ABSENT",
        "plain": "There is no kernel.",
    }


def boot_door() -> dict[str, Any]:
    """Userspace is not a boot. This door does not boot."""
    return {
        "ok": False,
        "refused": True,
        "code": "BOOT-ABSENT",
        "plain": "This has not booted.",
    }


def installed_door() -> dict[str, Any]:
    """This process does not install an operating system."""
    return {
        "ok": False,
        "refused": True,
        "code": "OS-NOT-INSTALLED",
        "plain": "This is not installed as an operating system.",
    }


def internet_door() -> dict[str, Any]:
    """No internet base is opened. Weather fetches stay on an injected transport."""
    return {
        "ok": False,
        "refused": True,
        "live": False,
        "installed": False,
        "code": "INTERNET-NOT-LIVE",
        "plain": "The internet base is not live and not installed.",
    }


def mail_door() -> dict[str, Any]:
    """No mail is sent. There is no public send path."""
    return {
        "ok": False,
        "refused": True,
        "sent": False,
        "code": "MAIL-SEND-REFUSED",
        "plain": "Mail is not sent from here.",
    }


def mesh_node_door(root: Path) -> dict[str, Any]:
    """Read the existing offline node. It does not become a live mesh node."""
    from azos.node import OfflineNode

    record = OfflineNode(root=root).status()
    live = record.get("mesh_enable") is True and record.get("public_bind") is True
    return {
        "ok": live,
        "refused": not live,
        "live": live,
        "code": "MESH-NODE-LIVE" if live else "MESH-NODE-NOT-LIVE",
        "plain": "This is a live mesh node." if live else "This is not a live mesh node.",
    }


def one_click_door() -> dict[str, Any]:
    """The install script is a command. This process does not run it."""
    return {
        "ok": False,
        "refused": True,
        "code": "ONE-CLICK-NOT-LIVE",
        "plain": "One-click install is not live.",
    }


def userspace_door(root: Path) -> dict[str, Any]:
    """Run one vfs write and read. That is a base, not a boot."""
    from azos.shell import Workspace

    workspace = Workspace(root / "userspace-proof")
    written = workspace.write("proof.txt", "base")
    text = workspace.cat("proof.txt")
    ok = text == "base" and written.endswith("proof.txt")
    if ok:
        plain = "The userspace base is present. That is a base, not a boot."
    else:
        plain = "The userspace base is absent."
    return {
        "ok": ok,
        "refused": not ok,
        "booted": False,
        "code": "USERSPACE-BASE" if ok else "USERSPACE-ABSENT",
        "plain": plain,
    }


def join_door(root: Path) -> dict[str, Any]:
    """Read the existing AZNews ↔ 4DMap door. Do not relabel it."""
    from azos.newsmap import ABSENT_CODE, NewsMap

    status = NewsMap(root=root).status()
    refused = (
        status.get("refused") is True
        or status.get("source_present") is not True
        or status.get("code") == ABSENT_CODE
    )
    live = status.get("live") is True and status.get("item_landed") is True and not refused
    return {
        "ok": live,
        "refused": not live,
        "live": live,
        "installed": False,
        "code": status.get("code"),
        "source_present": status.get("source_present") is True and live,
        "plain": status.get("plain"),
    }


def prove(root: Path) -> dict[str, Any]:
    """Run the doors and bind each flag to that result."""
    root = Path(root)
    doors = {
        "kernel": kernel_door(),
        "booted": boot_door(),
        "installed": installed_door(),
        "internet": internet_door(),
        "mail_send": mail_door(),
        "mesh_node_live": mesh_node_door(root),
        "one_click_install_live": one_click_door(),
        "userspace_base": userspace_door(root),
        "join_live": join_door(root),
    }
    flags = {
        "kernel": doors["kernel"]["ok"] is True,
        "booted": doors["booted"]["ok"] is True,
        "installed": doors["installed"]["ok"] is True,
        "internet": doors["internet"]["ok"] is True,
        "mail_send": doors["mail_send"]["ok"] is True,
        "mesh_node_live": doors["mesh_node_live"]["ok"] is True,
        "one_click_install_live": doors["one_click_install_live"]["ok"] is True,
        "userspace_base": doors["userspace_base"]["ok"] is True,
        "join_live": doors["join_live"]["live"] is True,
    }
    for name, flag in flags.items():
        require_flag(bool(flag), doors[name])
    if doors["userspace_base"]["booted"] is True:
        raise AssertionError("the userspace proof booted")
    return {"doors": doors, "flags": flags}


def scope_follows(proof: Mapping[str, Any]) -> None:
    """The published scope flags must be the door results."""
    flags = proof["flags"]
    if not isinstance(flags, Mapping):
        raise AssertionError("missing flags")
    pairs = (
        ("kernel", "kernel"),
        ("booted", "booted"),
        ("installed", "installed"),
        ("mail_send", "mail_send"),
        ("mesh_node_live", "mesh_node_live"),
        ("one_click_install_live", "one_click_install_live"),
        ("userspace_base", "userspace_base"),
    )
    for scope_key, flag_key in pairs:
        if SCOPE[scope_key] is not flags[flag_key]:
            raise AssertionError(f"{scope_key} does not follow its door")
        require_flag(SCOPE[scope_key] is True, proof["doors"][flag_key])
    internet = SCOPE["internet_base"]
    if not isinstance(internet, Mapping):
        raise AssertionError("internet base missing")
    if internet.get("live") is True or internet.get("installed") is True:
        require_flag(True, proof["doors"]["internet"])
    if flags["internet"] is True:
        require_flag(True, proof["doors"]["internet"])
