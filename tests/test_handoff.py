"""PID 1 does not start the updater. A version compare does not fetch."""

from __future__ import annotations

import json
from pathlib import Path

from azos import __version__
from azos.handoff import (
    compare_version,
    design_matches_init,
    init_markers,
    kernel_swap_path,
    key_reason,
    pid1_contract,
    read_handoff,
    record_handoff,
)

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = "SENTINEL-OPERATOR-KEY-MATERIAL-9c79"


def _assert_off(record: dict) -> None:
    assert record["ok"] is False
    assert record["refused"] is True
    assert record["booted"] is False
    assert record["live"] is False
    assert record["hardware"] is False
    assert record["updater"] == "OFF"
    assert record["updater_enabled"] is False
    assert record["operator_key"] == "absent"
    assert record["key_verified"] is False
    assert record["kernel_swapped"] is False
    assert record["kexec"] is False
    assert record["userspace_started"] is False
    assert record["python_exec"] is False
    assert record["p2p_fetch"] is False
    assert record["applied"] is False
    assert record["release_named"] is False
    assert record["release_url"] is None
    assert record["code"] == "HANDOFF-ABSENT"
    assert record["version_sync"]["fetch"] is False
    assert record["version_sync"]["apply"] is False
    assert record["version_sync"]["url"] is None
    assert record["version_sync"]["updater_enabled"] is False


def test_pid1_contract_and_kernel_swap_stay_unexecuted() -> None:
    pid1 = pid1_contract()
    assert pid1["script"] == "image/init"
    assert pid1["runs_python"] is False
    assert pid1["starts_updater"] is False
    assert pid1["swaps_kernel"] is False
    assert pid1["next"] == "poweroff"
    swap = kernel_swap_path()
    assert swap["executed"] is False
    assert swap["kexec"] is False
    assert swap["kernel_swapped"] is False
    assert swap["booted"] is False
    assert swap["live"] is False
    assert swap["code"] == "KERNEL-SWAP-ABSENT"
    assert [step["done"] for step in swap["steps"]] == [False, False, False]
    init = (ROOT / "image/init").read_text(encoding="utf-8")
    assert design_matches_init(init)
    smoke = (ROOT / "scripts/boot-smoke.sh").read_text(encoding="utf-8")
    for marker in init_markers():
        assert marker in smoke
    code = [line.split("#", 1)[0] for line in init.splitlines()]
    assert not any(
        token in line
        for line in code
        for token in ("kexec", "python", "wget", "curl", "http://", "https://")
    )


def test_record_stays_off_without_a_key(tmp_path: Path) -> None:
    record = record_handoff(tmp_path)
    _assert_off(record)
    assert record["reason"] == "NO-OPERATOR-KEY"
    assert record["receipt"] is True
    assert record["content_hash"]
    assert record["version_sync"]["code"] == "VERSION-SYNC-IDLE"
    assert record["version_sync"]["local"] == __version__
    again = read_handoff(tmp_path)
    _assert_off(again)
    assert again["receipt"] is True
    assert again["content_hash"] == record["content_hash"]
    text = (tmp_path / ".azos" / "handoff" / "receipt.json").read_text(encoding="utf-8")
    assert "://" not in text
    assert "http" not in text


def test_a_claimed_key_is_not_stored_and_does_not_enable_the_updater(tmp_path: Path) -> None:
    assert key_reason(None) == "NO-OPERATOR-KEY"
    assert key_reason("   ") == "NO-OPERATOR-KEY"
    assert key_reason(SENTINEL) == "KEY-UNVERIFIED"
    record = record_handoff(tmp_path, claimed_key=SENTINEL)
    _assert_off(record)
    assert record["reason"] == "KEY-UNVERIFIED"
    assert record["receipt"] is True
    blob = json.dumps(record) + (tmp_path / ".azos" / "handoff" / "receipt.json").read_text(encoding="utf-8")
    assert SENTINEL not in blob
    assert record["updater_enabled"] is False


def test_peer_version_compare_does_not_fetch_or_apply(tmp_path: Path) -> None:
    same = compare_version("0.3.0")
    assert same["relation"] == "same"
    assert same["fetch"] is False and same["apply"] is False and same["url"] is None
    assert same["updater"] == "OFF" and same["updater_enabled"] is False
    newer = compare_version({"version": "0.4.0"})
    assert newer["relation"] == "peer-newer"
    assert newer["fetch"] is False and newer["apply"] is False and newer["code"] == "VERSION-COMPARE-ONLY"
    older = compare_version("0.2.9", local="0.3.0")
    assert older["relation"] == "local-newer" and older["apply"] is False
    record = record_handoff(tmp_path, peer="0.9.0")
    _assert_off(record)
    assert record["version_sync"]["relation"] == "peer-newer"
    assert record["version_sync"]["peer"] == "0.9.0"
    assert record["applied"] is False
    assert record["p2p_fetch"] is False


def test_a_peer_url_or_manifest_is_refused_and_not_stored(tmp_path: Path) -> None:
    url = "https://example.invalid/azos-release.json"
    for peer in (
        url,
        {"version": "0.9.0", "url": url},
        {"version": "0.9.0", "manifest": {"version_seq": 9}, "signature": "abcd"},
        {"version": url},
        {"release": "azos-9"},
        9,
    ):
        sync = compare_version(peer)
        assert sync["code"] == "VERSION-SYNC-REFUSED"
        assert sync["peer"] is None
        assert sync["fetch"] is False and sync["apply"] is False and sync["url"] is None
        assert url not in json.dumps(sync)
    record = record_handoff(tmp_path, peer={"version": "0.9.0", "url": url}, claimed_key=SENTINEL)
    _assert_off(record)
    assert record["reason"] == "KEY-UNVERIFIED"
    assert record["version_sync"]["code"] == "VERSION-SYNC-REFUSED"
    assert record["version_sync"]["peer"] is None
    text = (tmp_path / ".azos" / "handoff" / "receipt.json").read_text(encoding="utf-8")
    assert url not in text
    assert SENTINEL not in text
    assert "example.invalid" not in text


def test_altered_receipt_stays_refused(tmp_path: Path) -> None:
    written = record_handoff(tmp_path)
    assert written["receipt"] is True
    path = tmp_path / ".azos" / "handoff" / "receipt.json"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    loaded["booted"] = True
    loaded["updater_enabled"] = True
    loaded["kernel_swapped"] = True
    path.write_text(json.dumps(loaded), encoding="utf-8")
    record = read_handoff(tmp_path)
    _assert_off(record)
    assert record["receipt"] is False
    assert record["content_hash"] is None
    assert record["booted"] is False
    assert record["updater_enabled"] is False
    assert record["kernel_swapped"] is False


def test_module_does_not_invent_a_key_or_a_url() -> None:
    source = (ROOT / "azos" / "handoff.py").read_text(encoding="utf-8")
    assert "http://" not in source
    assert "https://" not in source
    assert "BEGIN PUBLIC KEY" not in source
    assert "BEGIN OPENSSH" not in source
    assert "urllib" not in source
    assert "socket" not in source
