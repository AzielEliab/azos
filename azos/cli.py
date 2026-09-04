"""Command-line interface for AZ-OS + AZ Interface.

    azos version
    azos ui                 # 127.0.0.1:8800  THE product
    azos status
    azos invite             # prints voluntary adoption text + download URL
    azos session            # open an ethics-gated shell session
    azos shell              # ethics-coded remote shell (REPL or -c)
    azos exec NAME          # only if a token is active
    azos halt
    azos purge --confirm    # deletes .azos session only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from azos import __version__
from azos.errors import AuthorizationError, AzosError
from azos.gate import shell_proposal
from azos.interface import DEFAULT_HOST, DEFAULT_PORT, serve
from azos.invite import emit_invite, invite_text
from azos.runtime import Runtime


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="azos",
        description=(
            "AZ-OS — ethics-coded remote shell "
            "(Aziel Eliab, 2026). Integrity precedes execution. "
            "Not a kernel, not malware, not unrestricted host bash. "
            "Control surface: `azos ui` at http://127.0.0.1:8800."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="Print package version.")
    sub.add_parser("status", help="Overlay, Lumen, token, shell, and log status.")
    sub.add_parser(
        "invite",
        help="Print voluntary adoption text and the counted download URL. Writes no files.",
    )

    p_ui = sub.add_parser(
        "ui",
        help="Serve AZ Interface on 127.0.0.1:8800 (the product).",
    )
    p_ui.add_argument("--host", default=DEFAULT_HOST, help="Loopback host (default 127.0.0.1).")
    p_ui.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port (default 8800).")

    p_exec = sub.add_parser(
        "exec",
        help="Run a registered safe builtin (list_modules, echo, status, purge_session, shell). Requires a live ARC token.",
    )
    p_exec.add_argument("name", help="Builtin name.")
    p_exec.add_argument(
        "rest",
        nargs="*",
        help="Optional echo message or shell command words. Never passed to a host shell.",
    )
    p_exec.add_argument(
        "--token",
        default=None,
        help="Issued ARC token (hex). If omitted, a live session token must already exist.",
    )
    p_exec.add_argument("--session", default=None, help="Shell session id (for name=shell).")
    p_exec.add_argument("--json", action="store_true", dest="as_json", help="Print JSON.")

    p_sess = sub.add_parser(
        "session",
        help="Open an ethics-gated shell session (five gates + ARC token).",
    )
    p_sess.add_argument("--actor", default="operator", help="Named actor (name is not a privilege).")
    p_sess.add_argument("--token", default=None, help="Existing ARC token. If omitted, gates run.")
    p_sess.add_argument("--json", action="store_true", dest="as_json", help="Print JSON.")

    p_sh = sub.add_parser(
        "shell",
        help="Ethics-coded remote shell. REPL, or -c COMMAND. Principle-bound.",
    )
    p_sh.add_argument("-c", "--command", default=None, help="Run one command and exit.")
    p_sh.add_argument("--actor", default="operator", help="Named actor for a new session.")
    p_sh.add_argument("--token", default=None, help="Issued ARC token.")
    p_sh.add_argument("--session", default=None, help="Existing session id.")
    p_sh.add_argument("--json", action="store_true", dest="as_json", help="Print JSON (one-shot).")

    sub.add_parser("halt", help="Halt execution authority. Lumen keeps running.")

    p_purge = sub.add_parser(
        "purge",
        help="Delete the .azos session directory only. Never $HOME or OS files.",
    )
    p_purge.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Confirms deletion of .azos only.",
    )

    p_doc = sub.add_parser("doctor", help="Self-check. No network, no telemetry.")
    p_doc.add_argument("--json", action="store_true", dest="as_json", help="Print doctor results as JSON.")

    p_imp = sub.add_parser("import", help="Import a JSON document.")
    p_imp.add_argument("path")

    p_exp = sub.add_parser("export", help="Export a JSON document.")
    p_exp.add_argument("path")

    return parser


def _runtime() -> Runtime:
    return Runtime(root=Path.cwd())


def _ensure_shell_token(rt: Runtime, *, token: str | None, actor: str) -> str:
    if token:
        if not rt.arc.verify(token):
            raise AuthorizationError("unauthorized: token missing or revoked")
        return token
    if rt.arc.has_active():
        return token or ""
    result = rt.request(shell_proposal(actor))
    if not result.passed or not result.token:
        raise AuthorizationError("unauthorized: ethics gates refused the shell session")
    return result.token


def _print_shell_result(result: dict, *, as_json: bool) -> int:
    if as_json:
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
        return 0 if result.get("ok") else 1
    if result.get("stdout"):
        sys.stdout.write(str(result["stdout"]))
        if not str(result["stdout"]).endswith("\n"):
            sys.stdout.write("\n")
    if not result.get("ok"):
        sys.stderr.write((result.get("error") or "denied") + "\n")
        if result.get("invite"):
            sys.stderr.write(str(result["invite"]))
        return 1
    return 0


def _repl(rt: Runtime, *, session_id: str, token: str | None) -> int:
    sys.stdout.write(
        f"AZ-OS ethics-coded remote shell {__version__}\n"
        "Protocol: cli-stdin  Auth: ARC  Sandbox: session vfs\n"
        "Integrity precedes execution. Type help. Ctrl-D or exit to leave.\n"
    )
    while True:
        try:
            line = input("azos$ ")
        except EOFError:
            sys.stdout.write("\n")
            return 0
        except KeyboardInterrupt:
            sys.stdout.write("\n")
            return 0
        if not line.strip():
            continue
        try:
            result = rt.run_command(line, session_id=session_id, token=token or None)
        except AuthorizationError as exc:
            sys.stderr.write(f"{exc}\n")
            sys.stderr.write(invite_text())
            return 1
        except AzosError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        _print_shell_result(result, as_json=False)
        if result.get("closed") or result.get("halted"):
            return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.cmd == "version":
        sys.stdout.write(f"azos {__version__}\n")
        return 0

    if args.cmd == "invite":
        emit_invite(sys.stdout)
        return 0

    if args.cmd == "ui":
        serve(host=args.host, port=args.port, runtime=_runtime())
        return 0

    rt = _runtime()

    if args.cmd == "status":
        sys.stdout.write(json.dumps(rt.status(), indent=2) + "\n")
        return 0

    if args.cmd == "halt":
        sys.stdout.write(json.dumps(rt.halt(), indent=2) + "\n")
        return 0

    if args.cmd == "purge":
        if not args.confirm:
            sys.stderr.write("purge requires --confirm (deletes .azos only)\n")
            sys.stderr.write(invite_text())
            return 2
        try:
            out = rt.purge(confirm=True)
        except AzosError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        sys.stdout.write(json.dumps(out, indent=2) + "\n")
        return 0

    if args.cmd == "session":
        try:
            token = _ensure_shell_token(rt, token=args.token, actor=args.actor)
            opened = rt.open_session(token=token or None, actor=args.actor)
        except AuthorizationError as exc:
            sys.stderr.write(f"{exc}\n")
            sys.stderr.write(invite_text())
            return 1
        except AzosError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        sys.stdout.write(json.dumps(opened, indent=2) + "\n")
        return 0

    if args.cmd == "shell":
        try:
            token = _ensure_shell_token(rt, token=args.token, actor=args.actor)
            session_id = args.session
            if not session_id:
                opened = rt.open_session(token=token or None, actor=args.actor)
                session_id = str(opened["session"])
            if args.command:
                result = rt.run_command(
                    args.command, session_id=session_id, token=token or None
                )
                return _print_shell_result(result, as_json=args.as_json)
            return _repl(rt, session_id=session_id, token=token or None)
        except AuthorizationError as exc:
            sys.stderr.write(f"{exc}\n")
            sys.stderr.write(invite_text())
            return 1
        except AzosError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1

    if args.cmd == "exec":
        extra: dict = {}
        if args.rest:
            if args.name == "shell":
                extra["command"] = " ".join(args.rest)
            else:
                extra["message"] = " ".join(args.rest)
        if getattr(args, "session", None):
            extra["session"] = args.session
        try:
            result = rt.run(args.name, token=args.token, args=extra or None)
        except AuthorizationError as exc:
            sys.stderr.write(f"{exc}\n")
            sys.stderr.write(invite_text())
            return 1
        except AzosError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        sys.stdout.write(json.dumps(result, indent=2) + "\n")
        return 0

    if args.cmd == "doctor":
        from azos.doctor import run_doctor

        return run_doctor(as_json=getattr(args, "as_json", False))

    if args.cmd == "import":
        from azos.jsonio import import_json

        rec = import_json(args.path)
        sys.stdout.write(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        return 0

    if args.cmd == "export":
        from azos.jsonio import export_json

        rec = export_json(args.path)
        sys.stdout.write(json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        return 0

    parser.error(f"unknown command {args.cmd}")
    return 2
