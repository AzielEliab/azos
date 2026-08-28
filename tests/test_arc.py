"""ARC tokens: 32 bytes, hashed at rest, revoke, no auto-grant."""

from __future__ import annotations

import json

from azos.runtime import Runtime
from tests.conftest import passing_proposal


def test_token_is_32_bytes_hex_hashed_at_rest(runtime: Runtime, tmp_path) -> None:
    result = runtime.request(passing_proposal())
    token = result.token
    assert token is not None
    assert len(token) == 64
    raw = bytes.fromhex(token)
    assert len(raw) == 32
    stored = json.loads((tmp_path / ".azos" / "tokens.json").read_text())
    hashes = [t["hash"] for t in stored["tokens"]]
    assert token not in json.dumps(stored)
    assert all(len(h) == 64 for h in hashes)
    assert runtime.arc.verify(token) is True


def test_has_active_after_issue_and_not_after_revoke(runtime: Runtime) -> None:
    assert runtime.arc.has_active() is False
    result = runtime.request(passing_proposal())
    assert runtime.arc.has_active() is True
    runtime.arc.revoke(result.token)  # type: ignore[arg-type]
    assert runtime.arc.has_active() is False
