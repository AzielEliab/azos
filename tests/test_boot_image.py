"""AZOS-BOOT-1: build the initramfs and boot it in QEMU. Skips (never passes) when tools are absent."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HAVE = shutil.which("qemu-system-x86_64") and shutil.which("busybox") and shutil.which("cpio") and list(Path("/boot").glob("vmlinuz-*"))


@pytest.mark.skipif(not HAVE, reason="needs qemu-system-x86_64, static busybox, cpio and a /boot/vmlinuz")
def test_boots_in_qemu_and_seals_receipt():
    subprocess.run([str(ROOT / "scripts/build-image.sh")], check=True, cwd=ROOT)
    out = subprocess.run([str(ROOT / "scripts/boot-smoke.sh")], capture_output=True, text=True, cwd=ROOT, timeout=300)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "AZOS-BOOT-SMOKE-PASS" in out.stdout and '"signed":false' in out.stdout and '"guardian":"on"' in out.stdout


def test_init_keeps_bash_ssh_off_and_guardian_on():
    init = (ROOT / "image/init").read_text()
    assert "guardian: ON" in init and "bash_host: OFF" in init and "ssh: OFF" in init
    assert "sshd" not in init and "dropbear" not in init
