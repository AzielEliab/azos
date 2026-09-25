"""Command-line interface for AZ-OS.

Human text is the default. ``--json`` prints the same records a program
already received from these commands.
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

WELCOME = """\
AZ-OS runs registered commands in a session folder on this machine, after an ethics check.

Open the local app, then choose Open shell.

  azos ui
  azos shell
  azos doctor
  azos --help

Author: Aziel Eliab
"""

HELP = """\
azos — ethics-gated shell

Usage:
  azos
  azos <command> [options]

Commands run in a session folder named .azos in the current directory.

Start here:
  ui        Open http://127.0.0.1:8800/
  shell     Type commands in a session
  status    Show whether the shell is ready
  doctor    Check this install

Advanced:
  session   Open a session and print its id
  exec      Run one registered builtin
  halt      Stop new commands (the watch stays on)
  purge     Delete the .azos folder (needs --confirm)
  invite    Print the adoption text and download URL
  import    Read a JSON file into .azos-state.json
  export    Write .azos-state.json to a file
  version   Print the package version

Add --json to status, doctor, session, exec, halt, purge, import,
or export for the machine-readable record. azos --json prints status.

Examples:
  azos
  azos ui
  azos shell
  azos doctor
  azos status --json

Author: Aziel Eliab
"""


class AzosParser(argparse.ArgumentParser):
    """Parser that explains a mistake and a next step."""

    command_name: str | None = None

    def error(self, message: str) -> None:
        sys.stderr.write(_plain_error(self.command_name, message) + "\n")
        self.exit(2)


def _plain_error(command: str | None, message: str) -> str:
    marker = "invalid choice: '"
    if marker in message:
        name = message.split(marker, 1)[1].split("'", 1)[0]
        return f'Unknown command "{name}". Try: azos ui   or   azos --help'
    if "the following arguments are required" in message:
        if command == "exec":
            return (
                "azos exec needs a builtin name. "
                "Try: azos exec echo hello   or   azos --help"
            )
        if command == "import":
            return (
                "azos import needs a file path. "
                "Try: azos import request.json   or   azos --help"
            )
        if command == "export":
            return (
                "azos export needs a file path. "
                "Try: azos export azos-state.json   or   azos --help"
            )
        hint = f"azos {command} --help" if command else "azos --help"
        return f"A required value is missing. Try: {hint}"
    if message.startswith("unrecognized arguments"):
        extra = message.split(":", 1)[-1].strip()
        return f"Unrecognized option {extra}. Try: azos --help"
    if "invalid int value" in message and command == "ui":
        return "The port needs to be a number. Try: azos ui --port 8800"
    if command:
        return f"{message}. Try: azos {command} --help"
    return f"{message}. Try: azos --help"


def _build_parser() -> AzosParser:
    parser = AzosParser(prog="azos", add_help=False)
    parser.format_help = lambda: HELP  # type: ignore[method-assign]
    sub = parser.add_subparsers(dest="cmd")

    def add(name: str, help_text: str) -> AzosParser:
        command = sub.add_parser(name, help=help_text)
        command.command_name = name
        return command

    add("version", "Print the package version.")
    add("status", "Show whether the shell is ready.")
    add("invite", "Print the adoption text and download URL. Writes no files.")

    p_ui = add("ui", "Open the local app at http://127.0.0.1:8800/.")
    p_ui.add_argument("--host", default=DEFAULT_HOST, help="Loopback host (default 127.0.0.1).")
    p_ui.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port (default 8800).")

    p_exec = add("exec", "Run one registered builtin. Needs a live token.")
    p_exec.add_argument("name", help="Builtin name (echo, status, list_modules, shell, purge_session).")
    p_exec.add_argument(
        "rest",
        nargs="*",
        help="Optional echo message or shell command words. Never passed to a host shell.",
    )
    p_exec.add_argument("--token", default=None, help="Issued token (hex).")
    p_exec.add_argument("--session", default=None, help="Shell session id (for name=shell).")

    p_sess = add("session", "Open a session and print its id.")
    p_sess.add_argument("--actor", default="operator", help="Name for this session (default operator).")
    p_sess.add_argument("--token", default=None, help="Existing token. If omitted, the ethics check runs.")

    p_sh = add("shell", "Type commands in a session, or pass -c COMMAND.")
    p_sh.add_argument("-c", "--command", default=None, help="Run one command and exit.")
    p_sh.add_argument("--actor", default="operator", help="Name for a new session (default operator).")
    p_sh.add_argument("--token", default=None, help="Issued token.")
    p_sh.add_argument("--session", default=None, help="Existing session id.")

    add("halt", "Stop new commands. The watch stays on.")

    p_purge = add("purge", "Delete the .azos folder in this directory. Needs --confirm.")
    p_purge.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Confirms deletion of .azos only.",
    )

    add("doctor", "Check this install. No network.")

    p_imp = add("import", "Read a JSON file into .azos-state.json.")
    p_imp.add_argument("path")

    p_exp = add("export", "Write .azos-state.json to a file.")
    p_exp.add_argument("path")

    return parser


def _runtime() -> Runtime:
    return Runtime(root=Path.cwd())


def _emit(obj: object, *, as_json: bool, human: str) -> None:
    if as_json:
        sys.stdout.write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
        return
    sys.stdout.write(human if human.endswith("\n") else human + "\n")


def _watch_word(lumen: object) -> str:
    return "on" if lumen == "running" else "off"


def _human_status(st: dict) -> str:
    halted = bool(st.get("halted"))
    lumen = st.get("lumen")
    if halted and lumen == "running":
        state = "Halted — the watch is still on. New commands are refused."
    elif halted:
        state = "Halted. New commands are refused."
    elif lumen == "running":
        state = "Ready."
    else:
        state = "The watch is off."
    shell = st.get("shell") if isinstance(st.get("shell"), dict) else {}
    tokens = st.get("tokens") if isinstance(st.get("tokens"), dict) else {}
    version = st.get("version") or __version__
    return (
        f"AZ-OS {version}\n"
        "Author: Aziel Eliab\n"
        "\n"
        f"{state}\n"
        f"Watch: {_watch_word(lumen)}\n"
        f"Session folder: {st.get('session', '')}\n"
        f"Log entries: {st.get('log_length', 0)}\n"
        f"Active tokens: {tokens.get('active', 0)}\n"
        f"Open sessions: {shell.get('active', 0)}\n"
        "\n"
        "Next: azos ui    or    azos shell\n"
    )


def _human_halt(out: dict) -> str:
    return (
        "Halted. New commands are refused.\n"
        f"Watch: {_watch_word(out.get('lumen'))}\n"
        "\n"
        "Next: azos status    or    azos purge --confirm\n"
    )


def _human_purge(out: dict) -> str:
    removed = out.get("session") or ".azos"
    return (
        "Deleted the .azos folder in this directory.\n"
        f"Removed: {removed}\n"
        f"Watch: {_watch_word(out.get('lumen'))}\n"
    )


def _human_session(opened: dict) -> str:
    session = opened.get("session")
    lines = [
        "Session open.",
        f"Id: {session}",
        f"Actor: {opened.get('actor')}",
        f"Working directory: {opened.get('cwd')}",
    ]
    lattice = opened.get("lattice")
    if isinstance(lattice, dict) and lattice.get("ok"):
        lines.append("Recorded on the integrity lattice.")
    lines.append("")
    lines.append(f"Next: azos shell --session {session}")
    return "\n".join(lines) + "\n"


def _human_exec(name: str, result: dict) -> str:
    if name == "echo" and "echo" in result:
        return f"{result['echo']}\n"
    if name == "status" or ("overlay" in result and "lumen" in result and "shell" in result):
        return _human_status(result)
    if "modules" in result and isinstance(result.get("modules"), list):
        mods = ", ".join(str(item) for item in result["modules"])
        return f"Builtins: {mods}\n"
    if result.get("purged") is True:
        return _human_purge(result)
    if result.get("stdout") is not None:
        text = str(result.get("stdout") or "")
        if text and not text.endswith("\n"):
            text += "\n"
        if result.get("ok") is False:
            err = result.get("error") or "denied"
            return f"{text}{err}\nNext: azos shell -c help\n"
        return text or "Done.\n"
    if result.get("session") and name == "shell":
        return _human_session(result)
    lines = []
    for key, value in result.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            lines.append(f"{key}: {value}")
    if lines:
        return "\n".join(lines) + "\n"
    return "Done. Add --json for the full record.\n"


def _human_import(rec: dict) -> str:
    keys = rec.get("keys") or []
    listed = ", ".join(str(key) for key in keys) if keys else "(none)"
    return (
        f"Imported {rec.get('imported')}\n"
        f"Stored: {rec.get('stored')}\n"
        f"Keys: {listed}\n"
    )


def _human_export(rec: dict) -> str:
    return f"Wrote {rec.get('exported')}\n"


def _write_auth_error(exc: BaseException) -> None:
    sys.stderr.write(f"{exc}\n")
    if "halted" in str(exc).lower():
        sys.stderr.write("Next: azos status    or    azos purge --confirm\n")
    else:
        sys.stderr.write("Next: azos shell    or    azos ui\n")
    if getattr(exc, "invite", False):
        sys.stderr.write(invite_text())


def _write_error(exc: BaseException) -> None:
    sys.stderr.write(f"{exc}\nNext: azos --help\n")


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
        sys.stderr.write("Next: azos shell -c help    or    azos --help\n")
        if result.get("invite"):
            sys.stderr.write(str(result["invite"]))
        return 1
    return 0


def _repl(rt: Runtime, *, session_id: str, token: str | None) -> int:
    sys.stdout.write(
        f"AZ-OS {__version__}\n"
        "Integrity precedes execution.\n"
        "Session ready. Type help. Ctrl-D or exit to leave.\n"
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
            _write_auth_error(exc)
            return 1
        except AzosError as exc:
            _write_error(exc)
            return 1
        _print_shell_result(result, as_json=False)
        if result.get("closed") or result.get("halted"):
            return 0


def _default(as_json: bool) -> int:
    if not as_json:
        sys.stdout.write(WELCOME)
        return 0
    rt = _runtime()
    sys.stdout.write(json.dumps(rt.status(), indent=2) + "\n")
    return 0


def _exit_code(exc: SystemExit) -> int:
    code = exc.code
    if code is None or code == 0:
        return 0
    if isinstance(code, int):
        return code
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in raw
    args_list = [item for item in raw if item != "--json"]

    if not args_list:
        return _default(as_json)
    if args_list == ["-h"] or args_list == ["--help"] or args_list == ["help"]:
        sys.stdout.write(HELP)
        return 0

    parser = _build_parser()
    try:
        args = parser.parse_args(args_list)
    except SystemExit as exc:
        return _exit_code(exc)

    if args.cmd == "version":
        sys.stdout.write(f"azos {__version__}\nAuthor: Aziel Eliab\n")
        return 0

    if args.cmd == "invite":
        emit_invite(sys.stdout)
        return 0

    if args.cmd == "ui":
        try:
            serve(host=args.host, port=args.port, runtime=_runtime())
        except ValueError:
            sys.stderr.write(
                "AZ Interface listens on this machine only (127.0.0.1).\n"
                "Next: azos ui\n"
            )
            return 2
        except OSError as exc:
            if getattr(exc, "errno", None) in {98, 48, 10048}:
                sys.stderr.write(
                    f"Port {args.port} is already in use.\n"
                    f"Next: azos ui --port {int(args.port) + 1}\n"
                )
            else:
                detail = exc.strerror or str(exc)
                sys.stderr.write(
                    f"Could not start the local app ({detail}).\n"
                    "Next: azos ui --help\n"
                )
            return 1
        return 0

    rt = _runtime()

    if args.cmd == "status":
        status = rt.status()
        _emit(status, as_json=as_json, human=_human_status(status))
        return 0

    if args.cmd == "halt":
        out = rt.halt()
        _emit(out, as_json=as_json, human=_human_halt(out))
        return 0

    if args.cmd == "purge":
        if not args.confirm:
            sys.stderr.write(
                "Purge needs --confirm. That deletes the .azos folder in this directory only.\n"
                "Next: azos purge --confirm\n"
            )
            sys.stderr.write(invite_text())
            return 2
        try:
            out = rt.purge(confirm=True)
        except AzosError as exc:
            _write_error(exc)
            return 1
        _emit(out, as_json=as_json, human=_human_purge(out))
        return 0

    if args.cmd == "session":
        try:
            token = _ensure_shell_token(rt, token=args.token, actor=args.actor)
            opened = rt.open_session(token=token or None, actor=args.actor)
        except AuthorizationError as exc:
            _write_auth_error(exc)
            return 1
        except AzosError as exc:
            _write_error(exc)
            return 1
        _emit(opened, as_json=as_json, human=_human_session(opened))
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
                return _print_shell_result(result, as_json=as_json)
            return _repl(rt, session_id=session_id, token=token or None)
        except AuthorizationError as exc:
            _write_auth_error(exc)
            return 1
        except AzosError as exc:
            _write_error(exc)
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
            _write_auth_error(exc)
            return 1
        except AzosError as exc:
            _write_error(exc)
            return 1
        _emit(result, as_json=as_json, human=_human_exec(args.name, result))
        return 0

    if args.cmd == "doctor":
        from azos.doctor import run_doctor

        return run_doctor(as_json=as_json)

    if args.cmd == "import":
        from azos.jsonio import import_json

        try:
            rec = import_json(args.path)
        except FileNotFoundError:
            sys.stderr.write(
                f'No file at "{args.path}". Next: azos import path/to/file.json\n'
            )
            return 1
        except json.JSONDecodeError:
            sys.stderr.write(
                "That file is not a JSON object. Next: azos import path/to/file.json\n"
            )
            return 1
        except ValueError as exc:
            sys.stderr.write(f"{exc}\nNext: azos import path/to/file.json\n")
            return 1
        except OSError as exc:
            detail = exc.strerror or str(exc)
            sys.stderr.write(
                f"Could not read {args.path} ({detail}). Next: azos import path/to/file.json\n"
            )
            return 1
        _emit(rec, as_json=as_json, human=_human_import(rec))
        return 0

    if args.cmd == "export":
        from azos.jsonio import export_json

        try:
            rec = export_json(args.path)
        except OSError as exc:
            detail = exc.strerror or str(exc)
            sys.stderr.write(
                f"Could not write {args.path} ({detail}). Next: azos export azos-state.json\n"
            )
            return 1
        _emit(rec, as_json=as_json, human=_human_export(rec))
        return 0

    sys.stderr.write(f'Unknown command "{args.cmd}". Try: azos ui   or   azos --help\n')
    return 2
