"""Append-only sha256 hash chain of authorized executions.

Time-bound actions are final. No rewrite, pop, insert, or delete.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from azos.errors import AppendOnlyError

GENESIS_PREV = "0" * 64


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canon(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canon(payload)).hexdigest()


@dataclass(frozen=True)
class Entry:
    timestamp: str
    action: str
    token_hash: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "token_hash": self.token_hash,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


class ExecutionLog:
    """JSONL-backed chain. File is only ever opened in append mode."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else None
        self._entries: tuple[Entry, ...] = ()
        if self._path is not None and self._path.is_file():
            self._entries = tuple(self._read_file(self._path))

    @property
    def path(self) -> Path | None:
        return self._path

    def __len__(self) -> int:
        return len(self._entries)

    def __iter__(self) -> Iterator[Entry]:
        return iter(self._entries)

    def __getitem__(self, index: int) -> Entry:
        return self._entries[index]

    def _refuse(self, action: str) -> None:
        raise AppendOnlyError(
            f"cannot {action}: AZ-OS execution log is append-only; "
            "time-bound actions are final"
        )

    def pop(self, *args: object, **kwargs: object) -> None:
        self._refuse("pop")

    def insert(self, *args: object, **kwargs: object) -> None:
        self._refuse("insert")

    def remove(self, *args: object, **kwargs: object) -> None:
        self._refuse("remove")

    def clear(self) -> None:
        self._refuse("clear")

    def reverse(self) -> None:
        self._refuse("reverse")

    def __setitem__(self, *args: object, **kwargs: object) -> None:
        self._refuse("replace")

    def __delitem__(self, *args: object, **kwargs: object) -> None:
        self._refuse("delete")

    def append(
        self,
        *,
        action: str,
        token_hash: str,
        payload: dict[str, Any] | None = None,
    ) -> Entry:
        prev = self._entries[-1].hash if self._entries else GENESIS_PREV
        ts = _utcnow()
        body = payload if isinstance(payload, dict) else {}
        material = {
            "timestamp": ts,
            "action": action,
            "token_hash": token_hash,
            "payload": body,
            "prev_hash": prev,
        }
        entry = Entry(
            timestamp=ts,
            action=action,
            token_hash=token_hash,
            payload=body,
            prev_hash=prev,
            hash=digest(material),
        )
        if self._path is not None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(entry.to_dict(), sort_keys=True, separators=(",", ":"))
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.write("\n")
                fh.flush()
        self._entries = self._entries + (entry,)
        return entry

    def entries(self) -> tuple[Entry, ...]:
        return self._entries

    def reload_empty(self) -> None:
        """In-memory reset after a session purge (the file is gone)."""
        self._entries = ()

    @staticmethod
    def _read_file(path: Path) -> list[Entry]:
        out: list[Entry] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            out.append(
                Entry(
                    timestamp=str(data.get("timestamp", "")),
                    action=str(data.get("action", "")),
                    token_hash=str(data.get("token_hash", "")),
                    payload=dict(data.get("payload") or {}),
                    prev_hash=str(data.get("prev_hash", "")),
                    hash=str(data.get("hash", "")),
                )
            )
        return out
