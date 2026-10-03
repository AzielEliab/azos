"""AZ-OS points at the runtime AZNews ↔ 4DMap join. It does not install it."""

from __future__ import annotations

import json
from pathlib import Path

from azos.cli import main
from azos.newsmap import (
    ABSENT_CODE,
    ABSENT_MODULE,
    ENGINE_SLUG,
    FIXTURE_LABEL,
    JOIN,
    L0_DOOR,
    OPEN_OP,
    PIN_OP,
    NewsMap,
    secondary_hash,
)
from azos.node import L0_DOOR as NODE_DOOR
from azos.prefab import prefab_apps, slugs
from azos.runtime import Runtime


def test_prefab_does_not_install_4dmap_or_aznews() -> None:
    found = {app["slug"]: app for app in prefab_apps()}
    assert "4dmap" not in found
    assert "aznews" not in found
    assert "4dmap" not in slugs()
    assert "aznews" not in slugs()


def test_status_refuses_absent_source_and_points_at_runtime(tmp_path: Path) -> None:
    record = NewsMap(root=tmp_path).status()
    assert record["code"] == ABSENT_CODE
    assert record["absent"] == ABSENT_MODULE
    assert record["source"] == "aznews"
    assert record["source_present"] is False
    assert record["engine_slug"] == ENGINE_SLUG
    assert record["join"] == JOIN
    assert record["installed"] is False
    assert record["engine_installed"] is False
    assert record["second_app"] is False
    assert record["engine_copy"] is False
    assert record["merged"] is False
    assert record["live"] is False
    assert record["lattice_live"] is False
    assert record["door"] == NODE_DOOR == L0_DOOR
    assert record["pin_op"] == PIN_OP
    assert record["open_op"] == OPEN_OP
    assert "azos.news_source" in record["plain"]
    assert "4DMap" in record["plain"]
    assert "map pin" in record["plain"]
    assert "matching news" in record["plain"]
    assert record["lattice"]["live"] is False
    assert record["author"] == "Aziel Eliab"


def test_pin_and_open_refuse_without_calling_the_network(tmp_path: Path) -> None:
    door = NewsMap(root=tmp_path)

    def transport(url: str, body: dict) -> dict:
        raise AssertionError(f"network call {url} {body}")

    pin = door.pin(username="operator")
    opened = door.open_news(username="operator")
    assert pin["refused"] is True
    assert opened["refused"] is True
    assert pin["op"] == PIN_OP
    assert opened["op"] == OPEN_OP
    assert "azos.news_source" in pin["plain"]
    assert "azos.news_source" in opened["plain"]
    assert pin["live"] is False and opened["merged"] is False
    assert door.lattice.verify()
    assert len(door.lattice) == 2
    assert transport  # the absent path has no transport argument


def test_same_refusal_is_not_doubled(tmp_path: Path) -> None:
    door = NewsMap(root=tmp_path)
    first = door.pin(username="operator")
    second = door.pin(username="operator")
    assert first["doubled"] is False
    assert second["doubled"] is True
    assert second["code"] == "NEWS-DOC-DOUBLED"
    assert second["primary_hash"] == first["primary_hash"]
    assert second["secondary_hash"] == first["secondary_hash"]
    assert len(door.lattice) == 1
    assert door.lattice.verify()
    assert "not written again" in second["plain"]
    again = secondary_hash(
        "0" * 64,
        first["primary_hash"],
        "operator",
    )
    assert again == first["secondary_hash"]


def test_two_names_do_not_share_a_secondary_hash(tmp_path: Path) -> None:
    door = NewsMap(root=tmp_path)
    left = door.pin(username="operator")
    right = door.pin(username="reader")
    assert left["secondary_hash"] != right["secondary_hash"]
    assert left["primary_hash"] != right["primary_hash"]
    assert door.lattice.verify()
    assert len(door.lattice) == 2


def test_fixture_calls_the_runtime_join_and_is_not_live_news(tmp_path: Path) -> None:
    calls: list[tuple[str, dict]] = []

    def transport(url: str, body: dict) -> dict:
        calls.append((url, body))
        return {
            "ok": True,
            "slug": body["slug"],
            "op": body["op"],
            "live": True,
            "merged": True,
            "articles": [{"title": "invented"}],
            "article": "invented body",
        }

    door = NewsMap(root=tmp_path)
    pin = door.pin(
        username="operator",
        fixture=True,
        transport=transport,
        date="2026-01-01",
        event=FIXTURE_LABEL,
        geo="fixture-place",
    )
    opened = door.open_news(
        username="operator",
        fixture=True,
        transport=transport,
        date="2026-01-01",
        event=FIXTURE_LABEL,
        geo="fixture-place",
    )
    assert calls[0][0] == L0_DOOR
    assert calls[0][1]["slug"] == "4dmap"
    assert calls[0][1]["op"] == "news_pin"
    assert calls[0][1]["direction"] == "news_to_pin"
    assert calls[0][1]["join"] == JOIN
    assert calls[0][1]["fixture"] is True
    assert calls[0][1]["live"] is False
    assert calls[0][1]["item"]["label"] == FIXTURE_LABEL
    assert calls[1][1]["op"] == "news_open"
    assert calls[1][1]["direction"] == "pin_to_news"
    assert pin["ok"] is True
    assert pin["called"] is True
    assert pin["live"] is False and pin["merged"] is False
    assert pin["installed"] is False
    assert pin["fixture"] is True
    assert "not live news" in pin["plain"]
    assert "invented" not in pin["plain"]
    assert opened["op"] == "news_open"
    stored = json.loads((tmp_path / ".azos" / "newsmap" / "lattice.json").read_text(encoding="utf-8"))
    assert stored["live"] is False
    blob = json.dumps(stored)
    assert "invented" not in blob
    assert door.lattice.verify()


def test_runtime_status_keeps_4dmap_uninstalled(runtime: Runtime) -> None:
    news = runtime.status()["news_map"]
    assert news["installed"] is False
    assert news["engine_slug"] == "4dmap"
    assert news["source_present"] is False
    assert news["live"] is False
    assert news["merged"] is False
    assert "4dmap" not in {app["slug"] for app in runtime.status()["prefab"]["apps"]}


def test_cli_news_is_plain_language(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["news"]) == 0
    out = capsys.readouterr().out
    assert "runtime 4DMap" in out
    assert "azos.news_source" in out
    assert "{" not in out
    assert main(["news", "pin"]) == 1
    refused = capsys.readouterr().out
    assert "Refused" in refused
    assert "azos.news_source" in refused
    assert "{" not in refused
    assert main(["news", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["installed"] is False
    assert payload["live"] is False
    assert payload["merged"] is False
    assert payload["absent"] == "azos.news_source"
