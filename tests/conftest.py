from __future__ import annotations

from pathlib import Path

import pytest

from azos.gate import Proposal
from azos.runtime import Runtime


@pytest.fixture
def runtime(tmp_path: Path) -> Runtime:
    return Runtime(root=tmp_path)


def passing_proposal(action: str = "echo") -> Proposal:
    return Proposal(
        action=action,
        definition="Print a bounded status string from a registered builtin.",
        evidence="Action is on the closed SAFE_ACTIONS list in azos.exec.",
        impact="In-process result only. No host disk, no other machines.",
        actor="tester",
    )
