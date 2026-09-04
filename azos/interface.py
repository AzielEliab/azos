"""AZ Interface — the control surface. Bind 127.0.0.1:8800.

Not cosmetic. Request → five gates → token or invite. Ethics-coded
shell session. Action buttons only enable with a live token. Halt.
Purge with typed CONFIRM. Lumen status stays running after halt.
Self-contained CSS, no CDN.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import urlparse

from azos.gate import Proposal
from azos.invite import invite_text
from azos.runtime import Runtime

LOOPBACK = frozenset({"127.0.0.1", "localhost", "::1"})
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8800
WEB = files("azos") / "templates"


def _html_bytes() -> bytes:
    return (WEB / "ui.html").read_bytes()


def make_handler(runtime: Runtime):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AZ-Interface/0.3.0"

        def log_message(self, fmt: str, *args: object) -> None:
            return

        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj: object) -> None:
            body = json.dumps(obj, indent=2, ensure_ascii=False).encode("utf-8")
            self._send(status, body, "application/json; charset=utf-8")

        def _read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                return {}
            return payload if isinstance(payload, dict) else {}

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path in {"/", "/index.html"}:
                self._send(200, _html_bytes(), "text/html; charset=utf-8")
                return
            if path in {"/sigil.svg", "/brand/sigil.svg"}:
                self._send(200, (WEB / "sigil.svg").read_bytes(), "image/svg+xml")
                return
            if path == "/api/status":
                self._json(200, runtime.status())
                return
            if path == "/api/prefab":
                from azos.prefab import prefab_snapshot

                self._json(200, prefab_snapshot())
                return
            if path == "/api/lattice":
                self._json(200, runtime.lattice.snapshot())
                return
            if path == "/api/invite":
                self._json(200, {"invite": invite_text()})
                return
            if path == "/api/log":
                entries = [e.to_dict() for e in runtime.log.entries()]
                self._json(200, {"entries": entries, "length": len(entries)})
                return
            self._json(404, {"error": "not found", "invite": invite_text()})

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            payload = self._read_json()

            if path == "/api/request":
                proposal = Proposal(
                    action=str(payload.get("action") or ""),
                    definition=str(payload.get("definition") or ""),
                    evidence=str(payload.get("evidence") or ""),
                    impact=str(payload.get("impact") or ""),
                    actor=str(payload.get("actor") or ""),
                    extend_module=bool(payload.get("extend_module")),
                    comprehension=bool(payload.get("comprehension")),
                    intent=str(payload.get("intent") or ""),
                )
                result = runtime.request(proposal)
                self._json(200 if result.passed else 403, result.as_dict())
                return

            if path == "/api/exec":
                name = str(payload.get("name") or payload.get("action") or "")
                token = payload.get("token")
                token_s = str(token) if token else None
                args = payload.get("args") if isinstance(payload.get("args"), dict) else {}
                if "message" in payload and "message" not in args:
                    args = dict(args)
                    args["message"] = payload.get("message")
                try:
                    out = runtime.run(name, token=token_s, args=args)
                except Exception as exc:
                    self._json(
                        403,
                        {
                            "ok": False,
                            "error": str(exc),
                            "invite": invite_text(),
                        },
                    )
                    return
                self._json(200, {"ok": True, "result": out})
                return

            if path == "/api/session":
                token = payload.get("token")
                token_s = str(token) if token else None
                actor = str(payload.get("actor") or "operator")
                try:
                    opened = runtime.open_session(token=token_s, actor=actor)
                except Exception as exc:
                    self._json(
                        403,
                        {"ok": False, "error": str(exc), "invite": invite_text()},
                    )
                    return
                self._json(200, {"ok": True, **opened})
                return

            if path == "/api/shell":
                token = payload.get("token")
                token_s = str(token) if token else None
                session_id = str(payload.get("session") or payload.get("session_id") or "")
                command = str(payload.get("command") or payload.get("line") or "")
                if not session_id:
                    self._json(
                        400,
                        {"ok": False, "error": "session id required", "invite": invite_text()},
                    )
                    return
                try:
                    out = runtime.run_command(command, session_id=session_id, token=token_s)
                except Exception as exc:
                    self._json(
                        403,
                        {"ok": False, "error": str(exc), "invite": invite_text()},
                    )
                    return
                self._json(200 if out.get("ok") else 403, out)
                return

            if path == "/api/close":
                token = payload.get("token")
                token_s = str(token) if token else None
                session_id = str(payload.get("session") or payload.get("session_id") or "")
                try:
                    out = runtime.shell.close(session_id, token=token_s)
                except Exception as exc:
                    self._json(
                        403,
                        {"ok": False, "error": str(exc), "invite": invite_text()},
                    )
                    return
                self._json(200, out)
                return

            if path == "/api/halt":
                self._json(200, runtime.halt())
                return

            if path == "/api/revoke":
                token = str(payload.get("token") or "")
                try:
                    runtime.lumen.revoke(token)
                except Exception as exc:
                    self._json(403, {"ok": False, "error": str(exc), "invite": invite_text()})
                    return
                self._json(200, {"ok": True, "revoked": True})
                return

            if path == "/api/purge":
                typed = str(payload.get("confirm") or "")
                ok = typed == "CONFIRM" or payload.get("confirm") is True
                if not ok:
                    self._json(
                        400,
                        {
                            "ok": False,
                            "error": "type CONFIRM to purge the .azos session",
                            "invite": invite_text(),
                        },
                    )
                    return
                try:
                    out = runtime.purge(confirm=True)
                except Exception as exc:
                    self._json(400, {"ok": False, "error": str(exc)})
                    return
                self._json(200, out)
                return

            self._json(404, {"error": "not found", "invite": invite_text()})

    return Handler


def make_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    runtime: Runtime | None = None,
) -> ThreadingHTTPServer:
    if host not in LOOPBACK:
        raise ValueError("AZ Interface binds loopback only (127.0.0.1)")
    rt = runtime if runtime is not None else Runtime()
    handler = make_handler(rt)
    return ThreadingHTTPServer((host, port), handler)


def serve(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    runtime: Runtime | None = None,
) -> None:
    httpd = make_server(host, port, runtime)
    bound_host, bound_port = httpd.server_address[:2]
    print(
        f"AZ Interface http://{bound_host}:{bound_port}  "
        "(prefab Windows-style shell; Ever Blooming sigil; loopback only)"
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
