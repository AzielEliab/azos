"""Hosted AZNews / 4DMap paths read the runtime 4DMap engine through FragGate.

Joined (/v1/newsmap, pin, open), AZNews standalone (/v1/aznews, ingest), and
4DMap standalone (/v1/map, plot, library_pin). Flags pass through and are never
raised by this Worker. Author: Aziel Eliab.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "download-tracker"


def test_newsmap_door_script() -> None:
    completed = subprocess.run(
        ["node", str(WORKER / "scripts" / "verify-newsmap-door.mjs")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert "NEWSMAP-DOOR-OK azos" in completed.stdout


def test_newsmap_door_keeps_install_flags_false() -> None:
    src = (WORKER / "src" / "newsmap-door.js").read_text(encoding="utf-8")
    assert "installed: false" in src
    assert "engine_installed: false" in src
    assert "second_map: false" in src
    assert 'name: "4dmap"' in src
