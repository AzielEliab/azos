"""ARC — execution authority: issue, verify, revoke.

Tokens are 32 random bytes. Only a sha256 of the raw bytes is stored.
A root or user string does not auto-grant a token.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azos.errors import AuthorizationError

_TOKEN_BYTES = 32
_HEX_LEN = _TOKEN_BYTES * 2


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_raw(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_token(token: str) -> bytes:
    """Decode an issued hex token. Malformed → AuthorizationError (deny)."""
    if not isinstance(token, str) or len(token) != _HEX_LEN:
        raise AuthorizationError("unauthorized: malformed token")
    try:
        raw = bytes.fromhex(token)
    except ValueError as exc:
        raise AuthorizationError("unauthorized: malformed token") from exc
    if len(raw) != _TOKEN_BYTES:
        raise AuthorizationError("unauthorized: malformed token")
    return raw


class ARC:
    """Issue / revoke execution tokens. Hashed at rest in .azos/tokens.json."""

    def __init__(self, session_dir: Path) -> None:
        self.session_dir = Path(session_dir)
        self._path = self.session_dir / "tokens.json"

    def issue(self, *, action: str, actor: str) -> str:
        """Create a token. Caller must have already passed the five gates.

        Returns the hex form of 32 raw bytes once. Stores only sha256.
        The ``actor`` string is recorded; it is never treated as authority.
        """
        # Explicit: a root/user label is not a credential.
        if not action:
            raise AuthorizationError("unauthorized: action required to issue")
        raw = secrets.token_bytes(_TOKEN_BYTES)
        digest = _hash_raw(raw)
        records = self._load()
        records.append(
            {
                "hash": digest,
                "action": action,
                "actor": actor,
                "issued_at": _utcnow(),
                "revoked": False,
            }
        )
        self._save(records)
        return raw.hex()

    def verify(self, token: str) -> bool:
        """True iff the token is a live (issued, not revoked) ARC token."""
        try:
            raw = parse_token(token)
        except AuthorizationError:
            return False
        digest = _hash_raw(raw)
        for rec in self._load():
            if rec.get("hash") == digest and not rec.get("revoked"):
                return True
        return False

    def revoke(self, token: str) -> None:
        raw = parse_token(token)
        digest = _hash_raw(raw)
        self._revoke_hash(digest)

    def revoke_all(self) -> int:
        records = self._load()
        n = 0
        for rec in records:
            if not rec.get("revoked"):
                rec["revoked"] = True
                rec["revoked_at"] = _utcnow()
                n += 1
        if n:
            self._save(records)
        return n

    def has_active(self) -> bool:
        return any(not rec.get("revoked") for rec in self._load())

    def active_hashes(self) -> list[str]:
        return [rec["hash"] for rec in self._load() if not rec.get("revoked")]

    def snapshot(self) -> dict[str, Any]:
        records = self._load()
        return {
            "active": sum(1 for r in records if not r.get("revoked")),
            "revoked": sum(1 for r in records if r.get("revoked")),
            "issued": len(records),
        }

    def token_hash(self, token: str) -> str:
        return _hash_raw(parse_token(token))

    def _revoke_hash(self, digest: str) -> None:
        records = self._load()
        found = False
        for rec in records:
            if rec.get("hash") == digest:
                rec["revoked"] = True
                rec["revoked_at"] = _utcnow()
                found = True
        if not found:
            raise AuthorizationError("unauthorized: unknown token")
        self._save(records)

    def _load(self) -> list[dict[str, Any]]:
        if not self._path.is_file():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        tokens = data.get("tokens") if isinstance(data, dict) else None
        return list(tokens) if isinstance(tokens, list) else []

    def _save(self, records: list[dict[str, Any]]) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        payload = {"tokens": records}
        self._path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
