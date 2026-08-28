"""Five gates: FAIL → no token; all PASS → token."""

from __future__ import annotations

from azos.exec import SAFE_ACTIONS
from azos.gate import GATES, Proposal, authorize
from azos.runtime import Runtime
from tests.conftest import passing_proposal


def test_all_five_gates_named() -> None:
    assert GATES == (
        "definition",
        "evidence",
        "impact",
        "integrity",
        "responsibility",
    )


def test_empty_proposal_fails_all_relevant() -> None:
    result = authorize(Proposal(action=""), SAFE_ACTIONS)
    assert result.passed is False
    assert result.gates["definition"].passed is False
    assert result.gates["evidence"].passed is False
    assert result.gates["impact"].passed is False
    assert result.gates["integrity"].passed is False
    assert result.gates["responsibility"].passed is False


def test_unknown_module_fails_integrity_even_with_comprehension() -> None:
    p = Proposal(
        action="load_unsigned",
        definition="Load a new unsigned module into the overlay.",
        evidence="Operator wants to experiment with an extension.",
        impact="Would execute unsigned code if allowed; must not.",
        actor="tester",
        extend_module=True,
        comprehension=True,
        intent="I want to load extra code I wrote into AZ-OS.",
    )
    result = authorize(p, SAFE_ACTIONS)
    assert result.passed is False
    assert result.gates["integrity"].passed is False


def test_extend_without_comprehension_fails() -> None:
    p = passing_proposal("echo")
    p.extend_module = True
    p.comprehension = False
    p.intent = ""
    result = authorize(p, SAFE_ACTIONS)
    assert result.passed is False


def test_fail_returns_invite_no_token(runtime: Runtime) -> None:
    result = runtime.request(Proposal(action="echo"))
    assert result.passed is False
    assert result.token is None
    assert result.invite
    assert "Integrity precedes execution" in result.invite
