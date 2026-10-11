"""BUILD-STAMP-1.0: /v1/health reports git_sha and version_id from env, null when unset."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_health_build_stamp_script() -> None:
    script = ROOT / "workers" / "download-tracker" / "scripts" / "verify-build-stamp.mjs"
    completed = subprocess.run(["node", str(script)], check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert "test_worker_build_stamp: 7 passed" in completed.stdout
