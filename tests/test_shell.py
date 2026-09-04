"""Ethics-coded remote shell: session, vfs, per-command gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from azos.errors import AuthorizationError, HaltedError
from azos.ethics import SHELL_VERBS
from azos.gate import authorize_command, shell_proposal
from azos.runtime import Runtime
from tests.conftest import passing_proposal


def _open(runtime: Runtime, actor: str = "tester") -> tuple[str, str]:
    result = runtime.request(shell_proposal(actor))
    assert result.passed is True
    assert result.token
    opened = runtime.open_session(token=result.token, actor=actor)
    assert opened["session"]
    return result.token, opened["session"]


def test_session_requires_token(runtime: Runtime) -> None:
    with pytest.raises(AuthorizationError):
        runtime.open_session(actor="tester")


def test_shell_ls_and_write_and_cat(runtime: Runtime) -> None:
    token, session = _open(runtime)
    listed = runtime.run_command("ls", session_id=session, token=token)
    assert listed["ok"] is True
    assert listed["ethics"] is True
    assert "welcome.txt" in listed["stdout"]
    wrote = runtime.run_command(
        "write note.txt hello-ethics", session_id=session, token=token
    )
    assert wrote["ok"] is True
    cat = runtime.run_command("cat note.txt", session_id=session, token=token)
    assert cat["stdout"] == "hello-ethics"


def test_path_escape_denied(runtime: Runtime) -> None:
    token, session = _open(runtime)
    out = runtime.run_command("cat ../../etc/passwd", session_id=session, token=token)
    assert out["ok"] is False


def test_denied_verb_fails_integrity(runtime: Runtime) -> None:
    token, session = _open(runtime)
    out = runtime.run_command("bash -c id", session_id=session, token=token)
    assert out["ok"] is False
    assert out["ethics"] is False
    assert out["gates"]["integrity"]["pass"] is False
    assert out["invite"]


def test_host_meta_fails_impact(runtime: Runtime) -> None:
    token, session = _open(runtime)
    out = runtime.run_command("ls | cat", session_id=session, token=token)
    assert out["ok"] is False
    assert out["gates"]["impact"]["pass"] is False


def test_halt_then_command_fails(runtime: Runtime) -> None:
    token, session = _open(runtime)
    runtime.halt()
    with pytest.raises(HaltedError):
        runtime.run_command("ls", session_id=session, token=token)


def test_cli_shell_command(tmp_path: Path, monkeypatch, capsys) -> None:
    from azos.cli import main

    monkeypatch.chdir(tmp_path)
    rc = main(["shell", "--actor", "tester", "-c", "uname"])
    assert rc == 0
    assert "ethics-coded remote shell" in capsys.readouterr().out


def test_authorize_command_requires_actor_and_session() -> None:
    denied = authorize_command("ls", actor="", session_live=False)
    assert denied.passed is False
    ok = authorize_command("ls", actor="tester", session_live=True, allowed=SHELL_VERBS)
    assert ok.passed is True


def test_exec_shell_builtin_opens_and_runs(runtime: Runtime) -> None:
    result = runtime.request(passing_proposal("shell"))
    out = runtime.run(
        "shell",
        token=result.token,
        args={"command": "pwd", "actor": "tester"},
    )
    assert out["ok"] is True
    assert out["stdout"].strip() == "/"


def test_workspace_stays_under_session(runtime: Runtime, tmp_path: Path) -> None:
    token, session = _open(runtime)
    runtime.run_command("write a.txt x", session_id=session, token=token)
    workspace = tmp_path / ".azos" / "workspace" / session / "a.txt"
    assert workspace.is_file()
    assert workspace.read_text(encoding="utf-8") == "x"
    home_marker = Path.home() / "azos-should-not-exist-shell-test"
    assert not home_marker.exists()
