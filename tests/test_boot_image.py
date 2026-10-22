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
    assert "AZOS-BOOT-SMOKE-PASS" in out.stdout and '"signed":false' in out.stdout and '"guardian":"absent"' in out.stdout


def test_init_keeps_bash_ssh_off_and_guardian_honest():
    init = (ROOT / "image/init").read_text()
    assert "guardian: ON" not in init and '\\"guardian\\":\\"on\\"' not in init
    assert "guardian: absent" in init and '\\"guardian\\":\\"absent\\"' in init
    assert "bash_host: OFF" in init and "ssh: OFF" in init
    assert "sshd" not in init and "dropbear" not in init


def test_no_shell_escape_in_init():
    init = (ROOT / "image/init").read_text()
    assert "azos.shell" not in init and "/proc/cmdline" not in init
    code = [l.split("#", 1)[0] for l in init.splitlines()[1:]]
    assert not any("exec sh" in l or "exec /bin/sh" in l or "setsid" in l or "getty" in l for l in code)


def test_image_sha256_covers_whole_initramfs():
    build = (ROOT / "scripts/build-image.sh").read_text()
    assert "sha256sum image/init" not in build
    assert "find . -type f ! -path ./etc/azos-image-sha256" in build
