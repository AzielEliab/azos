"""Flags follow the door. A true flag while the path refuses fails the test."""

from __future__ import annotations

from pathlib import Path

import pytest

from azos.doors import prove, require_flag, scope_follows
from azos.ethics import scope_dict
from azos.newsmap import ABSENT_CODE, seal_join


def test_scope_flags_follow_the_doors(tmp_path: Path) -> None:
    from azos.chains import GENESIS, secondary_hash
    from azos.fourdmap import FourDMap
    from azos.news_source import FIELDS_CODE

    proof = prove(tmp_path)
    scope_follows(proof)
    scope = scope_dict()
    assert scope["kernel"] is True
    assert scope["kernel_base"] is False
    assert scope["booted"] is True
    assert scope["installed"] is True
    assert scope["os_yet"] is False
    assert scope["mail_send"] is True
    assert scope["mesh_node_live"] is True
    assert scope["one_click_install_live"] is True
    assert scope["internet_base"]["live"] is True
    assert scope["internet_base"]["installed"] is True
    assert scope["alt_internet_live"] is False
    assert scope["userspace_base"] is True
    assert proof["flags"]["userspace_base"] is True
    assert proof["doors"]["userspace_base"]["ok"] is True
    assert proof["doors"]["userspace_base"]["booted"] is False
    assert proof["doors"]["userspace_base"]["plain"] == (
        "The userspace base is present. That is a base, not a boot."
    )
    assert (tmp_path / "userspace-proof" / "proof.txt").read_text(encoding="utf-8") == "base"
    assert proof["doors"]["kernel"]["host_kernel"] is False
    assert proof["doors"]["kernel"]["code"] == "KERNEL-ENTERED"
    assert (tmp_path / ".azos" / "entry" / "receipt.json").is_file()
    assert proof["doors"]["booted"]["hardware"] is False
    assert proof["doors"]["booted"]["userspace_is_boot"] is False
    assert (tmp_path / ".azos" / "boot" / "receipt.json").is_file()
    assert proof["doors"]["installed"]["fourdmap_installed"] is False
    assert (tmp_path / "installed" / "INSTALLED").read_text(encoding="utf-8") == "Installed AZ-OS.\n"
    assert (tmp_path / "installed" / "azos" / "doors.py").is_file()
    assert proof["doors"]["one_click_install_live"]["remote_curl"] is False
    assert proof["doors"]["one_click_install_live"]["pip_ran"] is False
    assert (tmp_path / "one-click" / "INSTALLED").read_text(encoding="utf-8") == "Installed AZ-OS.\n"
    assert proof["doors"]["internet"]["status"] == 200
    assert proof["doors"]["internet"]["url"].startswith("https://")
    assert proof["doors"]["mail_send"]["public_mta"] is False
    assert proof["doors"]["mail_send"]["sent"] is True
    mail_row_secondary = proof["doors"]["mail_send"]["secondary_hash"]
    assert mail_row_secondary == secondary_hash(
        GENESIS, proof["doors"]["mail_send"]["primary_hash"], "operator"
    )
    assert proof["doors"]["mesh_node_live"]["public_bind"] is False
    assert proof["doors"]["mesh_node_live"]["host"] == "127.0.0.1"
    assert proof["flags"]["join_live"] is False
    assert proof["doors"]["join_live"]["code"] == FIELDS_CODE
    assert proof["doors"]["join_live"]["refused"] is True
    assert proof["doors"]["join_live"]["live"] is False
    assert proof["doors"]["join_live"]["source_present"] is True
    assert "score" in proof["doors"]["join_live"]["missing"]
    assert "place" in proof["doors"]["join_live"]["missing"]
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
        assert proof["doors"][name]["refused"] is False
        assert proof["flags"][name] is True


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
