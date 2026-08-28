"""Run registered *safe* builtin actions by name.

No eval(). No exec() of user strings. No subprocess. No shell.
Unsigned / unauthorized run() raises AuthorizationError. Default deny.

Safe builtins: list_modules, echo, status, purge_session.
"""

from __future__ import annotations

from typing import Any, Callable

from azos.errors import AuthorizationError, HaltedError

# Closed allow-list. Names only. Never a user-supplied callable.
SAFE_ACTIONS = frozenset({"list_modules", "echo", "status", "purge_session"})


def _echo(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    message = args.get("message", "ok")
    if not isinstance(message, str):
        message = "ok"
    # Bound the echo; never pass it to a shell.
    return {"echo": message[:4096]}


def _list_modules(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    return {"modules": sorted(SAFE_ACTIONS)}


def _status(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    return runtime.status()


def _purge_session(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    runtime.lumen.purge_session(confirm=True)
    return {"purged": True, "session": str(runtime.session_dir)}


_HANDLERS: dict[str, Callable[[Any, dict[str, Any]], dict[str, Any]]] = {
    "echo": _echo,
    "list_modules": _list_modules,
    "status": _status,
    "purge_session": _purge_session,
}


class Executor:
    """Dispatch a named builtin after ARC verifies a live token."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    def run(
        self,
        name: str,
        token: str | None = None,
        args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a registered builtin. Default deny.

        ``token`` is required unless ARC already has a live token
        (CLI ``azos exec NAME`` after the Interface issued one).
        """
        if self.runtime.halted:
            raise HaltedError()
        action = (name or "").strip()
        if action not in SAFE_ACTIONS:
            raise AuthorizationError(
                f"unauthorized: {action!r} is not a registered safe builtin"
            )
        token_hash = self._require_token(token)
        handler = _HANDLERS[action]
        payload = dict(args or {})
        result = handler(self.runtime, payload)
        # Do not log the raw token. Hash only.
        log_payload = {"ok": True, "args_keys": sorted(payload.keys())}
        self.runtime.log.append(
            action=action,
            token_hash=token_hash,
            payload=log_payload,
        )
        return result

    def _require_token(self, token: str | None) -> str:
        arc = self.runtime.arc
        if token:
            if not arc.verify(token):
                raise AuthorizationError("unauthorized: token missing or revoked")
            return arc.token_hash(token)
        if arc.has_active():
            hashes = arc.active_hashes()
            return hashes[0] if hashes else "active-session"
        raise AuthorizationError("unauthorized: no ARC token")
