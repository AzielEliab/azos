"""Standalone AZNews and standalone 4DMap. The join stays a cross-tether."""

from __future__ import annotations

import json
from pathlib import Path

from azos.aznews import AZNews
from azos.fourdmap import FourDMap
from azos.newsmap import ABSENT_CODE, NewsMap
from azos.prefab import slugs


def test_standalone_paths_do_not_install_or_claim_runtime(tmp_path: Path) -> None:
    news = AZNews(root=tmp_path).status()
    pins = FourDMap(root=tmp_path).status()
    joined = NewsMap(root=tmp_path).status()
    assert news["path"] == "standalone"
    assert pins["path"] == "standalone"
    assert joined["path"] == "joined"
    assert news["live"] is False
    assert pins["installed"] is False
    assert pins["engine_installed"] is False
    assert pins["runtime_done"] is False
    assert news["runtime_done"] is False
    assert joined["runtime_done"] is False
    assert joined["cross_tether"] is True
    assert "4dmap" not in slugs()
    assert "aznews" not in slugs()
    for record in (news, pins, joined):
        assert record["not_live"] == {
            "internet": False,
            "mail": False,
            "kernel": False,
            "one_click_install": False,
            "mesh_node": False,
        }


def test_standalone_item_does_not_open_the_map(tmp_path: Path) -> None:
    news = AZNews(root=tmp_path)
    stored = news.record_item(
        username="operator",
        wording="Fixture wording kept on the news chains only.",
        image={"content_hash": "cd" * 32, "fetch_url": "https://example.invalid/a.png"},
        score=3,
        date="2026-03-03",
        event="fixture item",
        geo="fixture shelf",
    )
    assert stored["live"] is False
    assert news.lattice.verify()
    assert news.lattice.primary_chain()[-1]["document"]["wording"].startswith("Fixture")
    assert news.lattice.secondary_chain()[-1]["document"]["score"] == 3
    assert len(FourDMap(root=tmp_path).lattice) == 0
    assert NewsMap(root=tmp_path).status()["code"] == ABSENT_CODE
    assert NewsMap(root=tmp_path).status()["live"] is False


def test_outlets_are_cited_and_not_live(tmp_path: Path) -> None:
    record = AZNews(root=tmp_path).outlets()
    assert record["count"] == 50
    assert record["live"] is False
    assert "pressgazette.co.uk" in record["citation"]["article_url"]
    assert "Similarweb" in record["citation"]["measurement"]
    assert record["outlets"][0]["site"] == "bbc.com + bbc.co.uk"
    assert record["outlets"][0]["rank"] == 1
    assert all(row["live"] is False and row["fetched"] is False for row in record["outlets"])
    paid = record["paid_adapters"][0]
    assert paid["id"] == "newsapi"
    assert paid["configured"] is True
    assert paid["paid_key"] is True
    assert paid["key_present"] is False
    assert paid["live"] is False
    assert paid["fetched"] is False


def test_weather_gaps_are_chained_and_not_invented(tmp_path: Path) -> None:
    news = AZNews(root=tmp_path)
    record = news.weather(username="operator")
    assert record["adapter"] == "open-meteo"
    assert record["live"] is False
    assert record["fetched"] is False
    assert record["readings"] == 0
    assert record["gaps"] == record["regions"] == 29
    assert "unstats.un.org" in record["citation"]["url"]
    assert news.lattice.verify()
    assert len(news.lattice.primary_chain()) == 29
    assert len(news.lattice.secondary_chain()) == 29
    blob = json.dumps(news.lattice.primary_chain())
    assert "temperature" not in blob
    for row in news.lattice.secondary_chain():
        document = row["document"]
        assert document["reading"] is None
        assert document["score"] is None
        assert document["gap"] == "not-fetched"
        assert document["live"] is False


def test_weather_fetch_failure_stays_a_gap(tmp_path: Path) -> None:
    news = AZNews(root=tmp_path)

    def transport(url: str) -> tuple[int, bytes]:
        raise OSError("offline")

    record = news.fetch_weather(
        transport=transport,
        station={"region_code": "002", "latitude": 1.0, "longitude": 2.0, "point_source": "test-point"},
        username="operator",
    )
    assert record["live"] is False
    assert record["reading"] is None
    assert record["gap"] == "fetch-failed"
    document = news.lattice.rows[-1]["document"]
    assert document["reading"] is None
    assert document["kind"] == "weather_gap"
    assert "temperature_2m" not in document


def test_weather_fetch_stores_only_the_returned_reading(tmp_path: Path) -> None:
    news = AZNews(root=tmp_path)
    body = json.dumps({"current": {"temperature_2m": 18.5}, "current_units": {"temperature_2m": "°C"}}).encode()

    def transport(url: str) -> tuple[int, bytes]:
        assert "open-meteo.com" in url
        assert "latitude=9.5" in url
        return 200, body

    record = news.fetch_weather(
        transport=transport,
        station={"region_code": "009", "latitude": 9.5, "longitude": 8.0, "point_source": "test-point"},
        username="operator",
    )
    assert record["live"] is False
    assert record["complete"] is False
    assert record["reading"] == {"temperature_2m": 18.5, "unit": "°C"}
    readings = [
        row["document"]
        for row in news.lattice.rows
        if row["document"].get("kind") == "weather_reading"
    ]
    assert len(readings) == 1
    assert readings[0]["reading"]["temperature_2m"] == 18.5
    assert readings[0]["live"] is False


def test_black_swans_are_cited_scored_and_pinnable(tmp_path: Path) -> None:
    news = AZNews(root=tmp_path)
    catalog = news.black_swans()
    assert catalog["live"] is False
    assert catalog["fetched_live"] is False
    assert "ncei.noaa.gov" in catalog["citation"]["url"]
    assert catalog["count"] > 100
    milton = next(row for row in catalog["events"] if row["name"] == "Hurricane Milton")
    assert milton["score"] == 34.3
    assert milton["begin"] == "2024-10-09"
    assert milton["pinnable"] is True
    chained = news.chain_black_swans(username="operator")
    assert chained["live"] is False
    assert news.lattice.verify()
    found = [
        row
        for row in news.lattice.secondary_chain()
        if row["document"].get("id") == milton["id"]
    ]
    assert found
    assert found[0]["document"]["wording"] == milton["summary"]
    assert found[0]["document"]["score"] == 34.3
    pins = FourDMap(root=tmp_path)
    pin = pins.pin_catalog(milton["id"], username="operator")
    assert pin["installed"] is False
    assert pin["engine_installed"] is False
    assert pin["live"] is False
    assert pin["event"] == "Hurricane Milton"
    assert pins.lattice.verify()
    try:
        pins.pin_catalog("event-not-in-catalog", username="operator")
    except Exception as exc:  # noqa: BLE001
        assert "not in the cited catalog" in str(exc)
    else:
        raise AssertionError("an unknown tail event was accepted")
