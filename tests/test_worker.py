"""Worker source: live count, isolated to azos, product homepage."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "workers" / "download-tracker" / "src" / "index.js"
HP = ROOT / "workers" / "download-tracker" / "src" / "homepage.js"
RT = ROOT / "workers" / "download-tracker" / "src" / "runtime.js"
TOML = ROOT / "workers" / "download-tracker" / "wrangler.toml"


def test_worker_live_count_and_isolation() -> None:
    js = JS.read_text(encoding="utf-8")
    hp = HP.read_text(encoding="utf-8")
    toml = TOML.read_text(encoding="utf-8")
    assert 'PROJECT = "azos"' in js
    assert "await collectStats" in js or "collectStats(env)" in js
    assert "/count" in js
    assert "project" in js and "total" in js
    assert "not VibeLock" in js or "not the VibeLock" in js or "Not VibeLock" in hp
    assert "isolated" in js.lower() or "Isolated" in hp
    assert 'href="/download?asset=' in hp
    assert "live downloads" in hp.lower() or "live download" in hp.lower()
    assert "Integrity precedes execution" in hp
    assert "azos-0.3.0.tar.gz" in hp
    assert "ethics-coded remote shell" in hp.lower() or "coded ethics" in hp.lower()
    assert "AzielEliab/azos" in js or "AzielEliab/azos" in hp
    homepage = hp
    assert "POST /event" not in homepage
    assert "/event" not in homepage
    assert "DOWNLOADS" in toml
    assert 'name = "azos-download-tracker"' in toml
    assert "ac575a9b822bea2bed97d0ab73aed238" in toml
    assert '"/count"' in toml


def test_worker_homepage_is_product_ui() -> None:
    hp = HP.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    assert "AZ-OS — Aziel Eliab" in hp
    assert "application/ld+json" in hp
    assert "SoftwareApplication" in hp
    assert "cite.json" in hp
    assert "id=\"workspace\"" in hp or 'id="workspace"' in hp
    assert "not a VPN" in hp or "AZ-OS is not a VPN" in hp
    assert "not a kernel" in hp.lower()
    assert "Apache-2.0" in hp
    assert "Forks welcome" in hp
    assert "sigil.svg" in hp
    assert "One-click install" in hp
    assert "10.5281" not in hp
    assert "doi.org" not in hp.lower()
    assert "doi: null" in hp
    assert "full AZ-OS" in hp
    assert "HTTP proxy is not the full OS" in hp
    assert "/v1/status" in hp
    assert "/v1/invite" in hp
    assert "/v1/prefab" in hp
    assert "/v1/lattice" in hp
    assert "THE EVER BLOOMING FLOWER" not in hp.upper()


def test_worker_cite_has_no_invented_doi() -> None:
    js = JS.read_text(encoding="utf-8")
    hp = HP.read_text(encoding="utf-8")
    rt = RT.read_text(encoding="utf-8")
    assert "citeDocument" in js
    assert "doi: null" in hp
    assert "10.5281" not in js
    assert "21431711" not in js
    assert "21431711" not in hp
    assert "21431711" not in rt
    assert "doi.org" not in js.lower()


def test_worker_serves_sigil() -> None:
    js = JS.read_text(encoding="utf-8")
    hp = HP.read_text(encoding="utf-8")
    toml = TOML.read_text(encoding="utf-8")
    assert "/sigil.svg" in js
    assert "function sigilSvg" in hp
    assert "<svg" in hp
    sigil_fn = hp.split("export function sigilSvg")[1].split("function breakdownList")[0]
    assert "<svg" in sigil_fn
    assert "<text" not in sigil_fn.lower()
    assert '"/sigil.svg"' in toml


def test_worker_runtime_exposes_ethics_shell() -> None:
    runtime = RT.read_text(encoding="utf-8")
    assert "ethics_coded_remote_shell" in runtime
    assert "/v1/session" in runtime
    assert "/v1/exec" in runtime
    assert "does not grant remote shell" not in runtime.lower()
    assert 'VERSION = "0.3.0"' in runtime
    assert "/v1/prefab" in runtime
    assert "/v1/lattice" in runtime
    assert "Aziel Eliab" in runtime


def test_worker_kv_binding_present() -> None:
    toml = TOML.read_text(encoding="utf-8")
    assert 'binding = "DOWNLOADS"' in toml
    assert "816b8d5da5fd470f9c4e783f3c87ca77" in toml
