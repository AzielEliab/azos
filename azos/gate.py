"""Tiny five-gate check (DecisionGATE-shaped, reimplemented inline).

Gates: definition, evidence, impact, integrity, responsibility.
Any FAIL → no token / no command. Default deny.

Unauthorized or incomplete proposals produce a GateResult with
passed=False so the Interface can show an invite, not a silent block.

Every shell command is re-evaluated here. A live session is evidence,
not a bypass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AbstractSet, Mapping

from azos.ethics import (
    BANNED_IMPACT,
    DENIED_VERBS,
    GATES as ETHICS_GATES,
    HOST_META,
    MAX_COMMAND_CHARS,
    SHELL_VERBS,
)

GATES = ETHICS_GATES

_MIN = 8


@dataclass
class Proposal:
    """A proposed action presented to the five gates."""

    action: str
    definition: str = ""
    evidence: str = ""
    impact: str = ""
    actor: str = ""
    extend_module: bool = False
    comprehension: bool = False
    intent: str = ""


@dataclass
class GateCheck:
    passed: bool
    reason: str


@dataclass
class GateResult:
    passed: bool
    gates: dict[str, GateCheck] = field(default_factory=dict)

    def as_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "gates": {
                name: {"pass": c.passed, "reason": c.reason}
                for name, c in self.gates.items()
            },
        }


def _filled(value: str, minimum: int = _MIN) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def authorize(proposal: Proposal, allowed: AbstractSet[str]) -> GateResult:
    """Evaluate all five gates. Does not short-circuit (UI shows each)."""
    action = (proposal.action or "").strip()
    checks: dict[str, GateCheck] = {}

    if not action:
        checks["definition"] = GateCheck(False, "action name is required")
    elif not _filled(proposal.definition):
        checks["definition"] = GateCheck(
            False, "definition must state what the action is (min 8 chars)"
        )
    else:
        checks["definition"] = GateCheck(True, "action is defined")

    if not _filled(proposal.evidence):
        checks["evidence"] = GateCheck(
            False, "evidence / justification is required (min 8 chars)"
        )
    else:
        checks["evidence"] = GateCheck(True, "evidence provided")

    impact = (proposal.impact or "").strip().lower()
    if not _filled(proposal.impact):
        checks["impact"] = GateCheck(
            False, "impact must state what will change (min 8 chars)"
        )
    elif any(b in impact for b in BANNED_IMPACT):
        checks["impact"] = GateCheck(False, "impact violates overlay bounds")
    else:
        checks["impact"] = GateCheck(True, "impact stated")

    integrity_ok = True
    integrity_reason = "action is a registered safe builtin"
    if action not in allowed:
        integrity_ok = False
        integrity_reason = "unsigned / unregistered action: default deny"
    if proposal.extend_module:
        if not proposal.comprehension:
            integrity_ok = False
            integrity_reason = (
                "extending a module requires the comprehension checkbox"
            )
        elif not _filled(proposal.intent, 12):
            integrity_ok = False
            integrity_reason = (
                "extending a module requires a short restatement of intent"
            )
        elif action not in allowed:
            integrity_ok = False
            integrity_reason = (
                "understood, but unsigned modules cannot run (integrity)"
            )
    checks["integrity"] = GateCheck(integrity_ok, integrity_reason)

    actor = (proposal.actor or "").strip()
    if not actor:
        checks["responsibility"] = GateCheck(False, "a named actor is required")
    else:
        # Root/user is a name, not a privilege. It does not auto-grant.
        checks["responsibility"] = GateCheck(
            True, f"actor {actor!r} is named (name is not a privilege)"
        )

    passed = all(c.passed for c in checks.values())
    return GateResult(passed=passed, gates=checks)


def parse_verb(line: str) -> str:
    """First token of a command line, lowercased. Empty if unparsable."""
    text = (line or "").strip()
    if not text:
        return ""
    verb = text.split(None, 1)[0].strip().lower()
    if verb.endswith(":"):
        verb = verb[:-1]
    return verb


def authorize_command(
    line: str,
    *,
    actor: str,
    session_live: bool,
    allowed: AbstractSet[str] | None = None,
) -> GateResult:
    """Five-gate check for one shell command. Does not short-circuit.

    A live session is *evidence* that ARC already authorized the operator.
    It is not a privilege skip. Integrity still requires a registered verb.
    """
    allowed_verbs = allowed if allowed is not None else SHELL_VERBS
    checks: dict[str, GateCheck] = {}
    text = line if isinstance(line, str) else ""
    stripped = text.strip()
    verb = parse_verb(stripped)

    if not stripped:
        checks["definition"] = GateCheck(False, "command line is required")
    elif len(stripped) > MAX_COMMAND_CHARS:
        checks["definition"] = GateCheck(
            False, f"command exceeds {MAX_COMMAND_CHARS} characters"
        )
    elif not verb:
        checks["definition"] = GateCheck(False, "command verb is required")
    else:
        checks["definition"] = GateCheck(True, f"command {verb!r} is defined")

    if not session_live:
        checks["evidence"] = GateCheck(
            False, "a live ethics-gated session is required (ARC token)"
        )
    else:
        checks["evidence"] = GateCheck(
            True, "live session is prior authorization (not a bypass)"
        )

    lowered = stripped.lower()
    if any(b in lowered for b in BANNED_IMPACT):
        checks["impact"] = GateCheck(False, "command violates overlay bounds")
    elif any(meta in stripped for meta in HOST_META):
        checks["impact"] = GateCheck(
            False, "host-shell metacharacters are out of sandbox scope"
        )
    else:
        checks["impact"] = GateCheck(True, "impact stays inside the session vfs")

    if verb in DENIED_VERBS:
        checks["integrity"] = GateCheck(
            False, f"denied verb {verb!r}: default deny"
        )
    elif verb and verb not in allowed_verbs:
        checks["integrity"] = GateCheck(
            False, "unsigned / unregistered command: default deny"
        )
    elif verb:
        checks["integrity"] = GateCheck(True, "command is a registered shell verb")
    else:
        checks["integrity"] = GateCheck(
            False, "unsigned / unregistered command: default deny"
        )

    named = (actor or "").strip()
    if not named:
        checks["responsibility"] = GateCheck(False, "a named actor is required")
    else:
        checks["responsibility"] = GateCheck(
            True, f"actor {named!r} is named (name is not a privilege)"
        )

    passed = all(c.passed for c in checks.values())
    return GateResult(passed=passed, gates=checks)


def shell_proposal(actor: str) -> Proposal:
    """Honest proposal for opening a local ethics-gated shell session."""
    return Proposal(
        action="shell",
        definition="Open an ethics-gated AZ-OS shell session in the session vfs.",
        evidence="Operator requested a principle-bound shell via AZ-OS itself.",
        impact="Sandbox workspace under .azos only. No host subprocess. No SSH.",
        actor=actor,
    )


def summary(result: GateResult) -> list[Mapping[str, object]]:
    return [
        {"gate": name, "pass": result.gates[name].passed, "reason": result.gates[name].reason}
        for name in GATES
        if name in result.gates
    ]
