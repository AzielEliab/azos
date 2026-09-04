"""Ethics-coded remote shell: session + sandboxed vfs + principle-bound commands.

This is a true remote shell. It is not unrestricted host bash, not SSH,
and not a kernel. Every command is re-run through the five gates.

Local sandbox root: ``<session>/.azos/workspace/<id>/``.
Hosted Worker uses an in-memory / KV vfs with the same verb list.
"""

from __future__ import annotations

import json
import secrets
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azos.ethics import (
    HISTORY_CAP,
    MAX_FILE_BYTES,
    MOTTO,
    PRINCIPLES,
    SHELL_VERBS,
    scope_dict,
)
from azos.errors import AuthorizationError, HaltedError
from azos.gate import authorize_command
from azos.invite import invite_text

WELCOME_NAME = "welcome.txt"
WELCOME_TEXT = (
    "AZ-OS ethics-coded remote shell\n"
    f"{MOTTO}\n"
    "Author: Aziel Eliab\n"
    "\n"
    "This session is a sandboxed vfs. Commands are principle-bound.\n"
    "Protocols: https-json (hosted), http-loopback (AZ Interface), cli-stdin.\n"
    "Auth: ARC token after the five gates. Sandbox: session vfs only.\n"
    "No host subprocess. No SSH. No kernel. Type `help`.\n"
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return secrets.token_hex(16)


def parse_line(line: str) -> list[str]:
    """Split a command line. Quotes allowed. Never passed to a host shell."""
    try:
        return shlex.split(line, posix=True)
    except ValueError:
        return [line.strip()] if line.strip() else []


class Workspace:
    """Virtual filesystem confined to ``root``. Paths never escape."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        welcome = self.root / WELCOME_NAME
        if not welcome.exists():
            welcome.write_text(WELCOME_TEXT, encoding="utf-8")
        self.cwd = Path("/")

    def _virt(self, user_path: str | None) -> Path:
        raw = (user_path or "").strip() or "."
        if raw.startswith("~"):
            raise AuthorizationError("sandbox: home expansion is out of scope")
        current = Path("/") / self.cwd.as_posix().lstrip("/")
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = current / candidate
        parts: list[str] = []
        for part in candidate.as_posix().split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if parts:
                    parts.pop()
                continue
            parts.append(part)
        return Path("/") / "/".join(parts) if parts else Path("/")

    def real(self, user_path: str | None = None) -> Path:
        virt = self._virt(user_path)
        rel = virt.as_posix().lstrip("/")
        target = (self.root / rel).resolve() if rel else self.root
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise AuthorizationError("sandbox: path escapes session vfs") from exc
        return target

    def virt_of(self, real_path: Path) -> str:
        rel = real_path.resolve().relative_to(self.root)
        posix = rel.as_posix()
        return "/" if posix == "." else "/" + posix

    def pwd(self) -> str:
        posix = self.cwd.as_posix()
        return posix if posix.startswith("/") else "/" + posix

    def cd(self, path: str) -> str:
        target = self.real(path)
        if not target.exists() or not target.is_dir():
            raise AuthorizationError(f"sandbox: not a directory: {path}")
        self.cwd = Path(self.virt_of(target))
        return self.pwd()

    def ls(self, path: str | None = None) -> list[str]:
        target = self.real(path) if path else self.real(self.pwd())
        if not target.exists():
            raise AuthorizationError(f"sandbox: no such path: {path or self.pwd()}")
        if target.is_file():
            return [target.name]
        names = []
        for child in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            names.append(child.name + ("/" if child.is_dir() else ""))
        return names

    def cat(self, path: str) -> str:
        target = self.real(path)
        if not target.is_file():
            raise AuthorizationError(f"sandbox: not a file: {path}")
        data = target.read_bytes()
        if len(data) > MAX_FILE_BYTES:
            raise AuthorizationError("sandbox: file exceeds cap")
        return data.decode("utf-8", errors="replace")

    def write(self, path: str, text: str) -> str:
        target = self.real(path)
        payload = text.encode("utf-8")
        if len(payload) > MAX_FILE_BYTES:
            raise AuthorizationError("sandbox: write exceeds cap")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not str(target.parent.resolve()).startswith(str(self.root)):
            raise AuthorizationError("sandbox: path escapes session vfs")
        target.write_text(text, encoding="utf-8")
        return self.virt_of(target)

    def mkdir(self, path: str) -> str:
        target = self.real(path)
        target.mkdir(parents=True, exist_ok=True)
        return self.virt_of(target)

    def rm(self, path: str) -> str:
        target = self.real(path)
        if target == self.root:
            raise AuthorizationError("sandbox: refusing to remove workspace root")
        if not target.exists():
            raise AuthorizationError(f"sandbox: no such path: {path}")
        if target.is_dir():
            if any(target.iterdir()):
                raise AuthorizationError("sandbox: directory not empty")
            target.rmdir()
        else:
            target.unlink()
        return self.virt_of(target)


class Shell:
    """Session manager bound to one Runtime."""

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        self._workspaces: dict[str, Workspace] = {}

    def _store_path(self) -> Path:
        return self.runtime.session_dir / "sessions.json"

    def _workspace_root(self, session_id: str) -> Path:
        return self.runtime.session_dir / "workspace" / session_id

    def _load(self) -> list[dict[str, Any]]:
        path = self._store_path()
        if not path.is_file():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        rows = data.get("sessions") if isinstance(data, dict) else None
        return list(rows) if isinstance(rows, list) else []

    def _save(self, rows: list[dict[str, Any]]) -> None:
        self.runtime.session_dir.mkdir(parents=True, exist_ok=True)
        self._store_path().write_text(
            json.dumps({"sessions": rows}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _workspace(self, session_id: str) -> Workspace:
        ws = self._workspaces.get(session_id)
        if ws is None:
            ws = Workspace(self._workspace_root(session_id))
            rec = self._record(session_id)
            if rec and rec.get("cwd"):
                try:
                    ws.cwd = Path(str(rec["cwd"]))
                except (TypeError, ValueError):
                    ws.cwd = Path("/")
            self._workspaces[session_id] = ws
        return ws

    def _record(self, session_id: str) -> dict[str, Any] | None:
        for rec in self._load():
            if rec.get("id") == session_id:
                return rec
        return None

    def _update(self, session_id: str, **fields: Any) -> dict[str, Any]:
        rows = self._load()
        found = None
        for rec in rows:
            if rec.get("id") == session_id:
                rec.update(fields)
                found = rec
                break
        if found is None:
            raise AuthorizationError("unauthorized: unknown session")
        self._save(rows)
        return found

    def open(
        self,
        *,
        token: str | None = None,
        actor: str = "",
    ) -> dict[str, Any]:
        """Open a shell session. Requires a live ARC token."""
        if self.runtime.halted:
            raise HaltedError()
        token_hash = self._require_token(token)
        named = (actor or "").strip() or "operator"
        session_id = _new_id()
        ws = self._workspace(session_id)
        rec = {
            "id": session_id,
            "token_hash": token_hash,
            "actor": named,
            "cwd": ws.pwd(),
            "opened_at": _utcnow(),
            "closed": False,
            "history": [],
        }
        rows = self._load()
        rows.append(rec)
        self._save(rows)
        return self._public(rec, token=None)

    def close(self, session_id: str, *, token: str | None = None) -> dict[str, Any]:
        rec = self._require_session(session_id, token)
        self._update(session_id, closed=True, closed_at=_utcnow())
        self._workspaces.pop(session_id, None)
        rec = self._record(session_id) or rec
        return {"ok": True, "closed": True, "session": rec.get("id")}

    def execute(
        self,
        command: str,
        *,
        session_id: str,
        token: str | None = None,
    ) -> dict[str, Any]:
        if self.runtime.halted:
            raise HaltedError()
        rec = self._require_session(session_id, token)
        actor = str(rec.get("actor") or "")
        gate = authorize_command(
            command,
            actor=actor,
            session_live=True,
            allowed=SHELL_VERBS,
        )
        gates = {
            name: {"pass": check.passed, "reason": check.reason}
            for name, check in gate.gates.items()
        }
        if not gate.passed:
            self._remember(session_id, command, ok=False, stdout="", error="ethics")
            return {
                "ok": False,
                "ethics": False,
                "gates": gates,
                "invite": invite_text(),
                "error": "command failed the ethics gates",
                "session": session_id,
            }
        try:
            stdout, extra = self._dispatch(session_id, command, rec)
        except AuthorizationError as exc:
            self._remember(session_id, command, ok=False, stdout="", error=str(exc))
            return {
                "ok": False,
                "ethics": True,
                "gates": gates,
                "error": str(exc),
                "session": session_id,
                "invite": invite_text(),
            }
        token_hash = str(rec.get("token_hash") or "active-session")
        verb = (parse_line(command) or ["?"])[0]
        self.runtime.log.append(
            action=f"shell:{verb}",
            token_hash=token_hash,
            payload={"ok": True, "command": verb, "session": session_id},
        )
        self._remember(session_id, command, ok=True, stdout=stdout, error="")
        out: dict[str, Any] = {
            "ok": True,
            "ethics": True,
            "gates": gates,
            "stdout": stdout,
            "session": session_id,
            "cwd": self._workspace(session_id).pwd(),
        }
        out.update(extra)
        return out

    def snapshot(self, session_id: str | None = None) -> dict[str, Any]:
        rows = [r for r in self._load() if not r.get("closed")]
        if session_id:
            rec = self._record(session_id)
            return self._public(rec, token=None) if rec else {"session": None}
        return {
            "active": len(rows),
            "sessions": [self._public(r, token=None) for r in rows],
        }

    def reset(self) -> None:
        self._workspaces.clear()

    def _dispatch(
        self, session_id: str, command: str, rec: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        parts = parse_line(command)
        verb = (parts[0] if parts else "").lower()
        args = parts[1:]
        ws = self._workspace(session_id)
        extra: dict[str, Any] = {}

        if verb == "help":
            text = (
                "AZ-OS ethics-coded remote shell. Registered verbs:\n  "
                + " ".join(sorted(SHELL_VERBS))
                + "\n"
                + MOTTO
                + "\n"
                + "Sandbox: session vfs. No host subprocess. No SSH.\n"
            )
            return text, extra
        if verb == "pwd":
            return ws.pwd() + "\n", extra
        if verb == "ls":
            names = ws.ls(args[0] if args else None)
            return ("\n".join(names) + ("\n" if names else "")), extra
        if verb == "cat":
            if not args:
                raise AuthorizationError("usage: cat <file>")
            return ws.cat(args[0]), extra
        if verb == "write":
            if len(args) < 2:
                raise AuthorizationError("usage: write <file> <text>")
            path = ws.write(args[0], " ".join(args[1:]))
            return f"wrote {path}\n", extra
        if verb == "echo":
            if len(args) >= 2 and args[-2] == ">":
                path = ws.write(args[-1], " ".join(args[:-2]))
                return f"wrote {path}\n", extra
            return ((" ".join(args) + "\n") if args else "\n"), extra
        if verb == "mkdir":
            if not args:
                raise AuthorizationError("usage: mkdir <path>")
            return f"{ws.mkdir(args[0])}\n", extra
        if verb == "rm":
            if not args:
                raise AuthorizationError("usage: rm <path>")
            return f"removed {ws.rm(args[0])}\n", extra
        if verb == "cd":
            return ws.cd(args[0] if args else "/") + "\n", extra
        if verb == "status":
            extra["status"] = self.runtime.status()
            return json.dumps(extra["status"], indent=2) + "\n", extra
        if verb == "principles":
            block = "\n".join(f"{i}. {p}" for i, p in enumerate(PRINCIPLES, start=1))
            return block + "\n", extra
        if verb == "invite":
            return invite_text(), extra
        if verb in {"modules", "list_modules"}:
            return " ".join(sorted(SHELL_VERBS)) + "\n", extra
        if verb == "history":
            hist = rec.get("history") or []
            lines = [
                f"{h.get('ok') and 'ok' or 'no'}  {h.get('command', '')}"
                for h in hist[-HISTORY_CAP:]
            ]
            return ("\n".join(lines) + ("\n" if lines else "")), extra
        if verb == "whoami":
            return str(rec.get("actor") or "operator") + "\n", extra
        if verb == "session":
            extra["scope"] = scope_dict()
            return json.dumps(self._public(rec, token=None), indent=2) + "\n", extra
        if verb == "halt":
            self.runtime.halt()
            extra["halted"] = True
            return "halted. Lumen keeps custody. Session will refuse new commands.\n", extra
        if verb in {"exit", "close"}:
            self.close(session_id)
            extra["closed"] = True
            return "session closed.\n", extra
        if verb == "id":
            return session_id + "\n", extra
        if verb == "uname":
            return "AZ-OS ethics-coded remote shell (session-vfs)\n", extra
        raise AuthorizationError(f"unauthorized: {verb!r} is not a registered shell verb")

    def _remember(
        self,
        session_id: str,
        command: str,
        *,
        ok: bool,
        stdout: str,
        error: str,
    ) -> None:
        rec = self._record(session_id)
        if rec is None:
            return
        history = list(rec.get("history") or [])
        history.append(
            {
                "command": command[:200],
                "ok": ok,
                "error": error[:200] if error else "",
                "at": _utcnow(),
            }
        )
        cwd = self._workspace(session_id).pwd()
        self._update(
            session_id,
            history=history[-HISTORY_CAP:],
            cwd=cwd,
        )

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

    def _require_session(self, session_id: str, token: str | None) -> dict[str, Any]:
        rec = self._record(session_id)
        if rec is None or rec.get("closed"):
            raise AuthorizationError("unauthorized: session missing or closed")
        token_hash = self._require_token(token)
        stored = rec.get("token_hash")
        if stored and stored != token_hash and token:
            raise AuthorizationError("unauthorized: token does not match session")
        return rec

    def _public(self, rec: dict[str, Any] | None, token: str | None) -> dict[str, Any]:
        if not rec:
            return {"session": None}
        return {
            "session": rec.get("id"),
            "actor": rec.get("actor"),
            "cwd": rec.get("cwd") or "/",
            "opened_at": rec.get("opened_at"),
            "closed": bool(rec.get("closed")),
            "history_length": len(rec.get("history") or []),
            "scope": scope_dict(),
            "token": token,
        }
