"""AZRT-AZOS-TETHER-1.0: AZ-OS verifies and stores signed runtime lattice tips.

The runtime sends; this tracker verifies and stores. The runtime does not exec
into AZ-OS. Author: Aziel Eliab.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "download-tracker"


def test_runtime_tether_script_verifies_and_refuses() -> None:
    completed = subprocess.run(
        ["node", str(WORKER / "scripts" / "verify-tether.mjs")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert "ok azos tether" in completed.stdout


def test_runtime_tether_key_is_pinned_public_key() -> None:
    toml = (WORKER / "wrangler.toml").read_text(encoding="utf-8")
    assert "RUNTIME_TETHER_PUBKEY" in toml
    assert "TETHER_SIGNING_SEED" not in toml


def test_tether_code_does_not_exec() -> None:
    src = (WORKER / "src" / "tether.js").read_text(encoding="utf-8")
    assert "/v1/exec" not in src
    assert "AZIEL_RUNTIME.fetch" not in src
    assert "runtime_exec_into_azos: false" in src
