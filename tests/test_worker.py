"""Worker source: live count, isolated to azos, KV REPLACE_ME, undeployed."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "workers" / "download-tracker" / "src" / "index.js"
TOML = ROOT / "workers" / "download-tracker" / "wrangler.toml"


def test_worker_live_count_and_isolation() -> None:
    js = JS.read_text(encoding="utf-8")
    toml = TOML.read_text(encoding="utf-8")
    assert 'PROJECT = "azos"' in js
    assert "await collectStats" in js or "collectStats(env)" in js
    assert "/count" in js
    assert "project" in js and "total" in js
    assert "not VibeLock" in js or "not the VibeLock" in js
    assert "isolated" in js.lower()
    assert 'href="/download?asset=' in js
    assert "live downloads" in js.lower() or "live download" in js.lower()
    assert "Integrity precedes execution" in js
    assert "azos-0.2.0.tar.gz" in js
    assert "ethics-coded remote shell" in js.lower() or "coded ethics" in js.lower()
    assert "AzielEliab/azos" in js
    homepage = js.split("function indexHtml")[1].split("export default")[0]
    assert "POST /event" not in homepage
    assert "/event" not in homepage
    assert "DOWNLOADS" in toml
    assert 'name = "azos-download-tracker"' in toml
    assert "ac575a9b822bea2bed97d0ab73aed238" in toml
    assert '"/count"' in toml


def test_worker_runtime_exposes_ethics_shell() -> None:
    runtime = (ROOT / "workers" / "download-tracker" / "src" / "runtime.js").read_text(
        encoding="utf-8"
    )
    assert "ethics_coded_remote_shell" in runtime
    assert "/v1/session" in runtime
    assert "/v1/exec" in runtime
    assert "does not grant remote shell" not in runtime.lower()
    assert "VERSION = \"0.2.0\"" in runtime
    assert "Aziel Eliab" in runtime


def test_worker_kv_binding_present() -> None:
    toml = TOML.read_text(encoding="utf-8")
    assert 'binding = "DOWNLOADS"' in toml
    assert "816b8d5da5fd470f9c4e783f3c87ca77" in toml
