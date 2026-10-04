"""Standalone AZNews on AZ-OS.

AZNews can be used without 4DMap. The joined path lives in ``azos.newsmap``.
This module does not install a prefab app and does not claim the
aziel-runtime side is done. ``azos.news_source`` is the fetch door.
It has no standing feed, so this probe stays refused until a real
fetched item lands. A fixture is not that item and does not flip the
live flag.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

from azos.chains import (
    AUTHOR,
    DOUBLE_CODE,
    DualLattice,
    clean_username,
    content_hash,
    image_record,
    require_score,
    scan_text,
)
from azos.errors import AzosError
from azos.node import L0_DOOR
from azos.paths import session_dir

SOURCE = "aznews"
ABSENT_CODE = "AZNEWS-SOURCE-ABSENT"
ABSENT_MODULE = "azos.news_source"
PATH = "standalone"
RUNTIME_DONE = False
CROSS_TETHER = True
RUNTIME_NOTE = "This package does not claim the aziel-runtime side is done."
WEATHER_ADAPTER = "open-meteo"
WEATHER_DOCS = "https://open-meteo.com/en/docs"
WEATHER_ENDPOINT = "https://api.open-meteo.com/v1/forecast"
CATALOG = "noaa-ncei-billions"

NOT_LIVE = {
    "internet": False,
    "mail": False,
    "kernel": False,
    "one_click_install": False,
    "mesh_node": False,
}

PAID_ADAPTERS: tuple[dict[str, Any], ...] = (
    {
        "id": "newsapi",
        "name": "NewsAPI",
        "url": "https://newsapi.org/",
        "configured": True,
        "paid_key": True,
        "key_present": False,
        "fetched": False,
        "live": False,
        "reason": "paid-key-required",
    },
)

_DATA = Path(__file__).resolve().parent / "data"
WeatherTransport = Callable[[str], tuple[int, bytes]]


def _load(name: str) -> dict[str, Any]:
    data = json.loads((_DATA / name).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AzosError(f"{name} is not a record.")
    return data


def regions() -> list[dict[str, Any]]:
    rows = _load("m49_regions.json").get("regions")
    if not isinstance(rows, list) or not rows:
        raise AzosError("The M49 region list is missing.")
    return [row for row in rows if isinstance(row, dict)]


def _region_by_code(code: str) -> dict[str, Any] | None:
    for row in regions():
        if str(row.get("code")) == code:
            return row
    return None


def _honesty() -> dict[str, Any]:
    return {
        "path": PATH,
        "standalone": True,
        "joined_path": "aznews-4dmap",
        "source": SOURCE,
        "source_present": False,
        "absent": ABSENT_MODULE,
        "code": ABSENT_CODE,
        "installed": False,
        "engine_installed": False,
        "second_app": False,
        "engine_copy": False,
        "merged": False,
        "live": False,
        "lattice_live": False,
        "runtime_done": RUNTIME_DONE,
        "runtime_claimed": False,
        "cross_tether": CROSS_TETHER,
        "door": L0_DOOR,
        "runtime_note": RUNTIME_NOTE,
        "not_live": dict(NOT_LIVE),
        "author": AUTHOR,
    }


class AZNews:
    """Local news surface. It does not fetch a live feed by itself."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self.lattice = DualLattice(session_dir(self.root) / "aznews" / "lattice.json")

    def status(self) -> dict[str, Any]:
        record = _honesty()
        record.update(
            {
                "ok": False,
                "refused": True,
                "plain": (
                    "AZNews can stand alone, without the map. "
                    "azos.news_source is the fetch door and it has no standing feed, "
                    "so the news source is absent. "
                    "Outlets, weather, and the tail-event catalog are cited locally. "
                    "Nothing is marked live unless it was fetched, and this probe did not fetch a feed. "
                    "This package does not claim the aziel-runtime side is done. "
                    "4DMap is not installed."
                ),
                "lattice": self.lattice.snapshot(),
            }
        )
        if self._has_fetched_item():
            record["ok"] = True
            record["refused"] = False
            record["live"] = True
            record["source_present"] = True
            record["code"] = "AZNEWS-ITEM-LANDED"
            record["absent"] = None
            record["plain"] = (
                "A fetched item is on the AZNews hash chains. "
                "AZNews can stand alone. 4DMap is not installed."
            )
        return seal_news(record)

    def _has_fetched_item(self) -> bool:
        if not self.lattice.verify():
            return False
        return _has_fetched_item_rows(self.lattice.rows)

    def outlets(self) -> dict[str, Any]:
        payload = _load("outlets.json")
        rows = payload.get("outlets")
        if not isinstance(rows, list) or len(rows) != 50:
            raise AzosError("The cited outlet list must contain 50 rows.")
        outlets = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            item["fetched"] = False
            item["live"] = False
            outlets.append(item)
        if any(item.get("live") for item in outlets):
            raise AzosError("A source that was not fetched cannot be marked live.")
        record = _honesty()
        record.update(
            {
                "ok": True,
                "kind": "outlet_list",
                "count": len(outlets),
                "citation": payload.get("citation"),
                "outlets": outlets,
                "paid_adapters": [dict(row) for row in PAID_ADAPTERS],
                "plain": (
                    "Fifty news sites from the Press Gazette May 2026 ranking, measured by Similarweb. "
                    "The list is cited. No outlet was fetched, so none is live. "
                    "NewsAPI is configured and needs a paid key, so it is not live."
                ),
            }
        )
        return record

    def weather(self, *, username: str = "operator") -> dict[str, Any]:
        """Record a gap for every M49 region. Does not invent a reading."""
        name = clean_username(username)
        citation = _load("m49_regions.json").get("citation")
        documents = [_gap_document(region, gap="not-fetched") for region in regions()]
        stored = self.lattice.extend(documents, name)
        record = _honesty()
        record.update(
            {
                "ok": True,
                "kind": "weather",
                "adapter": WEATHER_ADAPTER,
                "adapter_docs": WEATHER_DOCS,
                "endpoint": WEATHER_ENDPOINT,
                "fetched": False,
                "live": False,
                "regions": len(documents),
                "gaps": len(documents),
                "readings": 0,
                "citation": citation,
                "stored": stored,
                "plain": (
                    "Weather uses the open-meteo adapter. "
                    "No reading was fetched, so every UN M49 region is a gap. "
                    "No temperature was invented. Weather is not live."
                ),
                "lattice": self.lattice.snapshot(),
            }
        )
        return record

    def fetch_weather(
        self,
        *,
        transport: WeatherTransport,
        station: dict[str, Any],
        username: str = "operator",
    ) -> dict[str, Any]:
        """Fetch one supplied point. Other regions stay gaps. Live only if every region was fetched."""
        name = clean_username(username)
        code = str(station.get("region_code") or "").strip()
        region = _region_by_code(code)
        if region is None:
            raise AzosError("The station region code is not in the UN M49 region list.")
        try:
            latitude = float(station["latitude"])
            longitude = float(station["longitude"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AzosError("A weather fetch needs a supplied latitude and longitude.") from exc
        point_source = scan_text(str(station.get("point_source") or ""), "point source")
        if not point_source:
            raise AzosError("A weather fetch needs a named point source. AZ-OS will not invent a station.")
        query = urlencode(
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m",
            }
        )
        url = f"{WEATHER_ENDPOINT}?{query}"
        reading = None
        gap = "fetch-failed"
        error = None
        try:
            status, body = transport(url)
        except Exception as exc:  # noqa: BLE001 — a failed fetch is a gap, not a reading
            status, body = None, b""
            error = type(exc).__name__
        else:
            parsed = _parse_open_meteo(status, body)
            if parsed is None:
                gap = "source-omitted-reading"
            else:
                reading = parsed
                gap = None
        if reading is None:
            document = _gap_document(region, gap=gap)
            document["error"] = error
            document["fetch_url"] = url
            document["point_source"] = point_source
        else:
            document = {
                "kind": "weather_reading",
                "region_code": region.get("code"),
                "region": region.get("name"),
                "level": region.get("level"),
                "adapter": WEATHER_ADAPTER,
                "fetched": True,
                "reading": reading,
                "score": None,
                "score_gap": "open-meteo current weather does not publish a score",
                "live": False,
                "fetch_url": url,
                "point_source": point_source,
                "latitude": latitude,
                "longitude": longitude,
                "author": AUTHOR,
            }
        try:
            self.lattice.append(document, name)
        except AzosError as exc:
            if str(exc) != DOUBLE_CODE:
                raise
        fetched_codes = {
            str(row["document"].get("region_code"))
            for row in self.lattice.rows
            if isinstance(row.get("document"), dict)
            and row["document"].get("kind") == "weather_reading"
            and row["document"].get("fetched") is True
            and row["document"].get("reading") is not None
        }
        all_codes = {str(region_row.get("code")) for region_row in regions()}
        complete = all_codes <= fetched_codes
        record = _honesty()
        record.update(
            {
                "ok": reading is not None,
                "kind": "weather",
                "adapter": WEATHER_ADAPTER,
                "fetched": reading is not None,
                "live": False,
                "complete": complete,
                "region_code": code,
                "reading": reading,
                "gap": gap,
                "regions": len(all_codes),
                "regions_fetched": len(fetched_codes),
                "plain": (
                    "The open-meteo adapter returned a reading for the supplied point."
                    if reading is not None
                    else "The open-meteo adapter did not return a reading. The gap is recorded. Weather is not live."
                ),
                "lattice": self.lattice.snapshot(),
            }
        )
        record["live"] = False
        return record

    def black_swans(self) -> dict[str, Any]:
        payload = _load("black_swans.json")
        events = [row for row in payload.get("events") or [] if isinstance(row, dict)]
        if not events:
            raise AzosError("The tail-event catalog has no cited rows.")
        record = _honesty()
        record.update(
            {
                "ok": True,
                "kind": "black_swan_catalog",
                "catalog": CATALOG,
                "citation": payload.get("citation"),
                "gaps": payload.get("gaps"),
                "count": len(events),
                "live": False,
                "fetched_live": False,
                "pinnable": True,
                "events": events,
                "plain": (
                    "Historical tail events are the NOAA NCEI billion-dollar disaster table. "
                    "Scores are that table's CPI-adjusted cost. "
                    "Events that were not in the table are not added. "
                    "The catalog is not a live feed."
                ),
            }
        )
        return record

    def chain_black_swans(self, *, username: str = "operator") -> dict[str, Any]:
        name = clean_username(username)
        events = self.black_swans()["events"]
        documents = [_swan_document(event) for event in events]
        stored = self.lattice.extend(documents, name)
        record = _honesty()
        record.update(
            {
                "ok": True,
                "kind": "black_swan_chain",
                "catalog": CATALOG,
                "count": len(documents),
                "stored": stored,
                "live": False,
                "pinnable": True,
                "plain": (
                    "The cited tail events are on both hash chains, with the catalog score. "
                    "The chain is not live."
                ),
                "lattice": self.lattice.snapshot(),
            }
        )
        return record

    def fetch_item(self, *, transport: Any, username: str = "operator") -> dict[str, Any]:
        """Store one fetched item on the standalone chains. Does not open the map."""
        from azos.news_source import fetch

        got = fetch(transport)
        if got.get("refused") or not isinstance(got.get("document"), dict):
            return self.status()
        document = dict(got["document"])
        document["path"] = PATH
        stored = self._store(document, username)
        status = self.status()
        stored["live"] = status["live"] is True
        stored["source_present"] = status["source_present"] is True
        stored["code"] = status["code"]
        stored["refused"] = status["refused"]
        stored["installed"] = False
        stored["plain"] = status["plain"]
        return seal_news(stored)

    def record_item(
        self,
        *,
        username: str,
        wording: str,
        score: Any,
        date: str,
        event: str,
        geo: str,
        image: dict[str, Any] | None = None,
        image_bytes: bytes | None = None,
        fixture: bool = True,
        path: str = PATH,
        fetched: bool = False,
        source_present: bool = False,
    ) -> dict[str, Any]:
        """Append one supplied item to both hash chains. Does not mark the probe live."""
        document = news_document(
            wording=wording,
            score=score,
            date=date,
            event=event,
            geo=geo,
            image=image,
            image_bytes=image_bytes,
            fixture=fixture,
            path=path,
            fetched=fetched,
            source_present=source_present,
        )
        return self._store(document, username)

    def store_document(self, document: dict[str, Any], username: str) -> dict[str, Any]:
        return self._store(document, username)

    def _store(self, document: dict[str, Any], username: str) -> dict[str, Any]:
        name = clean_username(username)
        doubled = False
        try:
            row = self.lattice.append(document, name)
        except AzosError as exc:
            if str(exc) != DOUBLE_CODE:
                raise
            doubled = True
            found = self.lattice.find(content_hash(document), name)
            if found is None:
                raise
            row = found
        record = _honesty()
        record.update(
            {
                "ok": not doubled,
                "doubled": doubled,
                "code": DOUBLE_CODE if doubled else ABSENT_CODE,
                "fixture": bool(document.get("fixture")),
                "fetched": bool(document.get("fetched")),
                "username": name,
                "content_hash": row["content_hash"],
                "primary_hash": row["primary_hash"],
                "secondary_hash": row["secondary_hash"],
                "wording": document.get("wording"),
                "image": document.get("image"),
                "score": document.get("score"),
                "plain": (
                    "The item is on the primary hash chain and the secondary hash chain. "
                    "The secondary hash binds this name to the primary hash. "
                    "The global news probe is still not live."
                ),
                "lattice": self.lattice.snapshot(),
            }
        )
        record["live"] = False
        record["source_present"] = False
        return record


def news_document(
    *,
    wording: str,
    score: Any,
    date: str,
    event: str,
    geo: str,
    image: dict[str, Any] | None = None,
    image_bytes: bytes | None = None,
    fixture: bool = True,
    path: str = PATH,
    fetched: bool = False,
    source_present: bool = False,
) -> dict[str, Any]:
    text = scan_text(wording, "wording")
    if not text:
        raise AzosError("A news item needs its full wording.")
    number = require_score(score)
    item_date = scan_text(date, "date")
    item_event = scan_text(event, "event")
    item_geo = scan_text(geo, "place")
    if not item_date or not item_event or not item_geo:
        raise AzosError("A news item needs a date, an event, and a place.")
    pictured = image_record(image=image, image_bytes=image_bytes)
    return {
        "kind": "aznews_item",
        "path": path,
        "wording": text,
        "image": pictured,
        "score": number,
        "date": item_date,
        "event": item_event,
        "geo": item_geo,
        "fixture": bool(fixture),
        "fetched": bool(fetched),
        "source": SOURCE,
        "source_present": bool(source_present) and bool(fetched) and not bool(fixture),
        "live": False,
        "author": AUTHOR,
    }


def _gap_document(region: dict[str, Any], *, gap: str) -> dict[str, Any]:
    return {
        "kind": "weather_gap",
        "region_code": region.get("code"),
        "region": region.get("name"),
        "level": region.get("level"),
        "adapter": WEATHER_ADAPTER,
        "adapter_docs": WEATHER_DOCS,
        "fetched": False,
        "reading": None,
        "gap": gap,
        "score": None,
        "score_gap": "no reading to score",
        "live": False,
        "author": AUTHOR,
    }


def _parse_open_meteo(status: int | None, body: bytes) -> dict[str, Any] | None:
    if status != 200 or not body:
        return None
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    current = payload.get("current") if isinstance(payload, dict) else None
    if not isinstance(current, dict) or "temperature_2m" not in current:
        return None
    value = current.get("temperature_2m")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    units = payload.get("current_units") if isinstance(payload.get("current_units"), dict) else {}
    reading: dict[str, Any] = {"temperature_2m": value}
    unit = units.get("temperature_2m") if isinstance(units, dict) else None
    if isinstance(unit, str) and unit:
        reading["unit"] = unit
    return reading


def _swan_document(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "black_swan",
        "path": PATH,
        "id": event.get("id"),
        "name": event.get("name"),
        "wording": event.get("summary"),
        "date": event.get("begin"),
        "place": event.get("place"),
        "type": event.get("type"),
        "score": event.get("score"),
        "score_basis": event.get("score_basis"),
        "score_gap": event.get("score_gap"),
        "deaths": event.get("deaths"),
        "image": None,
        "image_gap": "catalog row has no image",
        "catalog": CATALOG,
        "pinnable": True,
        "live": False,
        "fetched_live": False,
        "author": AUTHOR,
    }


def seal_news(record: dict[str, Any]) -> dict[str, Any]:
    """AZNews stays not live while the source is absent, and it is not installed."""
    refused = record.get("refused") is True or record.get("source_present") is not True
    if refused and record.get("live") is True:
        raise AzosError("AZNews live is true while the source is absent")
    if record.get("installed") is True or record.get("engine_installed") is True:
        raise AzosError("AZNews is marked installed")
    return record


def _has_fetched_item_rows(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        document = row.get("document")
        if not isinstance(document, dict):
            continue
        if document.get("kind") != "aznews_item":
            continue
        if document.get("fixture") is True or document.get("fetched") is not True:
            continue
        if document.get("live") is True or not document.get("wording"):
            continue
        return True
    return False


def swan_by_id(event_id: str) -> dict[str, Any] | None:
    for event in _load("black_swans.json").get("events") or []:
        if isinstance(event, dict) and event.get("id") == event_id:
            return event
    return None
