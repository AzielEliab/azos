"""Tiny five-gate check (DecisionGATE-shaped, reimplemented inline).

Gates: definition, evidence, impact, integrity, responsibility.
Any FAIL → no token. Default deny.

Unauthorized or incomplete proposals produce a GateResult with
passed=False so the Interface can show an invite, not a silent block.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import AbstractSet, Mapping

GATES = (
    "definition",
    "evidence",
    "impact",
    "integrity",
    "responsibility",
)

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
    banned = ("wipe disk", "format drive", "mkfs", "self-replicate", "worm")
    if not _filled(proposal.impact):
        checks["impact"] = GateCheck(
            False, "impact must state what will change (min 8 chars)"
        )
    elif any(b in impact for b in banned):
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


def summary(result: GateResult) -> list[Mapping[str, object]]:
    return [
        {"gate": name, "pass": result.gates[name].passed, "reason": result.gates[name].reason}
        for name in GATES
        if name in result.gates
    ]
