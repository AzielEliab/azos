"""Composition root: ARC + Lumen + gate + exec + log + ethics-coded shell."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from azos.arc import ARC
from azos.ethics import KIND, scope_dict
from azos.exec import SAFE_ACTIONS, Executor
from azos.gate import Proposal, authorize
from azos.invite import invite_text
from azos.log import ExecutionLog
from azos.lumen import Lumen
from azos.paths import SESSION_DIRNAME
from azos.shell import Shell

__all__ = ["Runtime", "RequestResult", "SAFE_ACTIONS"]


@dataclass
class RequestResult:
    passed: bool
    token: str | None
    gates: dict[str, Any]
    invite: str | None

    def as_dict(self) -> dict[str, Any]:
        preview = None
        if self.token:
            preview = self.token[:8] + "…"
        return {
            "passed": self.passed,
            "token": self.token,
            "token_preview": preview,
            "gates": self.gates,
            "invite": self.invite,
        }


class Runtime:
    """One overlay session rooted at ``<root>/.azos``."""

    def __init__(
        self,
        root: Path | str | None = None,
        *,
        start_lumen: bool = True,
    ) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self.session_dir = self.root / SESSION_DIRNAME
        self.arc = ARC(self.session_dir)
        self.log = ExecutionLog(self.session_dir / "exec.jsonl")
        self._halted = False
        self._load_state()
        self.lumen = Lumen(self)
        self.executor = Executor(self)
        self.shell = Shell(self)
        if start_lumen:
            self.lumen.start()

    @property
    def halted(self) -> bool:
        return self._halted

    def mark_halted(self, value: bool = True) -> None:
        self._halted = bool(value)
        self._save_state()

    def request(self, proposal: Proposal) -> RequestResult:
        """Five gates then (only on PASS) an ARC token. FAIL → invite, no token."""
        if self._halted:
            return RequestResult(
                passed=False,
                token=None,
                gates={
                    "definition": {"pass": False, "reason": "overlay is halted"},
                    "evidence": {"pass": False, "reason": "overlay is halted"},
                    "impact": {"pass": False, "reason": "overlay is halted"},
                    "integrity": {"pass": False, "reason": "overlay is halted"},
                    "responsibility": {"pass": False, "reason": "overlay is halted"},
                },
                invite=invite_text(),
            )
        result = authorize(proposal, SAFE_ACTIONS)
        gates = {
            name: {"pass": check.passed, "reason": check.reason}
            for name, check in result.gates.items()
        }
        if not result.passed:
            return RequestResult(
                passed=False,
                token=None,
                gates=gates,
                invite=invite_text(),
            )
        token = self.arc.issue(action=proposal.action, actor=proposal.actor)
        return RequestResult(passed=True, token=token, gates=gates, invite=None)

    def run(
        self,
        name: str,
        token: str | None = None,
        args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.executor.run(name, token=token, args=args)

    def open_session(self, *, token: str | None = None, actor: str = "") -> dict[str, Any]:
        return self.shell.open(token=token, actor=actor)

    def run_command(
        self,
        command: str,
        *,
        session_id: str,
        token: str | None = None,
    ) -> dict[str, Any]:
        return self.shell.execute(command, session_id=session_id, token=token)

    def status(self) -> dict[str, Any]:
        arc = self.arc.snapshot()
        scope = scope_dict()
        return {
            "overlay": "AZ-OS",
            "interface": "AZ Interface",
            "kind": KIND,
            "version": _version(),
            "session": str(self.session_dir),
            "halted": self._halted,
            "lumen": "running" if self.lumen.running else "stopped",
            "tokens": arc,
            "log_length": len(self.log),
            "builtins": sorted(SAFE_ACTIONS),
            "shell": self.shell.snapshot(),
            **scope,
        }

    def halt(self) -> dict[str, Any]:
        return self.lumen.halt()

    def purge(self, *, confirm: bool) -> dict[str, Any]:
        return self.lumen.purge_session(confirm=confirm)

    def _state_path(self) -> Path:
        return self.session_dir / "state.json"

    def _load_state(self) -> None:
        path = self._state_path()
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if isinstance(data, dict):
            self._halted = bool(data.get("halted"))

    def _save_state(self) -> None:
        self.session_dir.mkdir(parents=True, exist_ok=True)
        payload = {"halted": self._halted, "lumen": "running"}
        self._state_path().write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )


def _version() -> str:
    from azos import __version__

    return __version__
