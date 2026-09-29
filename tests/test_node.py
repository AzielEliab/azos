"""Offline AZnet node client. Local hash refs. Three layers. No payload host."""

from __future__ import annotations

import json
from pathlib import Path

from azos.cli import main
from azos.node import (
    GARDEN_CAP,
    L0_DOOR,
    L0_HEALTH,
    LAYERS,
    OfflineNode,
    sha256_text,
)
from azos.prefab import slugs
from azos.runtime import Runtime


def test_layers_and_honesty(tmp_path: Path) -> None:
    assert LAYERS == ("base", "stacked", "standalone")
    base = OfflineNode(root=tmp_path, layer="base").status()
    stacked = OfflineNode(root=tmp_path, layer="stacked").status()
    alone = OfflineNode(root=tmp_path, layer="standalone").status()
    for record, layer, l0 in (
        (base, "base", "not-required"),
        (stacked, "stacked", "unprobed"),
        (alone, "standalone", "not-required"),
    ):
        assert record["sidenet"] == "aznet"
        assert record["sidenet_is_aznet"] is True
        assert record["browser_surface"] == "AZ Browser"
        assert record["browser_slug"] == "azbrowser"
        assert record["browser_role"] == "browser surface for AZnet"
        assert record["browser_for"] == "aznet"
        assert record["browser_in_this_package"] is False
        assert record["browser_is_layer"] is False
        assert record["layers_additive"] is True
        assert record["products_merged"] is False
        assert record["layers"] == ["base", "stacked", "standalone"]
        assert record["layer"] == layer
        assert record["l0"] == l0
        assert record["l0_executed"] is False
        assert record["l0_replaced"] is False
        assert record["payload_host"] is False
        assert record["softwares_desk"] == "frozen"
        assert record["softwares_tab"] is False
        assert record["hosted_engine"] is False
        assert record["kernel"] is False
        assert record["public_bind"] is False
        assert record["tunnel"] is False
        assert record["vpn"] is False
        assert record["mesh_enable"] is False
        assert record["shell_session_required"] is False
        assert record["l0_door"] == L0_DOOR
    assert "azos-node" not in slugs()
    assert not (tmp_path / ".azos").exists()


def test_stamp_stores_hash_not_text(tmp_path: Path) -> None:
    node = OfflineNode(root=tmp_path, layer="standalone")
    secret = "local-only-phrase"
    rec = node.stamp(text=secret, label="note")
    assert rec["ok"] is True
    assert rec["ref"] == sha256_text(secret)
    assert rec["text_stored"] is False
    assert rec["hosted_called"] is False
    raw = (tmp_path / ".azos" / "node" / "garden.jsonl").read_text(encoding="utf-8")
    assert secret not in raw
    assert rec["ref"] in raw
    verified = node.verify(text=secret)
    assert verified["in_garden"] is True
    assert verified["match"] is True
    listed = node.garden()
    assert listed["count"] == 1
    assert listed["hosted_garden"] is False
    assert listed["refs"][0]["ref"] == rec["ref"]


def test_payload_and_mismatch_store_nothing(tmp_path: Path) -> None:
    node = OfflineNode(root=tmp_path, layer="base")
    hosted = node.stamp(text="x", fields={"payload": "body-bytes"})
    assert hosted["ok"] is False
    assert hosted["code"] == "AZOS-NODE-NO-PAYLOAD"
    assert not (tmp_path / ".azos" / "node" / "garden.jsonl").exists()
    mismatch = node.stamp(text="alpha", ref="a" * 64)
    assert mismatch["ok"] is False
    assert mismatch["code"] == "AZOS-NODE-MISMATCH"
    assert not (tmp_path / ".azos" / "node" / "garden.jsonl").exists()


def test_broken_chain_is_not_rewritten(tmp_path: Path) -> None:
    node = OfflineNode(root=tmp_path, layer="base")
    first = node.stamp(text="one")
    assert first["ok"] is True
    path = tmp_path / ".azos" / "node" / "garden.jsonl"
    before = path.read_bytes()
    path.write_bytes(before + b'{"kind":"stamp","prev_hash":"ffff"}\n')
    refused = node.stamp(text="two")
    assert refused["ok"] is False
    assert refused["code"] == "AZOS-NODE-CHAIN"
    assert path.read_bytes() == before + b'{"kind":"stamp","prev_hash":"ffff"}\n'
    status = node.status()
    assert status["garden_chain_ok"] is False


def test_garden_cap_keeps_older_refs(tmp_path: Path) -> None:
    node = OfflineNode(root=tmp_path, layer="base")
    for index in range(GARDEN_CAP):
        rec = node.stamp(ref=f"{index:064x}")
        assert rec["ok"] is True
    blocked = node.stamp(text="overflow")
    assert blocked["ok"] is False
    assert blocked["code"] == "AZOS-NODE-CAP"
    assert node.garden()["count"] == GARDEN_CAP


def test_memorial_is_append_only(tmp_path: Path) -> None:
    node = OfflineNode(root=tmp_path, layer="stacked")
    short = node.memorial(summary="short", evidence="short")
    assert short["ok"] is False
    rec = node.memorial(summary="local memorial line", evidence="operator note only")
    assert rec["ok"] is True
    assert rec["terminal"] is True
    assert rec["hosted_called"] is False
    listed = node.memorial_list()
    assert listed["count"] == 1
    assert listed["lines"][0]["summary"] == "local memorial line"


def test_probe_does_not_call_an_op(tmp_path: Path) -> None:
    seen: list[str] = []

    def transport(url: str) -> tuple[int, bytes]:
        seen.append(url)
        return 200, b'{"ok":true}'

    rec = OfflineNode(root=tmp_path, layer="stacked").probe(transport=transport)
    assert seen == [L0_HEALTH]
    assert rec["reachable"] is True
    assert rec["l0"] == "reachable"
    assert rec["l0_executed"] is False
    assert rec["op_called"] is None
    assert rec["hosted_called"] is False
    assert rec["http_status"] == 200

    def down(_url: str) -> tuple[int, bytes]:
        raise TimeoutError("no route")

    offline = OfflineNode(root=tmp_path, layer="stacked").probe(transport=down)
    assert offline["ok"] is True
    assert offline["reachable"] is False
    assert offline["l0"] == "unreachable"
    assert offline["l0_executed"] is False
    assert not (tmp_path / ".azos" / "node" / "garden.jsonl").exists()


def test_pair_fields_are_not_a_hosted_pair(tmp_path: Path) -> None:
    secret = "pair-token-value"
    rec = OfflineNode(root=tmp_path).status(pair_token=secret, pair_flag="azbrowser")
    assert rec["pair"]["peer_name"] == "AZ Browser"
    assert rec["pair"]["peer_role"] == "browser surface for AZnet"
    assert rec["pair"]["peer"] == "azbrowser"
    assert rec["pair"]["token_present"] is True
    assert rec["pair"]["local_fields_present"] is True
    assert rec["pair"]["hosted_paired"] is False
    assert rec["pair"]["local_pair_is_hosted_pair"] is False
    assert rec["pair"]["token_stored"] is False
    assert secret not in json.dumps(rec)


def test_cli_stamp_and_halt(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["node", "status", "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["sidenet"] == "aznet"
    assert status["layer"] == "base"
    assert main(["node", "stamp", "--text", "hello", "--layer", "standalone"]) == 0
    out = capsys.readouterr().out
    assert "not stored" in out
    raw = (tmp_path / ".azos" / "node" / "garden.jsonl").read_text(encoding="utf-8")
    assert "hello" not in raw
    assert main(["halt"]) == 0
    capsys.readouterr()
    assert main(["node", "stamp", "--text", "after-halt"]) == 1
    err = capsys.readouterr().err
    assert "halted" in err.lower() or "unauthorized" in err.lower()
    assert "after-halt" not in (tmp_path / ".azos" / "node" / "garden.jsonl").read_text(
        encoding="utf-8"
    )


def test_status_includes_offline_node(tmp_path: Path) -> None:
    rt = Runtime(root=tmp_path)
    rt.lumen.stop()
    status = rt.status()
    node = status["offline_node"]
    assert node["sidenet"] == "aznet"
    assert node["browser_surface"] == "AZ Browser"
    assert node["layers_additive"] is True
    assert node["layers"] == ["base", "stacked", "standalone"]
    assert node["l0_executed"] is False
    assert node["softwares_desk"] == "frozen"
    assert node["payload_host"] is False
    assert "shell" in status["builtins"]
    assert "node_stamp" not in status["builtins"]
