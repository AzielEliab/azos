"""KERNEL-FIELD-1.0: AZ-OS mesh views carry kernel=false; the mesh spec name is kernel_profile."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_mesh_kernel_is_boolean_false() -> None:
    script = ROOT / "workers" / "download-tracker" / "scripts" / "verify-mesh-kernel.mjs"
    done = subprocess.run(["node", str(script)], check=False, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "mesh kernel field: 6 passed" in done.stdout
