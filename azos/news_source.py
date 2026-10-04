"""Fetch door for AZNews.

This module is the fetch door. It does not ship a standing feed, an API
key, or a default network call. ``probe()`` refuses. ``fetch(transport)``
accepts one item from an injected transport. A fixture is not that item.
Nothing here is marked live by itself. The join lives in ``azos.newsmap``.

Author: Aziel Eliab.
"""

from __future__ import annotations

from typing import Any, Callable

from azos.aznews import ABSENT_CODE, ABSENT_MODULE, news_document
from azos.errors import AzosError

AUTHOR = "Aziel Eliab"
Transport = Callable[[], dict[str, Any]]


def probe() -> dict[str, Any]:
    """No standing feed. This call does not open the network."""
    return {
        "ok": False,
        "refused": True,
        "fetched": False,
        "fixture": False,
        "source_present": False,
        "standing_feed": False,
        "live": False,
        "installed": False,
        "code": ABSENT_CODE,
        "absent": ABSENT_MODULE,
        "source": "aznews",
        "document": None,
        "author": AUTHOR,
        "plain": (
            "azos.news_source is the fetch door and it has no standing feed, "
            "so the news source is absent."
        ),
    }


def fetch(transport: Transport | None) -> dict[str, Any]:
    """Return one fetched item, or the same refusal when nothing was fetched."""
    if transport is None:
        return probe()
    try:
        payload = transport()
    except Exception as exc:  # noqa: BLE001 — a failed fetch is an absent source
        refused = probe()
        refused["error"] = type(exc).__name__
        return refused
    if not isinstance(payload, dict):
        return probe()
    if payload.get("fetched") is not True or payload.get("fixture") is True:
        return probe()
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
        return probe()
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
