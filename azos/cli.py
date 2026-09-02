"""Command-line interface for AZ-OS + AZ Interface.

    azos version
    azos ui                 # 127.0.0.1:8800  THE product
    azos status
    azos invite             # prints voluntary adoption text + download URL
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
from azos.interface import DEFAULT_HOST, DEFAULT_PORT, serve
from azos.invite import emit_invite, invite_text
from azos.runtime import Runtime


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="azos",
        description=(
            "AZ-OS + AZ Interface — ethical overlay framework "
            "(Aziel Eliab, 2026). Integrity precedes execution. "
            "Not a kernel, not malware. Propagation is invitation. "
            "Control surface: `azos ui` at http://127.0.0.1:8800."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="Print package version.")
    sub.add_parser("status", help="Overlay, Lumen, token, and log status.")
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
        help="Run a registered safe builtin (list_modules, echo, status, purge_session). Requires a live ARC token.",
    )
    p_exec.add_argument("name", help="Builtin name.")
    p_exec.add_argument(
        "rest",
        nargs="*",
        help="Optional echo message words. Never passed to a shell.",
    )
    p_exec.add_argument(
        "--token",
        default=None,
        help="Issued ARC token (hex). If omitted, a live session token must already exist.",
    )
    p_exec.add_argument("--json", action="store_true", dest="as_json", help="Print JSON.")

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

    if args.cmd == "exec":
        extra: dict = {}
        if args.rest:
            extra["message"] = " ".join(args.rest)
        try:
            result = rt.run(args.name, token=args.token, args=extra or None)
        except AuthorizationError as exc:
            sys.stderr.write(f"{exc}\n")
            sys.stderr.write(invite_text())
            return 1
        except AzosError as exc:
            sys.stderr.write(f"{exc}\n")
            return 1
        if args.as_json:
            sys.stdout.write(json.dumps(result, indent=2) + "\n")
        else:
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
