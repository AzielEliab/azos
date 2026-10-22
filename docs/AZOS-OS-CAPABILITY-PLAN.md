# AZ-OS OS capability plan (one PR per capability)

Goal (Aziel): AZ-OS as a true ethical computing OS at the runtime, bootstrap and OS levels:
kernel, bootloader, hypervisor, operating system, VPN, host bash and SSH.
**Never malware, never worms.** The ethical guardian is always on and refuses unethical use.
FragGate stays the single door. Host bash and SSH stay **OFF by default** until verified.
Every action gets a sealed (not signed) receipt. Nothing is called live until code and tests prove it.

| # | Capability | PR | Proof required before any "works" claim | Status |
|---|---|---|---|---|
| 1 | Bootable image (kernel + initramfs, PID 1 init) | this PR | `scripts/boot-smoke.sh` sees a sealed `AZOS-BOOT-1` line on QEMU serial | **boots in QEMU** (tcg); not hardware |
| 2 | Bootloader (GRUB/limine ISO + UEFI) | next | ISO boots in QEMU BIOS and OVMF UEFI, same AZOS-BOOT-1 line | not built |
| 3 | OS userspace (AZ-OS Python as first service after PID 1, receipts to disk) | next | boot shows AZ-OS service up + first ChainLock-shaped receipt; parity vectors (azos #42) pass in-image | not built |
| 4 | Guardian in the boot path (refusal gate before any service) | next | in-image refusal tests: malware/worm/self-propagation requests refused with sealed refusal receipt | not built |
| 5 | Hypervisor (KVM guest launch via FragGate op, off by default) | later | nested QEMU/KVM guest boots and is receipted; refused when off | not built |
| 6 | VPN (WireGuard, off by default) | later | two-VM tunnel carries a packet; receipted | not built |
| 7 | SSH (dropbear/OpenSSH, key-only, off by default) | later | key-only login in QEMU after explicit enable; every session receipted | not built |
| 8 | Host bash (operator-only, off by default) | later | explicit enable + guardian check + per-command sealed receipt | not built |

Hard rules for every PR: no self-propagation, no scanning or exploitation of third-party hosts,
no persistence on machines the operator does not own, no hidden remote control. Pin and
locks (42/36/363, 2.0.0-rc1) are untouched by AZ-OS image work.
