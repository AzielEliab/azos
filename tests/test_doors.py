"""Flags follow the door. A true flag while the path refuses fails the test."""

from __future__ import annotations

from pathlib import Path

import pytest

from azos.doors import prove, require_flag, scope_follows
from azos.ethics import plain_limits, scope_dict
from azos.newsmap import ABSENT_CODE, seal_join

HOSTED_LIMITS = (
    "There is no kernel. The kernel base is absent. This has not booted. "
    "This is not installed as an operating system. This is not an operating system yet. "
    "The userspace base is present. That is a base, not a boot. "
    "The internet base is not live and not installed. An alternative internet is not live. "
    "Mail is not sent from here. One-click install is not live. This is not a live mesh node. "
    "Existing doors stay in place. App shells are not started."
)


def test_scope_flags_follow_the_doors(tmp_path: Path) -> None:
    from azos.fourdmap import FourDMap

    proof = prove(tmp_path)
    scope_follows(proof)
    scope = scope_dict()
    assert plain_limits() == HOSTED_LIMITS
    assert scope["limits_plain"] == HOSTED_LIMITS
    assert scope["kernel"] is False
    assert scope["kernel_base"] is False
    assert scope["booted"] is False
    assert scope["installed"] is False
    assert scope["os_yet"] is False
    assert scope["mail_send"] is False
    assert scope["mesh_node_live"] is False
    assert scope["one_click_install_live"] is False
    assert scope["internet_base"]["live"] is False
    assert scope["internet_base"]["installed"] is False
    assert scope["alt_internet_live"] is False
    assert scope["userspace_base"] is True
    assert proof["flags"]["userspace_base"] is True
    assert proof["doors"]["userspace_base"]["ok"] is True
    assert proof["doors"]["userspace_base"]["booted"] is False
    assert proof["doors"]["userspace_base"]["kernel"] is False
    assert proof["doors"]["userspace_base"]["plain"] == (
        "The userspace base is present. That is a base, not a boot."
    )
    assert (tmp_path / "userspace-proof" / "proof.txt").read_text(encoding="utf-8") == "base"
    assert proof["doors"]["kernel"]["host_kernel"] is False
    assert proof["doors"]["kernel"]["kernel_base"] is False
    assert proof["doors"]["kernel"]["code"] == "KERNEL-ABSENT"
    assert proof["doors"]["kernel"]["process_receipt"] is True
    assert (tmp_path / ".azos" / "entry" / "receipt.json").is_file()
    assert proof["doors"]["booted"]["booted"] is False
    assert proof["doors"]["booted"]["hardware"] is False
    assert proof["doors"]["booted"]["userspace_is_boot"] is False
    assert proof["doors"]["booted"]["code"] == "BOOT-ABSENT"
    assert (tmp_path / ".azos" / "boot" / "receipt.json").is_file()
    assert proof["doors"]["installed"]["fourdmap_installed"] is False
    assert proof["doors"]["installed"]["code"] == "OS-NOT-INSTALLED"
    assert proof["doors"]["one_click_install_live"]["remote_curl"] is False
    assert proof["doors"]["one_click_install_live"]["pip_ran"] is False
    assert proof["doors"]["one_click_install_live"]["code"] == "ONE-CLICK-NOT-LIVE"
    assert proof["doors"]["internet"]["live"] is False
    assert proof["doors"]["internet"]["installed"] is False
    assert proof["doors"]["internet"]["code"] == "INTERNET-NOT-LIVE"
    assert proof["doors"]["mail_send"]["public_mta"] is False
    assert proof["doors"]["mail_send"]["sent"] is False
    assert proof["doors"]["mail_send"]["code"] == "MAIL-SEND-REFUSED"
    assert proof["doors"]["mesh_node_live"]["public_bind"] is False
    assert proof["doors"]["mesh_node_live"]["live"] is False
    assert proof["doors"]["mesh_node_live"]["code"] == "MESH-NODE-NOT-LIVE"
    assert proof["flags"]["join_live"] is False
    assert proof["doors"]["join_live"]["code"] == ABSENT_CODE
    assert proof["doors"]["join_live"]["refused"] is True
    assert proof["doors"]["join_live"]["live"] is False
    assert proof["doors"]["join_live"]["source_present"] is False
    assert FourDMap(root=tmp_path).status()["installed"] is False
    for name in (
        "kernel",
        "booted",
        "installed",
        "internet",
        "mail_send",
        "mesh_node_live",
        "one_click_install_live",
    ):
        assert proof["doors"][name]["refused"] is True
        assert proof["flags"][name] is False


def test_local_artifacts_do_not_become_a_host_kernel(tmp_path: Path) -> None:
    from azos.chains import GENESIS, secondary_hash
    from azos.entry import enter
    from azos.install import one_click, place
    from azos.mail import send_local
    from azos.node import OfflineNode

    receipt = enter(tmp_path / "receipt")
    assert receipt["process_receipt"] is True
    assert receipt["kernel"] is False
    assert receipt["kernel_base"] is False
    assert receipt["host_kernel"] is False
    assert receipt["code"] == "KERNEL-ABSENT"
    bound = OfflineNode(root=tmp_path / "node").bind_once()
    assert bound["answered"] is True
    assert bound["host"] == "127.0.0.1"
    assert bound["public_bind"] is False
    assert bound["live"] is False
    assert bound["kernel"] is False
    assert bound["mesh_node_live"] is False
    assert bound["code"] == "MESH-NODE-NOT-LIVE"
    copied = place(tmp_path / "copied")
    assert copied["placed"] is True
    assert copied["installed"] is False
    assert copied["os_yet"] is False
    assert copied["fourdmap_installed"] is False
    clicked = one_click(tmp_path / "clicked")
    assert clicked["placed"] is True
    assert clicked["ok"] is False
    assert clicked["installed"] is False
    assert clicked["code"] == "ONE-CLICK-NOT-LIVE"
    assert clicked["remote_curl"] is False
    mailbox = send_local(
        tmp_path / "mail",
        username="operator",
        recipient="operator@localhost",
        subject="Local note",
        body="This note stays in the local mailbox.",
    )
    assert mailbox["local_mailbox"] is True
    assert mailbox["sent"] is False
    assert mailbox["mail_send"] is False
    assert mailbox["public_mta"] is False
    assert mailbox["code"] == "MAIL-SEND-REFUSED"
    assert mailbox["secondary_hash"] == secondary_hash(GENESIS, mailbox["primary_hash"], "operator")
    proof = prove(tmp_path / "after")
    scope_follows(proof)
    for name in (
        "kernel",
        "booted",
        "installed",
        "internet",
        "mail_send",
        "mesh_node_live",
        "one_click_install_live",
    ):
        assert proof["flags"][name] is False
    assert proof["flags"]["userspace_base"] is True
    assert proof["doors"]["userspace_base"]["booted"] is False
    assert proof["flags"]["join_live"] is False


def test_true_flag_while_the_path_refuses_fails() -> None:
    with pytest.raises(AssertionError, match="still refuses"):
        require_flag(True, {"ok": False, "refused": True})


def test_join_seal_rejects_a_live_flag_while_absent() -> None:
    with pytest.raises(Exception, match="news source is absent"):
        seal_join(
            {
                "refused": True,
                "code": ABSENT_CODE,
                "source_present": False,
                "live": True,
                "installed": False,
                "engine_installed": False,
                "item_landed": False,
                "paths": {"joined": {"live": True}},
            }
        )
