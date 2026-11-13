#!/usr/bin/env bash
# AZOS-BOOT-SMOKE-1.0: boot build/azos-boot under qemu-system-x86_64 -nographic and require the
# sealed AZOS-BOOT-1 line on the serial console. Passing proves "boots in QEMU" only, not hardware.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=build/azos-boot; LOG="$OUT/serial.log"
command -v qemu-system-x86_64 >/dev/null || { echo "AZOS-BOOT-SMOKE-SKIP: no qemu-system-x86_64"; exit 3; }
ACCEL=tcg; [ -w /dev/kvm ] && ACCEL=kvm
timeout "${AZOS_BOOT_TIMEOUT:-180}" qemu-system-x86_64 -machine accel=$ACCEL -m 256 -nographic -no-reboot \
  -kernel "$OUT/vmlinuz" -initrd "$OUT/initramfs.cpio.gz" -append "console=ttyS0 panic=-1 quiet" > "$LOG" 2>&1 || true
LINE=$(grep -a -m1 "^AZOS-BOOT-1 sealed=" "$LOG" | tr -d '\r' || true)
[ -n "$LINE" ] || { echo "AZOS-BOOT-SMOKE-FAIL: no AZOS-BOOT-1 line"; tail -20 "$LOG"; exit 1; }
H=${LINE#AZOS-BOOT-1 sealed=}; H=${H%% *}; BODY=${LINE#AZOS-BOOT-1 sealed=$H }
[ "$(printf '%s' "$BODY" | sha256sum | cut -d' ' -f1)" = "$H" ] || { echo "AZOS-BOOT-SMOKE-FAIL: seal mismatch"; exit 1; }
grep -aq "AZOS guardian: absent" "$LOG" || { echo "AZOS-BOOT-SMOKE-FAIL: guardian line missing"; exit 1; }
case "$BODY" in *'"guardian":"absent"'*) ;; *) echo "AZOS-BOOT-SMOKE-FAIL: guardian not sealed absent"; exit 1;; esac
grep -aq "AZOS handoff: updater OFF (no operator signing key) kernel_swap: absent userspace: absent" "$LOG" || { echo "AZOS-BOOT-SMOKE-FAIL: handoff line missing"; exit 1; }
case "$BODY" in *'"updater":"OFF"'*) ;; *) echo "AZOS-BOOT-SMOKE-FAIL: updater not sealed OFF"; exit 1;; esac
case "$BODY" in *'"kernel_swap":false'*) ;; *) echo "AZOS-BOOT-SMOKE-FAIL: kernel_swap not sealed false"; exit 1;; esac
case "$BODY" in *'"handoff":"absent"'*) ;; *) echo "AZOS-BOOT-SMOKE-FAIL: handoff not sealed absent"; exit 1;; esac
case "$BODY" in *'"userspace":"absent"'*) ;; *) echo "AZOS-BOOT-SMOKE-FAIL: userspace not sealed absent"; exit 1;; esac
case "$BODY" in *'"updater":"on"'*|*'"updater":true'*|*'"kernel_swap":true'*|*'"booted":true'*|*'"live":true'*) echo "AZOS-BOOT-SMOKE-FAIL: boot line claims a live updater or a kernel swap"; exit 1;; esac
# Recompute image_sha256 over the whole unpacked initramfs on the host and compare with the sealed value.
X=$(mktemp -d); trap 'rm -rf "$X"' EXIT
( cd "$X" && gzip -dc "$OLDPWD/$OUT/initramfs.cpio.gz" | cpio -id --quiet 2>/dev/null )
WANT=$(scripts/image-manifest.sh "$X")
case "$BODY" in *"\"image_sha256\":\"$WANT\""*) ;; *) echo "AZOS-BOOT-SMOKE-FAIL: image_sha256 != whole-initramfs hash $WANT"; exit 1;; esac
echo "AZOS-BOOT-SMOKE-PASS (QEMU $ACCEL) $LINE"
