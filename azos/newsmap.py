"""AZ-OS door to the runtime AZNews ↔ 4DMap join.

The join lives in the runtime 4DMap engine (FragGate slug ``4dmap``).
A news item can become a map pin (date × event × geo), or a pin can
open the matching news. This module points at that door. It is not a
second app, not a copy of the engine, and not an installed prefab.

No news source ships here. ``azos.news_source`` is absent. Absent source
stays refused, and the refusal names that code. A test may inject a
transport and a clearly labeled fixture to prove the door calls the
runtime join. That fixture is not live news.

Receipts this module writes use two offline hash-chain lattices.
The secondary hash binds that user's primary hash plus their username,
so the same document cannot be stored twice for the same name.
Neither lattice is marked live.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from azos.errors import AzosError
from azos.node import L0_DOOR
from azos.paths import session_dir

AUTHOR = "Aziel Eliab"
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
DOUBLE_CODE = "NEWS-DOC-DOUBLED"
GENESIS = "0" * 64

PLAIN_STATUS = (
    "News and the map use one runtime join. A news item can become a map pin "
    "(date, event, and place), or a pin can open the matching news. That join "
    "is the runtime 4DMap engine on the FragGate door. AZ-OS does not install "
    "4DMap and does not keep a second map. The news source aznews is absent. "
    "The missing code is azos.news_source. Nothing here is live or merged."
)

_USER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_FORBIDDEN = ("legal name", "home address", "15:20")

Transport = Callable[[str, dict[str, Any]], dict[str, Any]]


def _canon(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def content_hash(document: dict[str, Any]) -> str:
    return _sha_bytes(_canon(document))


def primary_hash(prev_primary: str, document_hash: str) -> str:
    return _sha_bytes(f"{prev_primary}\n{document_hash}".encode("utf-8"))


def secondary_hash(prev_secondary: str, user_primary: str, username: str) -> str:
    """Chain the offline secondary lattice.

    The binding for this user is their primary hash plus their username.
    That binding is chained to the previous secondary hash.
    """
    bound = _sha_bytes(f"{user_primary}\n{username}".encode("utf-8"))
    return _sha_bytes(f"{prev_secondary}\n{bound}".encode("utf-8"))


def _clean_username(username: str | None) -> str:
    name = str(username or "").strip()
    if not name or not _USER_RE.match(name):
        raise AzosError("The name on this record must be 1–80 letters, digits, spaces, dots, or hyphens.")
    low = name.lower()
    for phrase in _FORBIDDEN:
        if phrase in low:
            raise AzosError("That name is refused.")
    return name


def _scan_text(value: str, label: str) -> str:
    text = str(value or "").strip()
    low = text.lower()
    for phrase in _FORBIDDEN:
        if phrase in low:
            raise AzosError(f"{label} is refused.")
    return text


class DualLattice:
    """Offline primary and secondary hash chains. Not a live lattice."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows: list[dict[str, Any]] = []
        self._load()

    def __len__(self) -> int:
        return len(self.rows)

    def verify(self) -> bool:
        prev_primary = GENESIS
        prev_secondary = GENESIS
        seen: set[tuple[str, str]] = set()
        for row in self.rows:
            if row.get("live") is True:
                return False
            key = (str(row.get("content_hash") or ""), str(row.get("username") or ""))
            if key in seen or not key[0] or not key[1]:
                return False
            seen.add(key)
            document = row.get("document")
            if not isinstance(document, dict):
                return False
            if content_hash(document) != row.get("content_hash"):
                return False
            if row.get("prev_primary") != prev_primary:
                return False
            if primary_hash(prev_primary, str(row["content_hash"])) != row.get("primary_hash"):
                return False
            if row.get("prev_secondary") != prev_secondary:
                return False
            if (
                secondary_hash(prev_secondary, str(row["primary_hash"]), str(row["username"]))
                != row.get("secondary_hash")
            ):
                return False
            prev_primary = str(row["primary_hash"])
            prev_secondary = str(row["secondary_hash"])
        return True

    def find(self, document_hash: str, username: str) -> dict[str, Any] | None:
        for row in self.rows:
            if row.get("content_hash") == document_hash and row.get("username") == username:
                return row
        return None

    def append(self, document: dict[str, Any], username: str) -> dict[str, Any]:
        name = _clean_username(username)
        digest = content_hash(document)
        existing = self.find(digest, name)
        if existing is not None:
            raise AzosError(DOUBLE_CODE)
        prev_primary = str(self.rows[-1]["primary_hash"]) if self.rows else GENESIS
        prev_secondary = str(self.rows[-1]["secondary_hash"]) if self.rows else GENESIS
        primary = primary_hash(prev_primary, digest)
        secondary = secondary_hash(prev_secondary, primary, name)
        row = {
            "username": name,
            "content_hash": digest,
            "prev_primary": prev_primary,
            "primary_hash": primary,
            "prev_secondary": prev_secondary,
            "secondary_hash": secondary,
            "document": document,
            "live": False,
            "offline": True,
            "author": AUTHOR,
        }
        self.rows.append(row)
        self._save()
        return row

    def snapshot(self) -> dict[str, Any]:
        tip = self.rows[-1] if self.rows else None
        return {
            "kind": "primary_secondary_hash_chain",
            "author": AUTHOR,
            "live": False,
            "offline": True,
            "verified": self.verify(),
            "rows": len(self.rows),
            "primary_tip": None if tip is None else tip["primary_hash"],
            "secondary_tip": None if tip is None else tip["secondary_hash"],
            "secondary_binds": "primary_hash + username",
        }

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        rows = data.get("rows") if isinstance(data, dict) else None
        if isinstance(rows, list):
            self.rows = [row for row in rows if isinstance(row, dict)]

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "author": AUTHOR,
            "kind": "primary_secondary_hash_chain",
            "live": False,
            "offline": True,
            "secondary_binds": "primary_hash + username",
            "rows": self.rows,
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


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
        "The missing source is aznews. The missing code is azos.news_source. "
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
    """Pointer at the runtime join. Writes no articles."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self.lattice = DualLattice(session_dir(self.root) / "newsmap" / "lattice.json")

    def status(self) -> dict[str, Any]:
        lattice = self.lattice.snapshot()
        return {
            "ok": False,
            "refused": True,
            "code": ABSENT_CODE,
            "absent": ABSENT_MODULE,
            "source": SOURCE,
            "source_present": False,
            "join": JOIN,
            "engine_slug": ENGINE_SLUG,
            "engine_name": ENGINE_NAME,
            "engine_copy": False,
            "second_app": False,
            "installed": False,
            "engine_installed": False,
            "merged": False,
            "live": False,
            "lattice_live": False,
            "door": L0_DOOR,
            "pin_op": PIN_OP,
            "open_op": OPEN_OP,
            "pin_direction": PIN_DIRECTION,
            "open_direction": OPEN_DIRECTION,
            "author": AUTHOR,
            "plain": PLAIN_STATUS,
            "lattice": lattice,
        }

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
        name = _clean_username(username)
        if not fixture:
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
            "engine_copy": False,
            "author": AUTHOR,
            "door": L0_DOOR,
        }
        return self._store(document, username, plain_for=action, fixture=False)

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
        item_date = _scan_text(date or "", "date")
        item_event = _scan_text(event or "", "event")
        item_geo = _scan_text(geo or "", "place")
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
            "fixture_label": FIXTURE_LABEL,
            "engine_copy": False,
            "author": AUTHOR,
            "door": L0_DOOR,
            "called": True,
            "runtime_slug": str(answered.get("slug") or ENGINE_SLUG),
            "runtime_op": str(answered.get("op") or op),
        }
        stored = self._store(document, username, plain_for=action, fixture=True)
        stored["called"] = True
        stored["request"] = body
        return stored

    def _store(
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
            "code": document["code"] if not doubled else DOUBLE_CODE,
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
            "author": AUTHOR,
            "door": L0_DOOR,
            "op": document["op"],
            "direction": document["direction"],
            "username": username,
            "primary_hash": row["primary_hash"],
            "secondary_hash": row["secondary_hash"],
            "plain": plain,
            "lattice": self.lattice.snapshot(),
        }
