"""Offline primary and secondary hash chains.

A news item is appended to both chains with its wording, image, and score.
The secondary hash binds that user's primary hash plus their username, so
the same document cannot be stored twice for the same name.

Neither chain is marked live.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from azos.errors import AzosError

AUTHOR = "Aziel Eliab"
DOUBLE_CODE = "NEWS-DOC-DOUBLED"
GENESIS = "0" * 64

_USER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN = ("legal name", "home address", "15:20")


def canon(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def content_hash(document: dict[str, Any]) -> str:
    return sha_bytes(canon(document))


def primary_hash(prev_primary: str, document_hash: str) -> str:
    return sha_bytes(f"{prev_primary}\n{document_hash}".encode("utf-8"))


def secondary_hash(prev_secondary: str, user_primary: str, username: str) -> str:
    """Chain the offline secondary lattice.

    The binding for this user is their primary hash plus their username.
    That binding is chained to the previous secondary hash.
    """
    bound = sha_bytes(f"{user_primary}\n{username}".encode("utf-8"))
    return sha_bytes(f"{prev_secondary}\n{bound}".encode("utf-8"))


def clean_username(username: str | None) -> str:
    name = str(username or "").strip()
    if not name or not _USER_RE.match(name):
        raise AzosError("The name on this record must be 1–80 letters, digits, spaces, dots, or hyphens.")
    low = name.lower()
    for phrase in _FORBIDDEN:
        if phrase in low:
            raise AzosError("That name is refused.")
    return name


def scan_text(value: str, label: str) -> str:
    text = str(value or "").strip()
    low = text.lower()
    for phrase in _FORBIDDEN:
        if phrase in low:
            raise AzosError(f"{label} is refused.")
    return text


def image_record(
    *,
    image: dict[str, Any] | None = None,
    image_bytes: bytes | None = None,
) -> dict[str, Any]:
    """Store image bytes as their content hash, or a supplied hash plus fetch URL.

    Raw bytes are not kept in the chain. The hash is sha256 of those bytes.
    A hash without the bytes still needs the fetch URL the bytes would come from.
    """
    if image_bytes is not None:
        if not isinstance(image_bytes, (bytes, bytearray)):
            raise AzosError("Image bytes must be bytes.")
        raw = bytes(image_bytes)
        if not raw:
            raise AzosError("Image bytes are empty.")
        fetch_url = None
        if isinstance(image, dict) and image.get("fetch_url"):
            fetch_url = scan_text(str(image.get("fetch_url")), "image URL")
        return {
            "content_hash": sha_bytes(raw),
            "byte_length": len(raw),
            "fetch_url": fetch_url,
            "from_bytes": True,
        }
    if not isinstance(image, dict):
        raise AzosError("An image needs bytes, or the content hash of the bytes plus a fetch URL.")
    digest = str(image.get("content_hash") or "").strip().lower()
    fetch_url = scan_text(str(image.get("fetch_url") or ""), "image URL")
    if not _HEX64_RE.match(digest) or not fetch_url:
        raise AzosError("An image needs the content hash of the bytes and a fetch URL.")
    return {
        "content_hash": digest,
        "byte_length": None,
        "fetch_url": fetch_url,
        "from_bytes": False,
    }


def require_score(score: Any) -> int | float:
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise AzosError("A score must be a number supplied with the item.")
    return score


class DualLattice:
    """Offline primary and secondary hash chains. Not a live lattice."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows: list[dict[str, Any]] = []
        self._load()

    def __len__(self) -> int:
        return len(self.rows)

    def primary_chain(self) -> list[dict[str, Any]]:
        return [self._chain_row(row, "primary") for row in self.rows]

    def secondary_chain(self) -> list[dict[str, Any]]:
        return [self._chain_row(row, "secondary") for row in self.rows]

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
        primary = self.primary_chain()
        secondary = self.secondary_chain()
        if len(primary) != len(self.rows) or len(secondary) != len(self.rows):
            return False
        for row, left, right in zip(self.rows, primary, secondary):
            if left["document"] != row["document"] or right["document"] != row["document"]:
                return False
            if left["hash"] != row["primary_hash"] or right["hash"] != row["secondary_hash"]:
                return False
            if left.get("live") is True or right.get("live") is True:
                return False
        return True

    def find(self, document_hash: str, username: str) -> dict[str, Any] | None:
        for row in self.rows:
            if row.get("content_hash") == document_hash and row.get("username") == username:
                return row
        return None

    def append(self, document: dict[str, Any], username: str, *, save: bool = True) -> dict[str, Any]:
        name = clean_username(username)
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
        if save:
            self._save()
        return row

    def extend(self, documents: list[dict[str, Any]], username: str) -> dict[str, Any]:
        """Append many documents, then write both chains once.

        A document already stored for this name is counted as doubled and skipped.
        """
        added = 0
        doubled = 0
        for document in documents:
            try:
                self.append(document, username, save=False)
            except AzosError as exc:
                if str(exc) != DOUBLE_CODE:
                    raise
                doubled += 1
                continue
            added += 1
        if added:
            self._save()
        return {"added": added, "doubled": doubled, "rows": len(self.rows), "live": False}

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
            "primary_chain": len(self.primary_chain()),
            "secondary_chain": len(self.secondary_chain()),
        }

    def _chain_row(self, row: dict[str, Any], side: str) -> dict[str, Any]:
        return {
            "side": side,
            "username": row["username"],
            "content_hash": row["content_hash"],
            "hash": row["primary_hash"] if side == "primary" else row["secondary_hash"],
            "document": row["document"],
            "live": False,
            "offline": True,
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
            "primary_chain": self.primary_chain(),
            "secondary_chain": self.secondary_chain(),
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
