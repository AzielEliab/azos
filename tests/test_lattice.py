"""TemporalLock × StaticClock integrity lattice: no rollbacks."""

from __future__ import annotations

import pytest

from azos.errors import AppendOnlyError
from azos.lattice import IntegrityLattice
from azos.runtime import Runtime
from tests.conftest import passing_proposal


def test_gear_click_then_timeslate(tmp_path) -> None:
    lat = IntegrityLattice(tmp_path / ".azos")
    first = lat.bind("boot", summary="genesis", evidence="session start")
    assert first["kind"] == "genesis"
    assert first["rollback"] is False
    second = lat.bind("exec", summary="command", evidence="ethics pass")
    assert second["kind"] == "append"
    assert second["gear"]["tick"] == 2
    assert lat.verify() is True
    assert lat.temporal[1].gear_hash == lat.clock.tip().hash


def test_no_rollback(tmp_path) -> None:
    lat = IntegrityLattice(tmp_path / ".azos")
    lat.bind("a", summary="a", evidence="a")
    with pytest.raises(AppendOnlyError):
        lat.clock.pop()
    with pytest.raises(AppendOnlyError):
        lat.temporal.clear()
    with pytest.raises(AppendOnlyError):
        lat.clock.reverse()


def test_runtime_binds_on_request(runtime: Runtime) -> None:
    assert runtime.lattice.snapshot()["gear_ticks"] == 0
    runtime.request(passing_proposal("shell"))
    snap = runtime.lattice.snapshot()
    assert snap["gear_ticks"] >= 1
    assert snap["verified"] is True
    assert snap["rollback"] is False
