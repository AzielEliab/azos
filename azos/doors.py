"""Flag proofs for the existing AZ-OS doors.

A flag is true only when that door performed its function. A refusing
door keeps its flag false. A process receipt, a loopback bind, and a
userspace file are not a host kernel. This module does not replace
those doors.

Author: Aziel Eliab.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from azos.carriers import guest_log_is_boot, guest_log_is_path, report
from azos.ethics import SCOPE, USERSPACE_YES


def require_flag(flag: bool, door: Mapping[str, Any]) -> None:
    """Fail when a flag is true while its door still refuses."""
    refused = door.get("refused") is True or door.get("ok") is not True
    if refused and flag is True:
        raise AssertionError("flag is true while the path still refuses")
    if not refused and flag is not True:
        raise AssertionError("the door performed and the flag is not true")


def kernel_door(root: Path) -> dict[str, Any]:
    """Write the process receipt. That file is not a host kernel."""
    from azos.entry import enter

    entered = enter(root)
    return {
        "ok": False,
        "refused": True,
        "code": "KERNEL-ABSENT",
        "kernel": False,
        "kernel_base": False,
        "host_kernel": False,
        "bootloader": False,
        "process_receipt": entered.get("process_receipt") is True,
        "content_hash": entered.get("content_hash"),
        "plain": "There is no kernel.",
    }


def boot_door(root: Path) -> dict[str, Any]:
    """Record that this has not booted. The userspace file is not a boot."""
    from azos.boot import boot_overlay

    booted = boot_overlay(root)
    return {
        "ok": False,
        "refused": True,
        "booted": False,
        "hardware": False,
        "userspace_is_boot": False,
        "kernel_base": False,
        "code": "BOOT-ABSENT",
        "plain": booted.get("plain") or "This has not booted.",
    }


def installed_door() -> dict[str, Any]:
    """This process does not install an operating system."""
    return {
        "ok": False,
        "refused": True,
        "fourdmap_installed": False,
        "host_os": False,
        "os_yet": False,
        "code": "OS-NOT-INSTALLED",
        "plain": "This is not installed as an operating system.",
    }


def internet_door() -> dict[str, Any]:
    """Run the carrier path. A health GET is not this door.

    The base can be present while the live flags stay false. Cap-7 and
    .aziel stay names. A same-machine frame does not flip the flags.
    """
    if guest_log_is_boot("AZOS-BOOTED") or guest_log_is_path("AZOS-BOOTED"):
        raise AssertionError("a guest log line was treated as a boot or a live path")
    found = report()
    found["installed"] = False
    found["booted"] = False
    found["kernel"] = False
    found["kernel_base"] = False
    if found.get("foreign_arrival") is not True:
        found["ok"] = False
        found["refused"] = True
        found["live"] = False
        found["packet_path_live"] = False
        found["alt_internet_live"] = False
        found["second_device"] = False
        net = found.get("internet_base")
        if isinstance(net, dict):
            net["live"] = False
            net["installed"] = False
    return found


def mail_door() -> dict[str, Any]:
    """No mail is sent. A local mailbox note is not this door."""
    return {
        "ok": False,
        "refused": True,
        "sent": False,
        "public_mta": False,
        "code": "MAIL-SEND-REFUSED",
        "plain": "Mail is not sent from here.",
    }


def mesh_node_door(root: Path) -> dict[str, Any]:
    """Read the offline node. A loopback bind is not a live mesh node."""
    from azos.node import OfflineNode

    record = OfflineNode(root=root).status()
    live = record.get("mesh_enable") is True and record.get("public_bind") is True
    return {
        "ok": live,
        "refused": not live,
        "live": live,
        "public_bind": False,
        "host_kernel": False,
        "code": "MESH-NODE-LIVE" if live else "MESH-NODE-NOT-LIVE",
        "plain": "This is a live mesh node." if live else "This is not a live mesh node.",
    }


def one_click_door() -> dict[str, Any]:
    """The install script is a command. This process does not run it."""
    return {
        "ok": False,
        "refused": True,
        "remote_curl": False,
        "pip_ran": False,
        "host_shell": False,
        "fourdmap_installed": False,
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
        plain = USERSPACE_YES
    else:
        plain = "The userspace base is absent."
    return {
        "ok": ok,
        "refused": not ok,
        "booted": False,
        "kernel": False,
        "code": "USERSPACE-BASE" if ok else "USERSPACE-ABSENT",
        "plain": plain,
    }


def join_door(root: Path) -> dict[str, Any]:
    """Read the AZNews and 4DMap door. An absent source stays not joined."""
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
        "kernel": kernel_door(root),
        "booted": boot_door(root),
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
    if doors["kernel"]["ok"] is True or flags["kernel"] is True:
        raise AssertionError("a process receipt was treated as a host kernel")
    if doors["booted"]["booted"] is True or flags["booted"] is True:
        raise AssertionError("a receipt was treated as a boot")
    if flags["mesh_node_live"] is True and doors["mesh_node_live"].get("public_bind") is not True:
        raise AssertionError("a loopback bind was treated as a live mesh node")
    internet = doors["internet"]
    if internet.get("foreign_arrival") is not True:
        for key in ("live", "packet_path_live", "alt_internet_live"):
            if internet.get(key) is True or flags.get("internet") is True:
                raise AssertionError("flag is true while the path still refuses")
        if internet.get("second_device") is True:
            raise AssertionError("a second device was marked on this machine")
    local_host = internet.get("local_host")
    remote_host = internet.get("remote_host")
    if local_host and local_host == remote_host and internet.get("second_device") is True:
        raise AssertionError("a second device was marked while both ends share one machine id")
    if internet.get("booted") is True or internet.get("kernel") is True or internet.get("installed") is True:
        raise AssertionError("the internet path booted the host")
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
    if SCOPE["kernel_base"] is not False:
        raise AssertionError("kernel base does not match the runtime")
    if SCOPE["os_yet"] is not False:
        raise AssertionError("os_yet does not match the runtime")
    internet = SCOPE["internet_base"]
    if not isinstance(internet, Mapping):
        raise AssertionError("internet base missing")
    door = proof["doors"]["internet"]
    if SCOPE["alt_internet_live"] is not (door.get("alt_internet_live") is True):
        raise AssertionError("alt internet does not follow its door")
    if SCOPE["packet_path_live"] is not (door.get("packet_path_live") is True):
        raise AssertionError("packet path does not follow its door")
    if door.get("foreign_arrival") is not True and (
        SCOPE["alt_internet_live"] is True or SCOPE["packet_path_live"] is True or internet.get("live") is True
    ):
        raise AssertionError("flag is true while the path still refuses")
    if (internet.get("live") is True) != (door.get("live") is True):
        raise AssertionError("internet live does not follow its door")
    if (internet.get("installed") is True) != (door.get("installed") is True):
        raise AssertionError("internet installed does not follow its door")
    if internet.get("base") is not True or door.get("base") is not True:
        raise AssertionError("internet base is not present")
    if internet.get("live") is True or internet.get("installed") is True:
        require_flag(True, door)
    if flags["internet"] is True:
        require_flag(True, door)
