"""Lumen keeps running after halt; revoke and purge still work."""

from __future__ import annotations

from pathlib import Path

from azos.errors import AuthorizationError, HaltedError
from azos.runtime import Runtime
from tests.conftest import passing_proposal


def test_lumen_running_after_halt(runtime: Runtime) -> None:
    result = runtime.request(passing_proposal())
    token = result.token
    assert runtime.lumen.running is True
    runtime.halt()
    assert runtime.halted is True
    assert runtime.lumen.running is True
    st = runtime.status()
    assert st["lumen"] == "running"
    assert st["halted"] is True
    # revoke still works
    runtime.lumen.revoke(token)  # type: ignore[arg-type]
    assert runtime.arc.verify(token) is False  # type: ignore[arg-type]


def test_purge_after_halt(tmp_path: Path) -> None:
    rt = Runtime(root=tmp_path)
    rt.request(passing_proposal())
    rt.halt()
    assert (tmp_path / ".azos").is_dir()
    rt.lumen.purge_session(confirm=True)
    assert not (tmp_path / ".azos").exists()
    assert rt.lumen.running is True
