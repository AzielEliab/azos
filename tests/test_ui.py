"""AZ Interface: GET / 200 contains AZ-OS and Interface; loopback; no CDN."""

from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from azos.interface import make_handler, make_server
from azos.runtime import Runtime


def test_html_is_self_contained() -> None:
    html = (
        Path(__file__).resolve().parents[1] / "azos" / "templates" / "ui.html"
    ).read_text(encoding="utf-8")
    assert "AZ-OS" in html
    assert "Interface" in html
    assert "<style>" in html
    assert "cdn" not in html.lower()
    assert "CONFIRM" in html
    assert "Lumen" in html
    assert "invite" in html.lower()
    assert "overlay" in html.lower() or "remote shell" in html.lower()
    assert "azos$" in html
    assert "/api/shell" in html
    assert "Open shell" in html
    assert "Advanced" in html
    assert "prefers-color-scheme" in html
    assert ":focus-visible" in html
    assert "/sigil.svg" in html
    assert "THE EVER BLOOMING FLOWER" not in html.upper()
    assert "windows logo" not in html.lower()


def test_ui_get_root_contains_azos_and_interface(tmp_path: Path) -> None:
    rt = Runtime(root=tmp_path)
    handler = make_handler(rt)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    host, port = httpd.server_address[:2]
    assert host == "127.0.0.1"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", "/")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        assert resp.status == 200
        assert "AZ-OS" in body
        assert "Interface" in body
        conn.request("GET", "/api/status")
        status = conn.getresponse()
        payload = json.loads(status.read().decode("utf-8"))
        assert status.status == 200
        assert payload["lumen"] == "running"
        assert payload["overlay"] == "AZ-OS"
        conn.request("GET", "/sigil.svg")
        sig = conn.getresponse()
        svg = sig.read().decode("utf-8")
        assert sig.status == 200
        assert "<svg" in svg
        assert "EVER BLOOMING" not in svg.upper()
        assert "<text" not in svg.lower()
        conn.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        rt.lumen.stop()


def test_ui_refuses_non_loopback() -> None:
    with pytest.raises(ValueError):
        make_server(host="0.0.0.0", port=0)


def test_ui_json_accept_returns_status(tmp_path: Path) -> None:
    rt = Runtime(root=tmp_path)
    handler = make_handler(rt)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
        conn.request("GET", "/", headers={"Accept": "application/json"})
        resp = conn.getresponse()
        payload = json.loads(resp.read().decode("utf-8"))
        assert resp.status == 200
        assert payload["overlay"] == "AZ-OS"
        assert payload["lumen"] == "running"
        conn.request("GET", "/", headers={"Accept": "text/html,application/json"})
        page = conn.getresponse()
        body = page.read().decode("utf-8")
        assert page.status == 200
        assert body.lstrip().startswith("<!doctype html>")
        conn.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        rt.lumen.stop()


def test_ui_request_token_then_exec_and_invite_on_fail(tmp_path: Path) -> None:
    rt = Runtime(root=tmp_path)
    handler = make_handler(rt)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
        # FAIL → invite, not a silent block
        conn.request(
            "POST",
            "/api/request",
            body=json.dumps({"action": "echo"}),
            headers={"Content-Type": "application/json"},
        )
        denied = conn.getresponse()
        denied_body = json.loads(denied.read().decode("utf-8"))
        assert denied.status == 403
        assert denied_body["passed"] is False
        assert denied_body["token"] is None
        assert "Integrity precedes execution" in denied_body["invite"]

        payload = {
            "action": "echo",
            "definition": "Print a bounded status string from a registered builtin.",
            "evidence": "Action is on the closed SAFE_ACTIONS list in azos.exec.",
            "impact": "In-process result only. No host disk, no other machines.",
            "actor": "tester",
        }
        conn.request(
            "POST",
            "/api/request",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        ok = conn.getresponse()
        issued = json.loads(ok.read().decode("utf-8"))
        assert ok.status == 200
        assert issued["passed"] is True
        token = issued["token"]
        assert token

        conn.request(
            "POST",
            "/api/exec",
            body=json.dumps({"name": "echo", "token": token, "message": "from-ui"}),
            headers={"Content-Type": "application/json"},
        )
        ran = conn.getresponse()
        ran_body = json.loads(ran.read().decode("utf-8"))
        assert ran.status == 200
        assert ran_body["ok"] is True
        assert ran_body["result"]["echo"] == "from-ui"

        conn.request("POST", "/api/halt", body="{}", headers={"Content-Type": "application/json"})
        halted = json.loads(conn.getresponse().read().decode("utf-8"))
        assert halted["halted"] is True
        assert halted["lumen"] == "running"
        conn.close()
    finally:
        httpd.shutdown()
        httpd.server_close()
        rt.lumen.stop()
