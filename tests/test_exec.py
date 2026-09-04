"""exec without token raises; token after PASS allows builtin; revoke then fail."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from azos.errors import AuthorizationError, HaltedError
from azos.gate import Proposal
from azos.runtime import Runtime
from tests.conftest import passing_proposal

PKG_EXEC = Path(__file__).resolve().parents[1] / "azos" / "exec.py"


def test_exec_without_token_raises(runtime: Runtime) -> None:
    with pytest.raises(AuthorizationError):
        runtime.run("echo")


def test_root_string_does_not_auto_grant(runtime: Runtime) -> None:
    with pytest.raises(AuthorizationError):
        runtime.run("echo", token="root")
    with pytest.raises(AuthorizationError):
        runtime.run("echo", token="user")
    # actor=root still has to pass gates; it is not a skip
    bad = Proposal(
        action="echo",
        definition="",
        evidence="",
        impact="",
        actor="root",
    )
    result = runtime.request(bad)
    assert result.passed is False
    assert result.token is None


def test_token_after_pass_allows_builtin(runtime: Runtime) -> None:
    result = runtime.request(passing_proposal("echo"))
    assert result.passed is True
    assert result.token
    out = runtime.run("echo", token=result.token, args={"message": "ok"})
    assert out["echo"] == "ok"
    listed = runtime.run("list_modules", token=result.token)
    assert "echo" in listed["modules"]
    assert "shell" in listed["modules"]
    st = runtime.run("status", token=result.token)
    assert st["overlay"] == "AZ-OS"
    assert st["kernel"] is False


def test_revoke_then_exec_fails(runtime: Runtime) -> None:
    result = runtime.request(passing_proposal("echo"))
    token = result.token
    assert token
    runtime.arc.revoke(token)
    with pytest.raises(AuthorizationError):
        runtime.run("echo", token=token)


def test_unknown_action_denied_even_with_token(runtime: Runtime) -> None:
    result = runtime.request(passing_proposal("echo"))
    with pytest.raises(AuthorizationError):
        runtime.run("not_a_builtin", token=result.token)


def test_halt_then_exec_fails(runtime: Runtime) -> None:
    result = runtime.request(passing_proposal("echo"))
    runtime.halt()
    with pytest.raises(HaltedError):
        runtime.run("echo", token=result.token)


def test_no_eval_or_subprocess_in_exec_module() -> None:
    source = PKG_EXEC.read_text(encoding="utf-8")
    tree = ast.parse(source)
    banned_calls = {"eval", "exec", "compile", "system", "popen", "Popen"}
    banned_mods = {"subprocess", "pty", "os"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned_mods
        if isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in {"subprocess", "pty"}
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in banned_calls
            if isinstance(func, ast.Attribute):
                assert func.attr not in banned_calls
                if func.attr in {"system", "popen", "execv", "execve", "spawn"}:
                    raise AssertionError(f"forbidden call {func.attr}")
