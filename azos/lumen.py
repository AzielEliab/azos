"""Lumen — gatekeeper that keeps running after halt.

Watch loop is in-process. After halt, Lumen can still revoke tokens
and purge the session directory ``.azos/`` only.
"""

from __future__ import annotations

import threading
from typing import Any

from azos.errors import AzosError
from azos.paths import safe_purge


class Lumen:
    """Always-on gatekeeper for the overlay process."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self._alive = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._alive and self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._alive = True
        self._thread = threading.Thread(
            target=self._watch,
            name="azos-lumen",
            daemon=True,
        )
        self._thread.start()

    def _watch(self) -> None:
        # Heartbeat. Halt stops execution, not this loop.
        while not self._stop.is_set():
            self._stop.wait(0.25)

    @property
    def running(self) -> bool:
        return self._alive and not self._stop.is_set()

    def halt(self) -> dict[str, Any]:
        """Stop execution authority. Lumen itself keeps running."""
        self.runtime.mark_halted()
        return self.status()

    def revoke(self, token: str) -> None:
        """Revoke still works after halt."""
        self.runtime.arc.revoke(token)

    def revoke_all(self) -> int:
        return self.runtime.arc.revoke_all()

    def purge_session(self, *, confirm: bool) -> dict[str, Any]:
        """Delete .azos only. Works after halt. Never $HOME or OS files."""
        if not confirm:
            raise AzosError("purge requires --confirm (or typed CONFIRM in the UI)")
        self.runtime.arc.revoke_all()
        if hasattr(self.runtime, "shell"):
            self.runtime.shell.reset()
        target = safe_purge(self.runtime.session_dir)
        self.runtime.log.reload_empty()
        # Do not persist state: that would recreate .azos after purge.
        self.runtime._halted = False
        return {
            "purged": True,
            "session": str(target),
            "lumen": "running" if self.running else "stopped",
        }

    def status(self) -> dict[str, Any]:
        return {
            "lumen": "running" if self.running else "stopped",
            "halted": bool(self.runtime.halted),
            "session": str(self.runtime.session_dir),
        }

    def stop(self) -> None:
        """End the watch loop (process teardown). Not the same as halt."""
        self._alive = False
        self._stop.set()
