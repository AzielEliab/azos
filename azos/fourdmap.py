"""Standalone 4DMap surface on AZ-OS.

A pin is a date, an event, and a place. This surface can pin a cited
tail event without a news article. It is not an installed prefab, and it
is not a copy of the runtime 4DMap engine. The runtime side is a cross-tether.
This package does not claim that side is done.

Author: Aziel Eliab.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from azos.aznews import NOT_LIVE, RUNTIME_NOTE, swan_by_id
from azos.chains import AUTHOR, DOUBLE_CODE, DualLattice, clean_username, content_hash, scan_text
from azos.errors import AzosError
from azos.node import L0_DOOR
from azos.paths import session_dir

ENGINE_SLUG = "4dmap"
ENGINE_NAME = "4DMap"
PATH = "standalone"
PIN_OP = "news_pin"
OPEN_OP = "news_open"
RUNTIME_DONE = False


def _base() -> dict[str, Any]:
    return {
        "path": PATH,
        "standalone": True,
        "joined_path": "aznews-4dmap",
        "engine_slug": ENGINE_SLUG,
        "engine_name": ENGINE_NAME,
        "engine_copy": False,
        "second_app": False,
        "installed": False,
        "engine_installed": False,
        "merged": False,
        "live": False,
        "lattice_live": False,
        "runtime_done": RUNTIME_DONE,
        "runtime_claimed": False,
        "cross_tether": True,
        "door": L0_DOOR,
        "pin_op": PIN_OP,
        "open_op": OPEN_OP,
        "runtime_note": RUNTIME_NOTE,
        "not_live": dict(NOT_LIVE),
        "author": AUTHOR,
    }


class FourDMap:
    """Local pins. The runtime engine is not marked installed."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self.lattice = DualLattice(session_dir(self.root) / "fourdmap" / "lattice.json")

    def status(self) -> dict[str, Any]:
        record = _base()
        record.update(
            {
                "ok": True,
                "refused": False,
                "source_present": False,
                "plain": (
                    "4DMap can stand alone. A pin is a date, an event, and a place. "
                    "It can pin a cited tail event without a news article. "
                    "AZ-OS does not install 4DMap and does not copy the runtime engine. "
                    "This package does not claim the aziel-runtime side is done. "
                    "Nothing here is live."
                ),
                "lattice": self.lattice.snapshot(),
            }
        )
        return record

    def pin_place(
        self,
        *,
        username: str = "operator",
        date: str,
        event: str,
        place: str,
        wording: str | None = None,
        score: Any = None,
        catalog_id: str | None = None,
        news_content_hash: str | None = None,
        image: dict[str, Any] | None = None,
        fixture: bool = False,
        path: str = PATH,
    ) -> dict[str, Any]:
        item_date = scan_text(date, "date")
        item_event = scan_text(event, "event")
        item_place = scan_text(place, "place")
        if not item_date or not item_event or not item_place:
            raise AzosError("A pin needs a date, an event, and a place.")
        document = {
            "kind": "fourdmap_pin",
            "path": path,
            "date": item_date,
            "event": item_event,
            "place": item_place,
            "wording": scan_text(wording, "wording") if wording else None,
            "wording_gap": None if wording else "no news wording on this pin",
            "score": score,
            "score_gap": None if score is not None else "no score on this pin",
            "image": image,
            "image_gap": None if image else "no image on this pin",
            "catalog_id": catalog_id,
            "news_content_hash": news_content_hash,
            "fixture": bool(fixture),
            "installed": False,
            "engine_installed": False,
            "live": False,
            "runtime_done": False,
            "engine_copy": False,
            "author": AUTHOR,
        }
        return self._store(document, username)

    def pin_catalog(self, event_id: str, *, username: str = "operator") -> dict[str, Any]:
        event = swan_by_id(event_id)
        if event is None:
            raise AzosError("That tail event is not in the cited catalog.")
        if event.get("score") is None and event.get("score_gap"):
            score = None
        else:
            score = event.get("score")
        stored = self.pin_place(
            username=username,
            date=str(event.get("begin") or ""),
            event=str(event.get("name") or ""),
            place=str(event.get("place") or ""),
            wording=str(event.get("summary") or ""),
            score=score,
            catalog_id=str(event.get("id") or event_id),
        )
        stored["pinnable"] = True
        stored["catalog"] = "noaa-ncei-billions"
        stored["live"] = False
        stored["installed"] = False
        stored["engine_installed"] = False
        return stored

    def pin_news(self, document: dict[str, Any], username: str) -> dict[str, Any]:
        """Pin a news document already stored on a news chain. Does not invent fields."""
        return self.pin_place(
            username=username,
            date=str(document.get("date") or ""),
            event=str(document.get("event") or ""),
            place=str(document.get("geo") or document.get("place") or ""),
            wording=str(document.get("wording") or ""),
            score=document.get("score"),
            image=document.get("image") if isinstance(document.get("image"), dict) else None,
            news_content_hash=content_hash(document),
            fixture=bool(document.get("fixture")),
            path=str(document.get("path") or "joined"),
        )

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
        record = _base()
        record.update(
            {
                "ok": not doubled,
                "doubled": doubled,
                "username": name,
                "content_hash": row["content_hash"],
                "primary_hash": row["primary_hash"],
                "secondary_hash": row["secondary_hash"],
                "date": document.get("date"),
                "event": document.get("event"),
                "place": document.get("place"),
                "pinnable": True,
                "plain": (
                    "The pin is on the primary hash chain and the secondary hash chain. "
                    "4DMap is not installed. This is not live."
                ),
                "lattice": self.lattice.snapshot(),
            }
        )
        record["live"] = False
        record["installed"] = False
        record["engine_installed"] = False
        return record
