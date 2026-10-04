"""Flag proofs for the existing AZ-OS doors.

A flag is true only when that door performed its function. A refusing
door keeps its flag false. This module does not replace those doors.

Author: Aziel Eliab.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from azos.ethics import (
    BOOT_NO,
    BOOT_YES,
    CLICK_NO,
    CLICK_YES,
    INSTALLED_NO,
    INSTALLED_YES,
    KERNEL_NO,
    KERNEL_YES,
    MAIL_NO,
    MAIL_YES,
    MESH_NO,
    MESH_YES,
    SCOPE,
    USERSPACE_YES,
)
from azos.node import L0_HEALTH


def require_flag(flag: bool, door: Mapping[str, Any]) -> None:
    """Fail when a flag is true while its door still refuses."""
    refused = door.get("refused") is True or door.get("ok") is not True
    if refused and flag is True:
        raise AssertionError("flag is true while the path still refuses")
    if not refused and flag is not True:
        raise AssertionError("the door performed and the flag is not true")


def kernel_door(root: Path) -> dict[str, Any]:
    """Call the process entry and read the receipt back."""
    from azos.entry import enter

    entered = enter(root)
    ok = (
        entered.get("ok") is True
        and entered.get("code") == "KERNEL-ENTERED"
        and entered.get("host_kernel") is False
        and entered.get("bootloader") is False
    )
    return {
        "ok": ok,
        "refused": not ok,
        "code": entered.get("code") if ok else "KERNEL-ABSENT",
        "host_kernel": False,
        "bootloader": False,
        "content_hash": entered.get("content_hash"),
        "plain": KERNEL_YES if ok else KERNEL_NO,
    }


def boot_door(root: Path) -> dict[str, Any]:
    """Boot the overlay. The userspace proof is not this boot."""
    from azos.boot import boot_overlay

    booted = boot_overlay(root)
    ok = (
        booted.get("ok") is True
        and booted.get("booted") is True
        and booted.get("hardware") is False
        and booted.get("userspace_is_boot") is False
    )
    return {
        "ok": ok,
        "refused": not ok,
        "booted": ok,
        "hardware": False,
        "userspace_is_boot": False,
        "code": "BOOT-RAN" if ok else "BOOT-ABSENT",
        "plain": BOOT_YES if ok else BOOT_NO,
    }


def installed_door(root: Path) -> dict[str, Any]:
    """Copy this package into a directory and read the hashes back."""
    from azos.install import place

    placed = place(root / "installed")
    ok = placed.get("ok") is True and placed.get("fourdmap_installed") is False and placed.get("host_os") is False
    return {
        "ok": ok,
        "refused": not ok,
        "fourdmap_installed": False,
        "host_os": False,
        "os_yet": False,
        "files": placed.get("files"),
        "code": "INSTALLED" if ok else "OS-NOT-INSTALLED",
        "plain": INSTALLED_YES if ok else INSTALLED_NO,
    }


def internet_door() -> dict[str, Any]:
    """GET the existing FragGate health URL. Loopback does not count."""
    from azos.httpget import get_bytes

    status, body = get_bytes(L0_HEALTH, limit=4096)
    ok = status == 200 and b'"ok"' in body and L0_HEALTH.startswith("https://")
    return {
        "ok": ok,
        "refused": not ok,
        "live": ok,
        "installed": ok,
        "status": status,
        "url": L0_HEALTH,
        "code": "INTERNET-LIVE" if ok else "INTERNET-NOT-LIVE",
        "plain": (
            "The internet base is live and installed."
            if ok
            else "The internet base is not live and not installed."
        ),
    }


def mail_door(root: Path) -> dict[str, Any]:
    """Send one local message and read it back. There is no public mail server."""
    from azos.mail import send_local

    sent = send_local(
        root,
        username="operator",
        recipient="operator@localhost",
        subject="Local delivery",
        body="The local mailbox read this message back.",
    )
    ok = sent.get("ok") is True and sent.get("sent") is True and sent.get("public_mta") is False
    return {
        "ok": ok,
        "refused": not ok,
        "sent": ok,
        "public_mta": False,
        "code": "MAIL-SENT" if ok else "MAIL-SEND-REFUSED",
        "primary_hash": sent.get("primary_hash"),
        "secondary_hash": sent.get("secondary_hash"),
        "plain": MAIL_YES if ok else MAIL_NO,
    }


def mesh_node_door(root: Path) -> dict[str, Any]:
    """Bind 127.0.0.1 and read the answer. A public bind does not count."""
    from azos.node import OfflineNode

    record = OfflineNode(root=root).bind_once()
    live = (
        record.get("bound") is True
        and record.get("answered") is True
        and record.get("public_bind") is False
        and record.get("host") == "127.0.0.1"
        and record.get("suite_mesh") is not True
    )
    return {
        "ok": live,
        "refused": not live,
        "live": live,
        "public_bind": False,
        "host": record.get("host"),
        "code": "MESH-NODE-LIVE" if live else "MESH-NODE-NOT-LIVE",
        "plain": MESH_YES if live else MESH_NO,
    }


def one_click_door(root: Path) -> dict[str, Any]:
    """Run the in-process install path. The remote curl command is not run."""
    from azos.install import one_click

    ran = one_click(root / "one-click")
    ok = (
        ran.get("ok") is True
        and ran.get("placed") is True
        and ran.get("remote_curl") is False
        and ran.get("pip_ran") is False
        and ran.get("host_shell") is False
    )
    return {
        "ok": ok,
        "refused": not ok,
        "remote_curl": False,
        "pip_ran": False,
        "host_shell": False,
        "fourdmap_installed": False,
        "code": "ONE-CLICK-RAN" if ok else "ONE-CLICK-NOT-LIVE",
        "plain": CLICK_YES if ok else CLICK_NO,
    }


def userspace_door(root: Path) -> dict[str, Any]:
    """Run one vfs write and read. That is a base, not a boot."""
    from azos.shell import Workspace

    workspace = Workspace(root / "userspace-proof")
    written = workspace.write("proof.txt", "base")
    text = workspace.cat("proof.txt")
    ok = text == "base" and written.endswith("proof.txt")
    if ok:
        plain = USERSPACE_YES
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
    """Read a landed join, or GET the standing feed and refuse to invent fields."""
    from azos.news_source import FIELDS_CODE
    from azos.newsmap import ABSENT_CODE, NewsMap

    status = NewsMap(root=root).status()
    landed = (
        status.get("live") is True
        and status.get("item_landed") is True
        and status.get("source_present") is True
        and status.get("refused") is not True
        and status.get("code") != ABSENT_CODE
        and status.get("installed") is not True
    )
    if landed:
        return {
            "ok": True,
            "refused": False,
            "live": True,
            "installed": False,
            "code": status.get("code"),
            "source_present": True,
            "plain": status.get("plain"),
        }
    from azos.news_source import acquire

    feed = acquire()
    if feed.get("code") == FIELDS_CODE and feed.get("fetched") is True and feed.get("source_present") is True:
        return {
            "ok": False,
            "refused": True,
            "live": False,
            "installed": False,
            "code": FIELDS_CODE,
            "source_present": True,
            "missing": feed.get("missing"),
            "image_sha256": feed.get("image_sha256"),
            "plain": feed.get("plain"),
        }
    return {
        "ok": False,
        "refused": True,
        "live": False,
        "installed": False,
        "code": ABSENT_CODE,
        "source_present": False,
        "plain": status.get("plain"),
    }


def prove(root: Path) -> dict[str, Any]:
    """Run the doors and bind each flag to that result."""
    root = Path(root)
    doors = {
        "kernel": kernel_door(root),
        "booted": boot_door(root),
        "installed": installed_door(root),
        "internet": internet_door(),
        "mail_send": mail_door(root),
        "mesh_node_live": mesh_node_door(root),
        "one_click_install_live": one_click_door(root),
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
    door = proof["doors"]["internet"]
    if (internet.get("live") is True) != (door.get("live") is True):
        raise AssertionError("internet live does not follow its door")
    if (internet.get("installed") is True) != (door.get("installed") is True):
        raise AssertionError("internet installed does not follow its door")
    if internet.get("live") is True or internet.get("installed") is True:
        require_flag(True, door)
    if flags["internet"] is True:
        require_flag(True, door)
