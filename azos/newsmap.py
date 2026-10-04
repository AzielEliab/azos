"""AZ-OS door to the runtime AZNews ↔ 4DMap join.

The join lives in the runtime 4DMap engine (FragGate slug ``4dmap``).
A news item can become a map pin (date × event × geo), or a pin can
open the matching news. AZNews and 4DMap also each have a standalone
path in this package. This module is the joined path. It is not a
second app, not a copy of the engine, and not an installed prefab.

The runtime side is a cross-tether. This package does not claim that
side is done.

``azos.news_source`` GETs a standing feed. That feed has no score and
no place, and this package does not invent them, so the stored probe
stays refused until a complete fetched item lands on a pin.
A fixture is not that item. Absent source stays refused.
A test may inject a transport and a clearly labeled fixture to prove
the door calls the runtime join. That fixture is not live news.
``land_fetched`` is the same door with a fetched item: both hash chains
and a map pin, and only then may the join be marked live.

Receipts this module writes use two offline hash-chain lattices.
The secondary hash binds that user's primary hash plus their username,
so the same document cannot be stored twice for the same name.
Neither lattice is marked live.

Author: Aziel Eliab.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from azos.aznews import NOT_LIVE
from azos.chains import (
    AUTHOR,
    DOUBLE_CODE,
    DualLattice,
    clean_username,
    content_hash,
    primary_hash,
    require_score,
    scan_text,
    secondary_hash,
)
from azos.errors import AzosError
from azos.node import L0_DOOR
from azos.paths import session_dir

ENGINE_SLUG = "4dmap"
ENGINE_NAME = "4DMap"
SOURCE = "aznews"
ABSENT_CODE = "AZNEWS-SOURCE-ABSENT"
ABSENT_MODULE = "azos.news_source"
JOIN = "aznews-4dmap"
PIN_OP = "news_pin"
OPEN_OP = "news_open"
PIN_DIRECTION = "news_to_pin"
OPEN_DIRECTION = "pin_to_news"
FIXTURE_LABEL = "fixture — not live news"
RUNTIME_DONE = False
CROSS_TETHER = True
RUNTIME_NOTE = "This package does not claim the aziel-runtime side is done."

PLAIN_STATUS = (
    "News and the map have a joined path and two standalone paths. "
    "On the joined path, a news item can become a map pin "
    "(date, event, and place), or a pin can open the matching news. "
    "AZNews can stand alone, and 4DMap can stand alone. "
    "That join is the runtime 4DMap engine on the FragGate door. "
    "This package does not claim the aziel-runtime side is done. "
    "AZ-OS does not install 4DMap and does not keep a second map. "
    "azos.news_source can GET a standing feed. That feed has no score and no place, "
    "so the news source on this stored probe is absent. "
    "The probe refuses until a complete fetched item lands. Nothing here is live or merged."
)

PLAIN_LIVE = (
    "A fetched news item has landed as a map pin, so the join is marked live. "
    "AZNews can still stand alone, and 4DMap can still stand alone. "
    "4DMap is not installed. The join is not merged. "
    "This package does not claim the aziel-runtime side is done."
)

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

Transport = Callable[[str, dict[str, Any]], dict[str, Any]]


def _refusal_plain(action: str, *, doubled: bool) -> str:
    if action == "open":
        asked = "open the matching news"
    else:
        asked = "pin a news item"
    tail = (
        "That refusal is already on the offline record for this name, so it was not written again."
        if doubled
        else "The refusal is on the offline record for this name."
    )
    return (
        f"Refused. There is no news source, so AZ-OS will not {asked} or invent one. "
        "azos.news_source did not return a complete item. "
        "The join still points at the runtime 4DMap engine: a news item can become a map pin "
        "(date, event, and place), or the map can open the matching news. "
        "4DMap is not installed here. This is not live and not merged. "
        f"{tail}"
    )


def _fixture_plain(action: str) -> str:
    if action == "open":
        asked = "open the matching news for a fixture pin"
    else:
        asked = "pin a fixture (date, event, and place)"
    return (
        f"The door called the runtime 4DMap join to {asked}. "
        "The fixture is not live news. 4DMap is not installed here. "
        "Nothing was marked live or merged."
    )


class NewsMap:
    """Joined path. The probe stays refused while the news source is absent."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self.lattice = DualLattice(session_dir(self.root) / "newsmap" / "lattice.json")

    def status(self) -> dict[str, Any]:
        lattice = self.lattice.snapshot()
        landed = self._join_ready()
        record = {
            "ok": landed,
            "refused": not landed,
            "code": "AZNEWS-ITEM-LANDED" if landed else ABSENT_CODE,
            "absent": None if landed else ABSENT_MODULE,
            "source": SOURCE,
            "source_present": landed,
            "join": JOIN,
            "path": "joined",
            "paths": {
                "joined": {"present": True, "id": JOIN, "live": False},
                "aznews_standalone": {"present": True, "live": False, "installed": False},
                "fourdmap_standalone": {
                    "present": True,
                    "installed": False,
                    "engine_installed": False,
                    "live": False,
                },
            },
            "engine_slug": ENGINE_SLUG,
            "engine_name": ENGINE_NAME,
            "engine_copy": False,
            "second_app": False,
            "installed": False,
            "engine_installed": False,
            "merged": False,
            "live": landed,
            "lattice_live": False,
            "item_landed": landed,
            "runtime_done": RUNTIME_DONE,
            "runtime_claimed": False,
            "cross_tether": CROSS_TETHER,
            "runtime_note": RUNTIME_NOTE,
            "not_live": dict(NOT_LIVE),
            "door": L0_DOOR,
            "pin_op": PIN_OP,
            "open_op": OPEN_OP,
            "pin_direction": PIN_DIRECTION,
            "open_direction": OPEN_DIRECTION,
            "author": AUTHOR,
            "plain": PLAIN_LIVE if landed else PLAIN_STATUS,
            "lattice": lattice,
        }
        if landed:
            record["paths"]["joined"]["live"] = True
        return seal_join(record)

    def _join_ready(self) -> bool:
        if not self.lattice.verify():
            return False
        item = _fetched_row(self.lattice.rows)
        if item is None:
            return False
        from azos.fourdmap import FourDMap

        pins = FourDMap(root=self.root)
        if not pins.lattice.verify():
            return False
        digest = str(item.get("content_hash") or "")
        for row in pins.lattice.rows:
            document = row.get("document")
            if isinstance(document, dict) and document.get("news_content_hash") == digest:
                return True
        return False

    def _performed(self, action: str) -> dict[str, Any]:
        if not self._join_ready():
            raise AzosError("join performed without a fetched pin")
        status = self.status()
        row = _fetched_row(self.lattice.rows)
        if row is None:
            raise AzosError("join performed without a fetched item")
        performed = dict(status)
        performed.update(
            {
                "ok": True,
                "refused": False,
                "action": action,
                "code": "AZNEWS-ITEM-LANDED",
                "source_present": True,
                "live": True,
                "merged": False,
                "installed": False,
                "engine_installed": False,
                "item_landed": True,
                "lattice_live": False,
                "fixture": False,
                "wording": row["document"].get("wording"),
                "username": row.get("username"),
                "primary_hash": row["primary_hash"],
                "secondary_hash": row["secondary_hash"],
                "content_hash": row["content_hash"],
            }
        )
        return seal_join(performed)

    def pin(
        self,
        *,
        username: str = "operator",
        fixture: bool = False,
        transport: Transport | None = None,
        date: str | None = None,
        event: str | None = None,
        geo: str | None = None,
    ) -> dict[str, Any]:
        return self._act(
            "pin",
            op=PIN_OP,
            direction=PIN_DIRECTION,
            username=username,
            fixture=fixture,
            transport=transport,
            date=date,
            event=event,
            geo=geo,
        )

    def open_news(
        self,
        *,
        username: str = "operator",
        fixture: bool = False,
        transport: Transport | None = None,
        date: str | None = None,
        event: str | None = None,
        geo: str | None = None,
    ) -> dict[str, Any]:
        return self._act(
            "open",
            op=OPEN_OP,
            direction=OPEN_DIRECTION,
            username=username,
            fixture=fixture,
            transport=transport,
            date=date,
            event=event,
            geo=geo,
        )

    def land_fetched(self, *, transport: Any, username: str = "operator") -> dict[str, Any]:
        """Pin one fetched item. A missing fetch keeps the absent refusal."""
        from azos.aznews import AZNews
        from azos.fourdmap import FourDMap
        from azos.news_source import fetch

        name = clean_username(username)
        got = fetch(transport)
        if got.get("refused") or not isinstance(got.get("document"), dict):
            return self._refuse("pin", PIN_OP, PIN_DIRECTION, name)
        document = dict(got["document"])
        document["path"] = "joined"
        document["live"] = False
        document["fixture"] = False
        document["fetched"] = True
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
        AZNews(root=self.root).store_document(document, name)
        FourDMap(root=self.root).pin_news(document, name)
        if not self.lattice.verify() or not self._join_ready():
            raise AzosError("The fetched item did not land on both hash chains and a map pin.")
        performed = self._performed("pin")
        performed["doubled"] = doubled
        performed["primary_hash"] = row["primary_hash"]
        performed["secondary_hash"] = row["secondary_hash"]
        performed["content_hash"] = row["content_hash"]
        performed["primary_chain"] = self.lattice.primary_chain()
        performed["secondary_chain"] = self.lattice.secondary_chain()
        return performed

    def record_fixture(
        self,
        *,
        username: str = "operator",
        wording: str,
        score: Any,
        date: str,
        event: str,
        geo: str,
        image: dict[str, Any] | None = None,
        image_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        """Store a labeled fixture on both chains and pin it. Does not flip live."""
        from azos.aznews import AZNews, news_document
        from azos.fourdmap import FourDMap

        name = clean_username(username)
        document = news_document(
            wording=wording,
            score=score,
            date=date,
            event=event,
            geo=geo,
            image=image,
            image_bytes=image_bytes,
            fixture=True,
            path="joined",
            fetched=False,
        )
        _require_fixture_label(document)
        stored = self._store_document(document, name, plain_for="pin", fixture=True)
        stored["plain"] = (
            "The fixture item is on the primary hash chain and the secondary hash chain, "
            "with its wording, image hash, and score. "
            "The same item is on the standalone AZNews chains, and the map has a pin. "
            "The fixture is not live news. 4DMap is not installed. "
            "The global probe was not marked live."
        )
        stored["code"] = ABSENT_CODE if not stored["doubled"] else DOUBLE_CODE
        news = AZNews(root=self.root).store_document(document, name)
        pin = FourDMap(root=self.root).pin_news(document, name)
        stored["aznews_primary_hash"] = news["primary_hash"]
        stored["aznews_secondary_hash"] = news["secondary_hash"]
        stored["map_primary_hash"] = pin["primary_hash"]
        stored["map_secondary_hash"] = pin["secondary_hash"]
        stored["live"] = False
        stored["installed"] = False
        stored["engine_installed"] = False
        stored["merged"] = False
        stored["source_present"] = False
        probe = self.status()
        stored["probe_live"] = probe["live"]
        stored["probe_code"] = probe["code"]
        stored["primary_chain"] = self.lattice.primary_chain()
        stored["secondary_chain"] = self.lattice.secondary_chain()
        return stored

    def _act(
        self,
        action: str,
        *,
        op: str,
        direction: str,
        username: str,
        fixture: bool,
        transport: Transport | None,
        date: str | None,
        event: str | None,
        geo: str | None,
    ) -> dict[str, Any]:
        name = clean_username(username)
        if not fixture:
            if self._join_ready():
                return self._performed(action)
            return self._refuse(action, op, direction, name)
        return self._fixture_call(
            action,
            op,
            direction,
            name,
            transport,
            date=date,
            event=event,
            geo=geo,
        )

    def _refuse(self, action: str, op: str, direction: str, username: str) -> dict[str, Any]:
        document = {
            "kind": "aznews_4dmap_join",
            "action": action,
            "outcome": "refused",
            "code": ABSENT_CODE,
            "absent": ABSENT_MODULE,
            "source": SOURCE,
            "source_present": False,
            "engine_slug": ENGINE_SLUG,
            "op": op,
            "join": JOIN,
            "direction": direction,
            "installed": False,
            "merged": False,
            "live": False,
            "fixture": False,
            "fetched": False,
            "engine_copy": False,
            "author": AUTHOR,
            "door": L0_DOOR,
        }
        return self._store_document(document, username, plain_for=action, fixture=False)

    def _fixture_call(
        self,
        action: str,
        op: str,
        direction: str,
        username: str,
        transport: Transport | None,
        *,
        date: str | None,
        event: str | None,
        geo: str | None,
    ) -> dict[str, Any]:
        if transport is None:
            raise AzosError(
                "A fixture door call needs an injected transport. This package does not fetch news."
            )
        item_date = scan_text(date or "", "date")
        item_event = scan_text(event or "", "event")
        item_geo = scan_text(geo or "", "place")
        if not _DATE_RE.match(item_date):
            raise AzosError("A fixture date must look like YYYY-MM-DD.")
        if "fixture" not in item_event.lower() or "fixture" not in item_geo.lower():
            raise AzosError("A fixture must be labeled fixture. It is not live news.")
        body = {
            "slug": ENGINE_SLUG,
            "op": op,
            "join": JOIN,
            "source": SOURCE,
            "direction": direction,
            "fixture": True,
            "live": False,
            "merged": False,
            "installed": False,
            "engine_copy": False,
            "author": AUTHOR,
            "item": {
                "label": FIXTURE_LABEL,
                "date": item_date,
                "event": item_event,
                "geo": item_geo,
            },
        }
        answered = transport(L0_DOOR, body)
        if not isinstance(answered, dict):
            raise AzosError("The runtime join transport must return a record.")
        document = {
            "kind": "aznews_4dmap_join",
            "action": action,
            "outcome": "fixture_called",
            "code": "AZNEWS-FIXTURE-DOOR",
            "absent": ABSENT_MODULE,
            "source": SOURCE,
            "source_present": False,
            "engine_slug": ENGINE_SLUG,
            "op": op,
            "join": JOIN,
            "direction": direction,
            "installed": False,
            "merged": False,
            "live": False,
            "fixture": True,
            "fetched": False,
            "fixture_label": FIXTURE_LABEL,
            "engine_copy": False,
            "author": AUTHOR,
            "door": L0_DOOR,
            "called": True,
            "runtime_slug": str(answered.get("slug") or ENGINE_SLUG),
            "runtime_op": str(answered.get("op") or op),
            "runtime_done": False,
        }
        stored = self._store_document(document, username, plain_for=action, fixture=True)
        stored["called"] = True
        stored["request"] = body
        return stored

    def _store_document(
        self,
        document: dict[str, Any],
        username: str,
        *,
        plain_for: str,
        fixture: bool,
    ) -> dict[str, Any]:
        doubled = False
        try:
            row = self.lattice.append(document, username)
        except AzosError as exc:
            if str(exc) != DOUBLE_CODE:
                raise
            doubled = True
            found = self.lattice.find(content_hash(document), username)
            if found is None:
                raise
            row = found
        plain = _fixture_plain(plain_for) if fixture and not doubled else _refusal_plain(plain_for, doubled=doubled)
        if fixture and doubled:
            plain = (
                _fixture_plain(plain_for)
                + " That fixture record is already stored for this name, so it was not written again."
            )
        return {
            "ok": bool(fixture and not doubled),
            "refused": not fixture,
            "doubled": doubled,
            "code": document.get("code", ABSENT_CODE) if not doubled else DOUBLE_CODE,
            "absent": ABSENT_MODULE,
            "source": SOURCE,
            "source_present": False,
            "join": JOIN,
            "engine_slug": ENGINE_SLUG,
            "engine_installed": False,
            "installed": False,
            "second_app": False,
            "engine_copy": False,
            "merged": False,
            "live": False,
            "lattice_live": False,
            "fixture": fixture,
            "runtime_done": RUNTIME_DONE,
            "author": AUTHOR,
            "door": L0_DOOR,
            "op": document.get("op"),
            "direction": document.get("direction"),
            "username": username,
            "primary_hash": row["primary_hash"],
            "secondary_hash": row["secondary_hash"],
            "content_hash": row["content_hash"],
            "plain": plain,
            "lattice": self.lattice.snapshot(),
        }


def seal_join(record: dict[str, Any]) -> dict[str, Any]:
    """A join flag cannot be true while the source is absent or 4DMap is installed."""
    paths = record.get("paths") if isinstance(record.get("paths"), dict) else {}
    joined = paths.get("joined") if isinstance(paths.get("joined"), dict) else {}
    refused = (
        record.get("refused") is True
        or record.get("source_present") is not True
        or record.get("code") == ABSENT_CODE
    )
    if refused and (record.get("live") is True or joined.get("live") is True):
        raise AzosError("join flag is true while the news source is absent")
    if record.get("live") is True and record.get("item_landed") is not True:
        raise AzosError("join flag is true without a fetched item")
    if record.get("installed") is True or record.get("engine_installed") is True:
        raise AzosError("4DMap is marked installed")
    return record


def _fetched_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
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
        return row
    return None


def _require_fixture_label(document: dict[str, Any]) -> None:
    wording = str(document.get("wording") or "").lower()
    event = str(document.get("event") or "").lower()
    geo = str(document.get("geo") or "").lower()
    if "fixture" not in wording or "fixture" not in event or "fixture" not in geo:
        raise AzosError("A fixture must be labeled fixture. It is not live news.")
    image = document.get("image")
    if not isinstance(image, dict) or not image.get("content_hash"):
        raise AzosError("A fixture item needs an image hash.")
    require_score(document.get("score"))


__all__ = [
    "ABSENT_CODE",
    "ABSENT_MODULE",
    "AUTHOR",
    "CROSS_TETHER",
    "DOUBLE_CODE",
    "ENGINE_NAME",
    "ENGINE_SLUG",
    "FIXTURE_LABEL",
    "JOIN",
    "L0_DOOR",
    "OPEN_OP",
    "PIN_OP",
    "RUNTIME_DONE",
    "DualLattice",
    "NewsMap",
    "content_hash",
    "primary_hash",
    "secondary_hash",
]
