"""Purge only touches tmp_path/.azos. Never $HOME or sibling files."""

from __future__ import annotations

from pathlib import Path

import pytest

from azos.errors import AzosError
from azos.paths import safe_purge
from azos.runtime import Runtime
from tests.conftest import passing_proposal


def test_purge_only_touches_session_dir(tmp_path: Path) -> None:
    sibling = tmp_path / "keep-me.txt"
    sibling.write_text("untouched\n", encoding="utf-8")
    other_dir = tmp_path / "other"
    other_dir.mkdir()
    (other_dir / "file").write_text("also\n", encoding="utf-8")
    home_before = set(Path.home().iterdir()) if Path.home().exists() else set()

    rt = Runtime(root=tmp_path)
    result = rt.request(passing_proposal())
    rt.run("echo", token=result.token)
    session = tmp_path / ".azos"
    assert session.is_dir()

    out = rt.purge(confirm=True)
    assert out["purged"] is True
    assert not session.exists()
    assert sibling.read_text(encoding="utf-8") == "untouched\n"
    assert (other_dir / "file").read_text(encoding="utf-8") == "also\n"
    home_after = set(Path.home().iterdir()) if Path.home().exists() else set()
    assert home_before == home_after
    assert rt.lumen.running is True


def test_purge_requires_confirm(runtime: Runtime) -> None:
    with pytest.raises(AzosError):
        runtime.purge(confirm=False)


def test_safe_purge_refuses_non_azos(tmp_path: Path) -> None:
    decoy = tmp_path / "not-session"
    decoy.mkdir()
    with pytest.raises(AzosError):
        safe_purge(decoy)
    assert decoy.is_dir()


def test_safe_purge_refuses_home() -> None:
    with pytest.raises(AzosError):
        safe_purge(Path.home())
