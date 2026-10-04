"""Worker source: live count, isolated to azos, product homepage."""

from __future__ import annotations

import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "workers" / "download-tracker" / "src" / "index.js"
HP = ROOT / "workers" / "download-tracker" / "src" / "homepage.js"
RT = ROOT / "workers" / "download-tracker" / "src" / "runtime.js"
NM = ROOT / "workers" / "download-tracker" / "src" / "newsmap.js"
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
    assert "sigil.png" in hp
    assert 'class="brandrow"' in hp
    assert 'class="brandmark"' in hp
    assert 'src="/sigil.png"' in hp
    assert 'alt=""' in hp
    assert "everblooming sigil" not in hp.lower()
    assert "everbloom" not in hp.lower()
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
    assert 'id="news-map"' in hp
    assert "azos.news_source" in hp
    assert "does not install 4DMap" in hp
    assert "THE EVER BLOOMING FLOWER" not in hp.upper()
    assert "Claude (Anthropic)" in hp
    assert "other MCP/OpenAPI-capable assistants" in hp
    assert 'id="meshStrip"' in hp
    assert "Live Nodes" in hp


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
    png = ROOT / "workers" / "download-tracker" / "public" / "sigil.png"
    data = png.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    assert 60_000 <= len(data) <= 90_000
    assert 'class="brandrow"' in hp
    assert '<div class="brandrow"><img class="brandmark" src="/sigil.png" width="40" height="40" alt="" decoding="async"></div>' in hp
    assert "everbloom" not in hp.lower()
    assert "everblooming sigil" not in js.lower()
    assert 'X-Aziel-Sigil": "Everblooming"' in js
    assert "/sigil.png" in js
    assert "function serveSigilPng" in js
    assert "/sigil.svg" in js
    assert "function sigilSvg" in hp
    assert "<svg" in hp
    sigil_fn = hp.split("export function sigilSvg")[1].split("function breakdownList")[0]
    assert "<svg" in sigil_fn
    assert "<text" not in sigil_fn.lower()
    assert '"/sigil.png"' in toml
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
    assert "/v1/newsmap" in runtime
    assert "joinStatus(null)" in runtime
    newsmap = NM.read_text(encoding="utf-8")
    assert "AZNEWS-SOURCE-ABSENT" in newsmap
    assert "runtime_done: false" in newsmap
    assert "one_click_install_live: false" in runtime
    assert "mesh_node_live: false" in runtime
    assert "mail_live: false" in newsmap
    assert "internet_live: false" in newsmap
    assert "kernel_live: false" in newsmap
    assert "kernel_base: false" in runtime
    assert "booted: false" in runtime
    assert "os_yet: false" in runtime
    assert "userspace_base: true" in runtime
    assert "alt_internet_live: false" in runtime
    assert "mail_send: false" in runtime
    prefab_slugs = runtime.split("const slugs = [", 1)[1].split("];", 1)[0]
    assert "4dmap" not in prefab_slugs
    assert "aznews" not in prefab_slugs
    assert "Aziel Eliab" in runtime
    assert "Use with AI assistants" in runtime
    assert "Use with Grok, ChatGPT, Venice" not in runtime
    assert "Claude (Anthropic)" in runtime
    assert "Cursor (MCP)" in runtime
    assert "other MCP/OpenAPI-capable assistants" in runtime
    assert "/v1/mesh" in runtime
    assert "meshPointer" in runtime


def test_join_flag_script_rejects_a_live_label() -> None:
    import subprocess

    script = ROOT / "workers" / "download-tracker" / "scripts" / "verify-join-flags.mjs"
    completed = subprocess.run(
        ["node", str(script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "join flags ok" in completed.stdout


def test_worker_kv_binding_present() -> None:
    toml = TOML.read_text(encoding="utf-8")
    assert 'binding = "DOWNLOADS"' in toml
    assert "816b8d5da5fd470f9c4e783f3c87ca77" in toml


def test_counted_tarball_includes_offline_node_client() -> None:
    """public/azos-0.3.0.tar.gz is the counted sdist and must match this tree.

    The Worker skill points operators at this gzip for the local package.
    That package includes the AZnet offline node client (azos/node.py).
    """
    archive = ROOT / "workers" / "download-tracker" / "public" / "azos-0.3.0.tar.gz"
    prefix = "azos-0.3.0/"
    generated = {"PKG-INFO", "setup.cfg"}
    required = (
        "azos/node.py",
        "azos/cli.py",
        "azos/doctor.py",
        "azos/runtime.py",
        "azos/interface.py",
        "tests/test_node.py",
        "SKILL.md",
        "README.md",
        "docs/whitepaper.md",
        "CONTRIBUTING.md",
    )
    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())
        for rel in required:
            member = prefix + rel
            assert member in names
            assert tar.extractfile(member).read() == (ROOT / rel).read_bytes()
        for member in tar.getmembers():
            if not member.isfile():
                continue
            rel = member.name.removeprefix(prefix)
            if rel.startswith("azos.egg-info/") or rel in generated:
                continue
            assert (ROOT / rel).is_file()
            assert tar.extractfile(member).read() == (ROOT / rel).read_bytes()
        node = tar.extractfile(prefix + "azos/node.py").read().decode("utf-8")
        sources = tar.extractfile(prefix + "azos.egg-info/SOURCES.txt").read().decode("utf-8")
    assert 'CLIENT = "offline-node"' in node
    assert 'SIDENET = "aznet"' in node
    assert "This package does not include it." in node
    assert 'softwares_desk' in node
    assert "azos/node.py" in sources
    assert "tests/test_node.py" in sources
    assert not any("softwares" in name.lower() for name in names)
