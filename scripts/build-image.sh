#!/usr/bin/env bash
# AZOS-BOOT-IMAGE-1.0: build a minimal x86_64 initramfs (static busybox + image/init) for QEMU.
# Usage: scripts/build-image.sh [KERNEL]   (default: newest /boot/vmlinuz-*)
# Needs: busybox (static), cpio, gzip. Output: build/azos-boot/{vmlinuz,initramfs.cpio.gz,SHA256SUMS}
set -euo pipefail
cd "$(dirname "$0")/.."
KERNEL="${1:-$(ls -1 /boot/vmlinuz-* 2>/dev/null | sort -V | tail -1)}"
BB="$(command -v busybox || true)"
[ -n "$KERNEL" ] && [ -r "$KERNEL" ] || { echo "AZOS-BOOT-NO-KERNEL: pass a readable vmlinuz" >&2; exit 2; }
[ -n "$BB" ] || { echo "AZOS-BOOT-NO-BUSYBOX: install busybox-static" >&2; exit 2; }
{ ldd "$BB" 2>&1 || true; } | grep -q "not a dynamic" || { echo "AZOS-BOOT-BUSYBOX-DYNAMIC: need a static busybox" >&2; exit 2; }
OUT=build/azos-boot; ROOT=$(mktemp -d)
trap 'rm -rf "$ROOT"' EXIT
mkdir -p "$OUT" "$ROOT"/{bin,proc,sys,dev,etc}
cp "$BB" "$ROOT/bin/busybox"; cp image/init "$ROOT/init"; chmod 755 "$ROOT/init" "$ROOT/bin/busybox"
# image_sha256 = whole-initramfs manifest hash (type, mode, path, content hash / link target); see image-manifest.sh.
scripts/image-manifest.sh "$ROOT" > "$ROOT/etc/azos-image-sha256"
cp "$ROOT/etc/azos-image-sha256" "$OUT/image_sha256"
( cd "$ROOT" && find . -print0 | LC_ALL=C sort -z | cpio --null -o -H newc --reproducible 2>/dev/null ) | gzip -9n > "$OUT/initramfs.cpio.gz"
cp "$KERNEL" "$OUT/vmlinuz"
( cd "$OUT" && sha256sum vmlinuz initramfs.cpio.gz > SHA256SUMS )
echo "built $OUT"; cat "$OUT/SHA256SUMS"
