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
    assert payload["runtime_done"] is False
    assert payload["not_live"]["internet"] is False
    assert payload["not_live"]["one_click_install"] is False
    assert "standalone" in out


def test_fixture_item_is_on_both_chains_without_flipping_live(tmp_path: Path) -> None:
    door = NewsMap(root=tmp_path)
    before = door.status()
    assert before["code"] == ABSENT_CODE
    assert before["live"] is False
    assert before["installed"] is False
    assert before["engine_installed"] is False
    image_hash = "ab" * 32
    wording = "Fixture wording for the joined door, with the full sentence."
    stored = door.record_fixture(
        username="operator",
        wording=wording,
        image={"content_hash": image_hash, "fetch_url": "https://example.invalid/fixture.png"},
        score=0.25,
        date="2026-01-01",
        event="fixture event",
        geo="fixture place",
    )
    assert stored["live"] is False
    assert stored["installed"] is False
    assert stored["engine_installed"] is False
    assert stored["probe_live"] is False
    assert stored["probe_code"] == ABSENT_CODE
    assert door.status()["live"] is False
    assert door.status()["source_present"] is False
    assert door.status()["engine_installed"] is False
    primary = door.lattice.primary_chain()
    secondary = door.lattice.secondary_chain()
    assert primary[-1]["document"]["wording"] == wording
    assert secondary[-1]["document"]["wording"] == wording
    assert primary[-1]["document"]["image"]["content_hash"] == image_hash
    assert secondary[-1]["document"]["image"]["content_hash"] == image_hash
    assert secondary[-1]["document"]["image"]["fetch_url"] == "https://example.invalid/fixture.png"
    assert primary[-1]["document"]["score"] == 0.25
    assert secondary[-1]["document"]["score"] == 0.25
    assert primary[-1]["live"] is False
    assert secondary[-1]["live"] is False
    assert door.lattice.verify()
    from azos.aznews import AZNews
    from azos.fourdmap import FourDMap

    news = AZNews(root=tmp_path)
    pins = FourDMap(root=tmp_path)
    assert news.lattice.verify()
    assert pins.lattice.verify()
    assert news.lattice.primary_chain()[-1]["document"]["wording"] == wording
    assert news.lattice.secondary_chain()[-1]["document"]["score"] == 0.25
    assert pins.lattice.primary_chain()[-1]["document"]["event"] == "fixture event"
    assert pins.status()["installed"] is False
    assert news.status()["live"] is False


def test_fixture_image_bytes_are_hashed_onto_both_chains(tmp_path: Path) -> None:
    import hashlib

    raw = b"\x89PNG fixture-bytes"
    door = NewsMap(root=tmp_path)
    stored = door.record_fixture(
        username="reader",
        wording="Fixture bytes stay hashed.",
        image_bytes=raw,
        score=1,
        date="2026-02-02",
        event="fixture bytes",
        geo="fixture desk",
    )
    digest = hashlib.sha256(raw).hexdigest()
    assert stored["live"] is False
    assert door.status()["live"] is False
    for chain in (door.lattice.primary_chain(), door.lattice.secondary_chain()):
        image = chain[-1]["document"]["image"]
        assert image["content_hash"] == digest
        assert image["byte_length"] == len(raw)
        assert "fixture-bytes" not in json.dumps(image)


def _fetched_transport():
    def transport() -> dict:
        return {
            "fetched": True,
            "fixture": False,
            "wording": "The basin gauge rose after the storm and stayed above the mark.",
            "score": 4,
            "date": "2026-04-04",
            "event": "basin gauge",
            "geo": "test basin",
            "image": {
                "content_hash": "ab" * 32,
                "fetch_url": "https://example.invalid/gauge.png",
            },
        }

    return transport


def test_fetched_item_joins_only_when_both_chains_and_a_pin_exist(tmp_path: Path) -> None:
    from azos.aznews import AZNews
    from azos.chains import GENESIS, primary_hash, secondary_hash
    from azos.doors import prove
    from azos.fourdmap import FourDMap

    door = NewsMap(root=tmp_path)
    stored = door.land_fetched(transport=_fetched_transport(), username="operator")
    assert stored["live"] is True
    assert stored["refused"] is False
    assert stored["installed"] is False
    assert stored["engine_installed"] is False
    assert stored["merged"] is False
    assert stored["lattice_live"] is False
    assert door.lattice.verify()
    row = door.lattice.rows[-1]
    assert row["primary_hash"] == primary_hash(GENESIS, row["content_hash"])
    assert row["secondary_hash"] == secondary_hash(GENESIS, row["primary_hash"], "operator")
    assert len(door.lattice.primary_chain()) == len(door.lattice.secondary_chain()) == 1
    for chain in (door.lattice.primary_chain(), door.lattice.secondary_chain()):
        document = chain[-1]["document"]
        assert document["wording"].startswith("The basin gauge")
        assert document["score"] == 4
        assert document["image"]["content_hash"] == "ab" * 32
        assert document["live"] is False
    status = door.status()
    assert status["live"] is True
    assert status["source_present"] is True
    assert status["item_landed"] is True
    assert status["paths"]["joined"]["live"] is True
    assert status["installed"] is False
    pins = FourDMap(root=tmp_path)
    assert pins.status()["installed"] is False
    assert pins.status()["live"] is False
    assert pins.lattice.verify()
    news = AZNews(root=tmp_path)
    assert news.status()["live"] is True
    assert news.status()["path"] == "standalone"
    assert news.lattice.verify()
    opened = door.open_news(username="reader")
    assert opened["refused"] is False
    assert opened["wording"].startswith("The basin gauge")
    proof = prove(tmp_path)
    assert proof["flags"]["join_live"] is True
    assert proof["flags"]["kernel"] is True
    assert proof["doors"]["kernel"]["host_kernel"] is False
    assert proof["flags"]["booted"] is True
    assert proof["doors"]["booted"]["hardware"] is False
    assert proof["flags"]["mail_send"] is True
    assert proof["doors"]["mail_send"]["public_mta"] is False
    assert proof["flags"]["mesh_node_live"] is True
    assert proof["doors"]["mesh_node_live"]["public_bind"] is False
    assert proof["doors"]["userspace_base"]["booted"] is False


def test_standalone_fetch_does_not_mark_the_join_live(tmp_path: Path) -> None:
    from azos.aznews import AZNews
    from azos.fourdmap import FourDMap

    news = AZNews(root=tmp_path)
    stored = news.fetch_item(transport=_fetched_transport(), username="offline-user")
    assert stored["live"] is True
    assert stored["installed"] is False
    assert news.lattice.verify()
    row = news.lattice.rows[-1]
    from azos.chains import GENESIS, secondary_hash

    assert row["secondary_hash"] == secondary_hash(GENESIS, row["primary_hash"], "offline-user")
    assert len(news.lattice.primary_chain()) == len(news.lattice.secondary_chain()) == 1
    assert NewsMap(root=tmp_path).status()["live"] is False
    assert NewsMap(root=tmp_path).status()["code"] == ABSENT_CODE
    assert len(FourDMap(root=tmp_path).lattice) == 0


def test_missing_fetch_keeps_the_refusal(tmp_path: Path) -> None:
    door = NewsMap(root=tmp_path)

    def transport() -> dict:
        return {"fetched": False}

    refused = door.land_fetched(transport=transport, username="operator")
    assert refused["refused"] is True
    assert refused["live"] is False
    assert refused["code"] == ABSENT_CODE
    assert door.status()["live"] is False
    assert door.status()["paths"]["joined"]["live"] is False


def test_http_get_of_a_complete_item_joins(tmp_path: Path) -> None:
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    import hashlib

    from azos.chains import GENESIS, secondary_hash
    from azos.fourdmap import FourDMap
    from azos.news_source import http_item

    png = b"\x89PNG\r\n\x1a\nbasin-gauge"
    document = {
        "wording": "The gauge at the test basin stayed above the mark after the storm.",
        "score": 4,
        "date": "2026-04-04",
        "event": "basin gauge",
        "geo": "test basin",
    }

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path == "/gauge.png":
                body = png
                kind = "image/png"
            elif self.path == "/item.json":
                body = json.dumps(document).encode("utf-8")
                kind = "application/json"
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args: object) -> None:
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    document["image_url"] = f"http://127.0.0.1:{port}/gauge.png"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        stored = NewsMap(root=tmp_path).land_fetched(
            transport=lambda: http_item(f"http://127.0.0.1:{port}/item.json"),
            username="operator",
        )
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
    assert stored["live"] is True
    assert stored["installed"] is False
    assert stored["engine_installed"] is False
    row = NewsMap(root=tmp_path).lattice.rows[-1]
    assert row["secondary_hash"] == secondary_hash(GENESIS, row["primary_hash"], "operator")
    assert row["document"]["image"]["content_hash"] == hashlib.sha256(png).hexdigest()
    assert row["document"]["live"] is False
    pins = FourDMap(root=tmp_path)
    assert pins.status()["installed"] is False
    assert pins.status()["live"] is False
    assert pins.lattice.verify()
