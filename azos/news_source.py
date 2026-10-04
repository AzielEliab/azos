"""Fetch door for AZNews.

``probe()`` GETs the standing feed. That feed has wording, a date, and a
thumbnail. It does not include a score or a place, and this module does
not invent them, so the join stays refused. ``fetch(transport)`` accepts
one complete item. ``http_item`` reads that item with GET. A fixture is
not that item. Nothing here is marked live by itself.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
from typing import Any, Callable
from xml.etree import ElementTree

from azos.aznews import ABSENT_CODE, ABSENT_MODULE, news_document
from azos.chains import sha_bytes
from azos.errors import AzosError
from azos.httpget import get_bytes

AUTHOR = "Aziel Eliab"
FEED_URL = "https://feeds.bbci.co.uk/news/rss.xml"
FIELDS_CODE = "AZNEWS-FIELDS-MISSING"
_MEDIA = "{http://search.yahoo.com/mrss/}thumbnail"
Transport = Callable[[], dict[str, Any]]


def absent() -> dict[str, Any]:
    """The source did not answer. This call does not invent an item."""
    return {
        "ok": False,
        "refused": True,
        "fetched": False,
        "fixture": False,
        "source_present": False,
        "standing_feed": True,
        "live": False,
        "installed": False,
        "code": ABSENT_CODE,
        "absent": ABSENT_MODULE,
        "source": "aznews",
        "document": None,
        "missing": ["wording", "score", "date", "event", "place", "image"],
        "author": AUTHOR,
        "plain": (
            "azos.news_source is the fetch door. "
            "The standing feed did not answer, so the news source is absent."
        ),
    }


def probe() -> dict[str, Any]:
    """GET the standing feed. Do not store an item that is missing fields."""
    return acquire()


def acquire() -> dict[str, Any]:
    """GET the standing feed and the thumbnail. Refuse when score or place is absent."""
    status, body = get_bytes(FEED_URL, limit=1_000_000)
    if status != 200 or not body:
        return absent()
    try:
        root = ElementTree.fromstring(body)
    except ElementTree.ParseError:
        return absent()
    item = root.find("./channel/item")
    if item is None:
        return absent()
    title = (item.findtext("title") or "").strip()
    description = (item.findtext("description") or "").strip()
    published = (item.findtext("pubDate") or "").strip()
    thumb = item.find(_MEDIA)
    image_url = str(thumb.get("url") or "") if thumb is not None else ""
    image_hash = None
    if image_url.startswith("https://"):
        image_status, image_body = get_bytes(image_url, limit=2_000_000)
        if image_status == 200 and image_body:
            image_hash = sha_bytes(image_body)
    missing = ["score", "place"]
    if not title and not description:
        missing.append("wording")
    if not published:
        missing.append("date")
    if not title:
        missing.append("event")
    if not image_hash:
        missing.append("image")
    # The standing feed does not carry a score or a place. Do not fill them in.
    return {
        "ok": False,
        "refused": True,
        "fetched": True,
        "fixture": False,
        "source_present": True,
        "standing_feed": True,
        "live": False,
        "installed": False,
        "code": FIELDS_CODE,
        "absent": None,
        "source": "aznews",
        "document": None,
        "feed_url": FEED_URL,
        "image_url": image_url or None,
        "image_sha256": image_hash,
        "missing": missing,
        "author": AUTHOR,
        "plain": (
            "azos.news_source fetched the standing feed. "
            "The item has no score and no place, so it was not stored and the join is not live."
        ),
    }


def http_item(url: str) -> dict[str, Any]:
    """GET one JSON item and its image. ``fetched`` is set because the GETs returned."""
    status, body = get_bytes(url, limit=1_000_000)
    if status != 200 or not body:
        raise AzosError("The news URL did not return a document.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AzosError("The news URL did not return a document.") from exc
    if not isinstance(payload, dict):
        raise AzosError("The news URL did not return a document.")
    if payload.get("fixture") is True:
        raise AzosError("A fixture is not a fetched item.")
    image_url = str(payload.get("image_url") or "")
    image_status, image_bytes = get_bytes(image_url, limit=2_000_000)
    if image_status != 200 or not image_bytes:
        raise AzosError("The image URL did not return bytes.")
    return {
        "fetched": True,
        "fixture": False,
        "wording": payload.get("wording"),
        "score": payload.get("score"),
        "date": payload.get("date"),
        "event": payload.get("event"),
        "geo": payload.get("geo"),
        "image_bytes": image_bytes,
        "image": {"fetch_url": image_url},
    }


def fetch(transport: Transport | None) -> dict[str, Any]:
    """Return one fetched item, or the absent refusal when nothing was fetched."""
    if transport is None:
        return absent()
    try:
        payload = transport()
    except Exception as exc:  # noqa: BLE001 — a failed fetch is an absent source
        refused = absent()
        refused["error"] = type(exc).__name__
        return refused
    if not isinstance(payload, dict):
        return absent()
    if payload.get("fetched") is not True or payload.get("fixture") is True:
        return absent()
    try:
        document = news_document(
            wording=str(payload.get("wording") or ""),
            score=payload.get("score"),
            date=str(payload.get("date") or ""),
            event=str(payload.get("event") or ""),
            geo=str(payload.get("geo") or payload.get("place") or ""),
            image=payload.get("image") if isinstance(payload.get("image"), dict) else None,
            image_bytes=payload.get("image_bytes") if isinstance(payload.get("image_bytes"), (bytes, bytearray)) else None,
            fixture=False,
            fetched=True,
            source_present=True,
        )
    except AzosError:
        return absent()
    document["live"] = False
    return {
        "ok": True,
        "refused": False,
        "fetched": True,
        "fixture": False,
        "source_present": True,
        "standing_feed": False,
        "live": False,
        "installed": False,
        "code": "AZNEWS-ITEM-FETCHED",
        "absent": None,
        "source": "aznews",
        "document": document,
        "author": AUTHOR,
        "plain": "The fetch door returned one item. The item itself is not marked live.",
    }
