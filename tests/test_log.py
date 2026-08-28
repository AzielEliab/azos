"""Append-only execution log. Cannot edit."""

from __future__ import annotations

import pytest

from azos.errors import AppendOnlyError
from azos.log import ExecutionLog
from azos.runtime import Runtime
from tests.conftest import passing_proposal


def test_log_append_only_cannot_edit(runtime: Runtime) -> None:
    result = runtime.request(passing_proposal())
    runtime.run("echo", token=result.token, args={"message": "one"})
    runtime.run("echo", token=result.token, args={"message": "two"})
    log = runtime.log
    assert len(log) == 2
    first_hash = log[0].hash
    assert log[1].prev_hash == first_hash
    with pytest.raises(AppendOnlyError):
        log.pop()
    with pytest.raises(AppendOnlyError):
        log.clear()
    with pytest.raises(AppendOnlyError):
        log.insert(0, log[0])
    with pytest.raises(AppendOnlyError):
        log.remove(log[0])
    with pytest.raises(AppendOnlyError):
        log.reverse()
    with pytest.raises(AppendOnlyError):
        log[0] = log[1]
    with pytest.raises(AppendOnlyError):
        del log[0]
    assert len(log) == 2
    assert log[0].hash == first_hash
    assert not hasattr(log, "rewrite")
    assert not hasattr(log, "edit")


def test_log_file_is_append_mode(tmp_path) -> None:
    path = tmp_path / "exec.jsonl"
    log = ExecutionLog(path)
    log.append(action="echo", token_hash="a" * 64, payload={"n": 1})
    log.append(action="echo", token_hash="a" * 64, payload={"n": 2})
    text = path.read_text(encoding="utf-8")
    assert text.count("\n") == 2
    # The API still refuses mutation after reload
    reloaded = ExecutionLog(path)
    with pytest.raises(AppendOnlyError):
        reloaded.pop()
    assert len(reloaded) == 2
