"""TemporalLock × StaticClock integrity lattice.

StaticClock: every action is a gear-click that locks forward. No rollbacks.
TemporalLock: immutable timeslate lattice. Each slate is hash-chained and
bound to the current StaticClock gear-click hash.

Together they are AZ-OS session / kernel-overlay integrity. Receipts, not
truth claims. Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from azos.errors import AppendOnlyError, AuthorizationError

GENESIS_PREV = "0" * 64
AUTHOR = "Aziel Eliab"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canon(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canon(payload)).hexdigest()


@dataclass(frozen=True)
class GearClick:
    tick: int
    timestamp: str
    action: str
    prev_hash: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "timestamp": self.timestamp,
            "action": self.action,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


@dataclass(frozen=True)
class TimeSlate:
    index: int
    timestamp: str
    summary: str
    evidence: str
    gear_tick: int
    gear_hash: str
    prev_hash: str
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "evidence": self.evidence,
            "gear_tick": self.gear_tick,
            "gear_hash": self.gear_hash,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }


class _AppendOnly:
    def _refuse(self, action: str) -> None:
        raise AppendOnlyError(
            f"cannot {action}: integrity lattice is append-only; no rollbacks"
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


class StaticClock(_AppendOnly):
    """Gear-click timeline. Ticks only increase."""

    def __init__(self) -> None:
        self._clicks: tuple[GearClick, ...] = ()

    def __len__(self) -> int:
        return len(self._clicks)

    def __iter__(self) -> Iterator[GearClick]:
        return iter(self._clicks)

    def __getitem__(self, index: int) -> GearClick:
        return self._clicks[index]

    def tip(self) -> GearClick | None:
        return self._clicks[-1] if self._clicks else None

    def click(self, action: str) -> GearClick:
        prev = self._clicks[-1].hash if self._clicks else GENESIS_PREV
        tick = (self._clicks[-1].tick + 1) if self._clicks else 1
        ts = _utcnow()
        material = {
            "tick": tick,
            "timestamp": ts,
            "action": action,
            "prev_hash": prev,
        }
        item = GearClick(
            tick=tick,
            timestamp=ts,
            action=action,
            prev_hash=prev,
            hash=digest(material),
        )
        self._clicks = self._clicks + (item,)
        return item

    def verify(self) -> bool:
        prev = GENESIS_PREV
        expect = 1
        for item in self._clicks:
            if item.tick != expect or item.prev_hash != prev:
                return False
            material = {
                "tick": item.tick,
                "timestamp": item.timestamp,
                "action": item.action,
                "prev_hash": item.prev_hash,
            }
            if digest(material) != item.hash:
                return False
            prev = item.hash
            expect += 1
        return True

    def load(self, rows: list[dict[str, Any]]) -> None:
        clicks = []
        for row in rows:
            clicks.append(
                GearClick(
                    tick=int(row.get("tick") or 0),
                    timestamp=str(row.get("timestamp") or ""),
                    action=str(row.get("action") or ""),
                    prev_hash=str(row.get("prev_hash") or GENESIS_PREV),
                    hash=str(row.get("hash") or ""),
                )
            )
        self._clicks = tuple(clicks)

    def dump(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._clicks]


class TemporalLock(_AppendOnly):
    """Timeslate lattice bound to StaticClock gear hashes."""

    def __init__(self) -> None:
        self._slates: tuple[TimeSlate, ...] = ()

    def __len__(self) -> int:
        return len(self._slates)

    def __iter__(self) -> Iterator[TimeSlate]:
        return iter(self._slates)

    def __getitem__(self, index: int) -> TimeSlate:
        return self._slates[index]

    def genesis(self, *, summary: str, evidence: str, gear: GearClick) -> TimeSlate:
        if self._slates:
            raise AuthorizationError("genesis already exists; append only")
        return self._mint(summary=summary, evidence=evidence, gear=gear)

    def append(self, *, summary: str, evidence: str, gear: GearClick) -> TimeSlate:
        if not self._slates:
            return self.genesis(summary=summary, evidence=evidence, gear=gear)
        return self._mint(summary=summary, evidence=evidence, gear=gear)

    def _mint(self, *, summary: str, evidence: str, gear: GearClick) -> TimeSlate:
        prev = self._slates[-1].hash if self._slates else GENESIS_PREV
        index = (self._slates[-1].index + 1) if self._slates else 0
        ts = _utcnow()
        material = {
            "index": index,
            "timestamp": ts,
            "summary": summary,
            "evidence": evidence,
            "gear_tick": gear.tick,
            "gear_hash": gear.hash,
            "prev_hash": prev,
        }
        slate = TimeSlate(
            index=index,
            timestamp=ts,
            summary=summary,
            evidence=evidence,
            gear_tick=gear.tick,
            gear_hash=gear.hash,
            prev_hash=prev,
            hash=digest(material),
        )
        self._slates = self._slates + (slate,)
        return slate

    def verify(self, clock: StaticClock) -> bool:
        prev = GENESIS_PREV
        expect = 0
        gears = {c.tick: c.hash for c in clock}
        for slate in self._slates:
            if slate.index != expect or slate.prev_hash != prev:
                return False
            if gears.get(slate.gear_tick) != slate.gear_hash:
                return False
            material = {
                "index": slate.index,
                "timestamp": slate.timestamp,
                "summary": slate.summary,
                "evidence": slate.evidence,
                "gear_tick": slate.gear_tick,
                "gear_hash": slate.gear_hash,
                "prev_hash": slate.prev_hash,
            }
            if digest(material) != slate.hash:
                return False
            prev = slate.hash
            expect += 1
        return True

    def load(self, rows: list[dict[str, Any]]) -> None:
        slates = []
        for row in rows:
            slates.append(
                TimeSlate(
                    index=int(row.get("index") or 0),
                    timestamp=str(row.get("timestamp") or ""),
                    summary=str(row.get("summary") or ""),
                    evidence=str(row.get("evidence") or ""),
                    gear_tick=int(row.get("gear_tick") or 0),
                    gear_hash=str(row.get("gear_hash") or ""),
                    prev_hash=str(row.get("prev_hash") or GENESIS_PREV),
                    hash=str(row.get("hash") or ""),
                )
            )
        self._slates = tuple(slates)

    def dump(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._slates]


class IntegrityLattice:
    """Session integrity: StaticClock gear-clicks × TemporalLock timeslates."""

    def __init__(self, session_dir: Path | None = None) -> None:
        self.session_dir = Path(session_dir) if session_dir is not None else None
        self.clock = StaticClock()
        self.temporal = TemporalLock()
        self._load()

    def bind(self, action: str, *, summary: str, evidence: str) -> dict[str, Any]:
        """One irreversible step. Gear-click then timeslate. No rollback."""
        if self.clock and not self.clock.verify():
            raise AuthorizationError("integrity: StaticClock chain broken")
        if self.temporal and not self.temporal.verify(self.clock):
            raise AuthorizationError("integrity: TemporalLock lattice broken")
        gear = self.clock.click(action)
        if len(self.temporal) == 0:
            slate = self.temporal.genesis(summary=summary, evidence=evidence, gear=gear)
            kind = "genesis"
        else:
            slate = self.temporal.append(summary=summary, evidence=evidence, gear=gear)
            kind = "append"
        self._save()
        return {
            "ok": True,
            "kind": kind,
            "author": AUTHOR,
            "rollback": False,
            "gear": gear.to_dict(),
            "slate": slate.to_dict(),
            "verified": self.verify(),
        }

    def verify(self) -> bool:
        return self.clock.verify() and self.temporal.verify(self.clock)

    def snapshot(self) -> dict[str, Any]:
        tip = self.clock.tip()
        return {
            "kind": "temporallock_staticclock_lattice",
            "author": AUTHOR,
            "rollback": False,
            "verified": self.verify(),
            "gear_ticks": len(self.clock),
            "timeslates": len(self.temporal),
            "tip": tip.to_dict() if tip else None,
        }

    def reset(self) -> None:
        self.clock = StaticClock()
        self.temporal = TemporalLock()

    def _path(self) -> Path | None:
        if self.session_dir is None:
            return None
        return self.session_dir / "lattice.json"

    def _load(self) -> None:
        path = self._path()
        if path is None or not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict):
            return
        self.clock.load(list(data.get("gears") or []))
        self.temporal.load(list(data.get("slates") or []))

    def _save(self) -> None:
        path = self._path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "author": AUTHOR,
            "rollback": False,
            "gears": self.clock.dump(),
            "slates": self.temporal.dump(),
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
