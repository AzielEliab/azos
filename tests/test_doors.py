"""Flags follow the door. A true flag while the path refuses fails the test."""

from __future__ import annotations

from pathlib import Path

import pytest

from azos.doors import prove, require_flag, scope_follows
from azos.ethics import scope_dict
from azos.newsmap import ABSENT_CODE, seal_join


def test_scope_flags_follow_the_doors(tmp_path: Path) -> None:
    proof = prove(tmp_path)
    scope_follows(proof)
    scope = scope_dict()
    assert scope["kernel"] is False
    assert scope["booted"] is False
    assert scope["installed"] is False
    assert scope["mail_send"] is False
    assert scope["mesh_node_live"] is False
    assert scope["one_click_install_live"] is False
    assert scope["internet_base"]["live"] is False
    assert scope["internet_base"]["installed"] is False
    assert scope["userspace_base"] is True
    assert proof["flags"]["userspace_base"] is True
    assert proof["doors"]["userspace_base"]["ok"] is True
    assert proof["doors"]["userspace_base"]["booted"] is False
    assert proof["doors"]["userspace_base"]["plain"] == (
        "The userspace base is present. That is a base, not a boot."
    )
    assert (tmp_path / "userspace-proof" / "proof.txt").read_text(encoding="utf-8") == "base"
    assert proof["flags"]["join_live"] is False
    assert proof["doors"]["join_live"]["code"] == ABSENT_CODE
    assert proof["doors"]["join_live"]["refused"] is True
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
