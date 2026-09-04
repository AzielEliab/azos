"""Run registered *safe* builtin actions by name.

No eval(). No exec() of user strings. No host subprocess.
The `shell` builtin opens the ethics-coded session vfs — not bash.

Unsigned / unauthorized run() raises AuthorizationError. Default deny.

Safe builtins: list_modules, echo, status, purge_session, shell.
"""

from __future__ import annotations

from typing import Any, Callable

from azos.errors import AuthorizationError, HaltedError
from azos.ethics import SHELL_VERBS

# Closed allow-list. Names only. Never a user-supplied callable.
SAFE_ACTIONS = frozenset(
    {"list_modules", "echo", "status", "purge_session", "shell"}
)


def _echo(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    message = args.get("message", "ok")
    if not isinstance(message, str):
        message = "ok"
    # Bound the echo; never pass it to a host shell.
    return {"echo": message[:4096]}


def _list_modules(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    return {
        "modules": sorted(SAFE_ACTIONS),
        "shell_verbs": sorted(SHELL_VERBS),
    }


def _status(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    return runtime.status()


def _purge_session(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    runtime.lumen.purge_session(confirm=True)
    runtime.shell.reset()
    return {"purged": True, "session": str(runtime.session_dir)}


def _shell(runtime: Any, args: dict[str, Any]) -> dict[str, Any]:
    command = args.get("command") or args.get("line") or args.get("message") or ""
    session_id = args.get("session") or args.get("session_id")
    token = args.get("token")
    token_s = str(token) if token else None
    if not session_id:
        opened = runtime.shell.open(token=token_s, actor=str(args.get("actor") or ""))
        session_id = opened["session"]
        if not str(command).strip():
            return {"opened": True, **opened}
    return runtime.shell.execute(
        str(command),
        session_id=str(session_id),
        token=token_s,
    )


_HANDLERS: dict[str, Callable[[Any, dict[str, Any]], dict[str, Any]]] = {
    "echo": _echo,
    "list_modules": _list_modules,
    "status": _status,
    "purge_session": _purge_session,
    "shell": _shell,
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
        if token and "token" not in payload:
            payload["token"] = token
        result = handler(self.runtime, payload)
        # Do not log the raw token. Hash only. Shell logs per-command itself.
        if action != "shell":
            log_payload = {"ok": True, "args_keys": sorted(k for k in payload.keys() if k != "token")}
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
