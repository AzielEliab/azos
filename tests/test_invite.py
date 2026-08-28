"""Invite prints; does not write files outside cwd; not infection."""

from __future__ import annotations

import io
from pathlib import Path

from azos.cli import main
from azos.invite import DOWNLOAD_URL, emit_invite, invite_text


def test_invite_text_has_principles_and_url() -> None:
    text = invite_text()
    assert "Integrity precedes execution" in text
    assert "Propagation is not infection" in text
    assert DOWNLOAD_URL in text
    assert "https://azos-download-tracker.vibelock.workers.dev/" in text
    assert "silent" in text.lower() or "voluntary" in text.lower()


def test_invite_does_not_write_files_outside_cwd(tmp_path: Path, monkeypatch) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    marker = outside / "marker.txt"
    marker.write_text("stay\n", encoding="utf-8")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    before_out = {p.name: p.stat().st_mtime_ns for p in outside.iterdir()}
    before_cwd = list(cwd.iterdir())
    buf = io.StringIO()
    emit_invite(buf)
    assert "AZ-OS" in buf.getvalue()
    after_cwd = list(cwd.iterdir())
    assert after_cwd == before_cwd
    after_out = {p.name: p.stat().st_mtime_ns for p in outside.iterdir()}
    assert after_out == before_out
    assert marker.read_text(encoding="utf-8") == "stay\n"


def test_cli_invite_writes_nothing(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["invite"])
    assert rc == 0
    captured = capsys.readouterr()
    assert DOWNLOAD_URL in captured.out
    assert "Integrity precedes execution" in captured.out
    leftover = [p for p in tmp_path.iterdir() if p.name != ".azos"]
    # invite must not scatter files; .azos would be unexpected too
    assert leftover == []
    assert not (tmp_path / ".azos").exists()
