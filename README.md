# AZ-OS + AZ Interface

A **minimal ethical overlay framework** and its control surface.

**Author:** Aziel Eliab
**Date:** July–August 2026
**License:** [Apache-2.0](LICENSE)

> Integrity precedes execution.

**Counted download:** [https://azos-download-tracker.vibelock.workers.dev/](https://azos-download-tracker.vibelock.workers.dev/)

**Forks are welcome and always allowed.**

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
azos ui
```

Open http://127.0.0.1:8800 — **AZ Interface is the control surface.** Loopback only. No CDN, no telemetry. Not a kernel, not a worm.

Counted download: [https://azos-download-tracker.vibelock.workers.dev/](https://azos-download-tracker.vibelock.workers.dev/)



See the combined papers: [docs/whitepaper.md](docs/whitepaper.md).
How to contribute: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## What this is

AZ-OS is a **portable folder** — a soft overlay you run on top of an
operating system you already have. **AZ Interface** (`azos ui`) is the
product: a local control surface on `127.0.0.1:8800`.

It is **not**:

- a kernel, bootloader, or hypervisor
- a replacement OS
- malware, a worm, or ransomware
- a silent block on unauthorized environments

Unauthorized environments receive an **invite** to run AZ-OS themselves.
Propagation is invitation, not infection. `azos invite` prints the
principles and a download URL. It does not copy itself onto other machines.

---

## Principles (enforced in code)

1. **Integrity precedes execution.** No module or action runs without a token from ARC.
2. **Time-bound actions are final.** Authorized executions append to an immutable sha256 chain. No rewrite.
3. **Understanding precedes modification.** Extending or loading a new module requires an explicit comprehension checkbox and a short restatement of intent in the UI.
4. **The system protects itself architecturally.** Unsigned or unauthorized `run()` raises `AuthorizationError`. Default is deny.
5. **Propagation is not infection.** Invite only. No self-replication.

---

## Runtime

| Module | Role |
|--------|------|
| `azos.arc` | Issue / revoke execution tokens (32 random bytes, hashed at rest). A root/user string does not auto-grant. |
| `azos.lumen` | In-process watch loop. After halt, still revokes tokens and purges `.azos/` only. |
| `azos.gate` | Five-gate check: definition, evidence, impact, integrity, responsibility. FAIL → no token. |
| `azos.exec` | Registered safe builtins only: `list_modules`, `echo`, `status`, `purge_session`. No `eval()`, no subprocess, no shell. |
| `azos.log` | Append-only hash chain of executions. |
| `azos.interface` | AZ Interface — the product. |
| `azos.cli` | Command line. |

Session state lives in `.azos/` (tokens hashed, log, halt flag). Purge deletes that directory only — never `$HOME`, never OS files.

---

## Install

Python 3.10+. Stdlib only in the core.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## CLI

```bash
azos version
azos ui                 # 127.0.0.1:8800  THE product
azos status
azos invite             # principles + download URL (writes no files)
azos exec NAME          # only if a token is active
azos halt
azos purge --confirm    # deletes .azos session only
```

Safe builtins for `azos exec`: `list_modules`, `echo`, `status`, `purge_session`.

---

## AZ Interface

```bash
azos ui
```

Binds **127.0.0.1:8800**. Self-contained CSS. No CDN.

- Home explains the overlay (not a kernel).
- Request-execution form → five-gate result → token issued or blocked.
- Action buttons enable only with a live token.
- Halt. Lumen status stays **running** after halt.
- Purge requires typed `CONFIRM`.
- Invite card (not a silent error).

---


## iPhone & Android

Flutter sources: [`mobile/`](mobile/). Application id `com.azieeliab.azos`. Offline. No analytics. Dark matte / gold.

Control surface: invite, halt, revoke labels. Not a kernel or worm. Integrity precedes execution.

```bash
cd mobile
flutter create --org com.azieeliab --project-name azos .
flutter pub get
flutter run
```

The `android/` and `ios/` folders in this tree are skeleton READMEs until you run `flutter create .` (this machine has no Flutter SDK on PATH). Then open `android/` in Android Studio or `ios/Runner.xcworkspace` in Xcode. Not a store listing.

## Tests

```bash
python -m pytest -q
```

---

## Download tracker (undeployed)

A live-count Cloudflare Worker lives at `workers/download-tracker/`.
It is **not deployed** from this tree. KV id is the placeholder
`REPLACE_ME`. Isolated counter for **azos** only.

Intended public URL after a human deploys it:

`https://azos-download-tracker.vibelock.workers.dev/`

---

## Layout

```
azos/               library (arc, gate, exec, log, lumen, interface, cli)
tests/              pytest
docs/whitepaper.md  combined papers
mobile/             Flutter iPhone + Android (`flutter create .`)
workers/download-tracker/   Cloudflare Worker (undeployed)
```

## Malware comparison (constraints, not code)

AZ-OS is compared to malware **structurally** in the whitepaper: default
deny, no self-replication, no stealth, no disk wipe, invite instead of
infection. This repository does **not** implement malware, ransomware,
or host-disk wipes.
