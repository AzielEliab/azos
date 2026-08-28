"""CLI: version, status, exec, halt, purge --confirm."""

from __future__ import annotations

from pathlib import Path

from azos.cli import main
from azos.runtime import Runtime
from tests.conftest import passing_proposal


def test_version(capsys) -> None:
    assert main(["version"]) == 0
    assert "azos 0.1.0" in capsys.readouterr().out


def test_status_json(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert "AZ-OS" in out
    assert "lumen" in out


def test_exec_without_token_prints_invite(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["exec", "echo"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "unauthorized" in err.lower() or "token" in err.lower()
    assert "Integrity precedes execution" in err


def test_exec_with_active_token(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rt = Runtime(root=tmp_path)
    result = rt.request(passing_proposal())
    rt.lumen.stop()
    rc = main(["exec", "echo", "hello", "--token", result.token])
    assert rc == 0
    assert "hello" in capsys.readouterr().out


def test_purge_without_confirm_refuses(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    rc = main(["purge"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "--confirm" in err


def test_halt_then_status(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["halt"]) == 0
    capsys.readouterr()
    assert main(["status"]) == 0
    out = capsys.readouterr().out
    assert '"halted": true' in out
    assert '"lumen": "running"' in out


def test_help_lists_ui_and_version() -> None:
    from azos.cli import _build_parser

    text = _build_parser().format_help()
    assert "ui" in text
    assert "version" in text
    assert "azos ui" in text or "127.0.0.1:8800" in text
