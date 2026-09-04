# AZ-OS + AZ Interface

A **prefab ethics-coded remote shell**: all Aziel catalog software hooked in,
Windows-style desktop (Ever Blooming sigil, no words), TemporalLock ×
StaticClock integrity lattice.

**Author:** Aziel Eliab
**Date:** July–September 2026
**License:** [Apache-2.0](LICENSE)

> Integrity precedes execution.

**Counted download:** [https://azos-download-tracker.vibelock.workers.dev/](https://azos-download-tracker.vibelock.workers.dev/)

**Forks are welcome and always allowed.**

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
azos ui
# or
azos shell --actor operator
```


## One-click install

```bash
curl -fsSL https://azos-download-tracker.vibelock.workers.dev/install.sh | bash
```

The script curls the **counted** tarball from this project's Worker
(`/download`, User-Agent `Mozilla/5.0`), extracts, makes a venv, and
`pip install -e .`. Then run `azos ui` or `azos shell`.

Or tap **Download** / **One-click install** on the Worker homepage:
https://azos-download-tracker.vibelock.workers.dev/

## Counted download (Cloudflare Worker)

**This is the counted download.** GitHub releases exist as a mirror.
The Worker serves the gzip itself (HTTP 200, no 302 to GitHub).

- Homepage: [https://azos-download-tracker.vibelock.workers.dev/](https://azos-download-tracker.vibelock.workers.dev/)
- Direct tarball: [azos-0.3.0.tar.gz](https://azos-download-tracker.vibelock.workers.dev/download?asset=azos-0.3.0.tar.gz)
- One-click install: [https://azos-download-tracker.vibelock.workers.dev/install.sh](https://azos-download-tracker.vibelock.workers.dev/install.sh)
- Skill: [https://azos-download-tracker.vibelock.workers.dev/v1/skill](https://azos-download-tracker.vibelock.workers.dev/v1/skill)
- OpenAPI: [https://azos-download-tracker.vibelock.workers.dev/openapi.json](https://azos-download-tracker.vibelock.workers.dev/openapi.json)
- GitHub: [https://github.com/AzielEliab/azos](https://github.com/AzielEliab/azos)
- Zenodo DOI: [10.5281/zenodo.21431711](https://doi.org/10.5281/zenodo.21431711) · [record](https://zenodo.org/records/21431711)

Isolated counter: Worker `azos-download-tracker`, KV `AZOS_DOWNLOADS`. `/v1` does not increment downloads.

Open http://127.0.0.1:8800 — **AZ Interface is the control surface.** Loopback only. No CDN, no telemetry.

Counted download: [https://azos-download-tracker.vibelock.workers.dev/](https://azos-download-tracker.vibelock.workers.dev/)



See the combined papers: [docs/whitepaper.md](docs/whitepaper.md).
How to contribute: [CONTRIBUTING.md](CONTRIBUTING.md).

---

## What this is

AZ-OS is a **prefab true remote shell**. Every catalog product (FoldLock,
TemporalLock, StaticClock, ShadowLock, VeilLock, VibeLock, SpectralLock,
MirageGrid, AZAI/JEEVES, GodLock client hooks, and the rest) ships as an
**installed desktop app**. The Interface is a Windows-identical shell
whose Start glyph is the Ever Blooming sigil (gold rose + five-point
star + circle + foliage swirls — **no words**).

Every session and command is bound to the five coded ethics principles.
**AZ Interface** (`azos ui`) is the local control surface on
`127.0.0.1:8800`. Hosted `/v1/session` + `/v1/exec` is the same shell
over HTTPS JSON. TemporalLock timeslates are hash-chained against
StaticClock gear-clicks. No rollbacks.

### Honest scope

| Layer | What it is |
|-------|------------|
| **Protocols** | HTTPS JSON (Worker), HTTP loopback `127.0.0.1:8800`, CLI stdin (`azos shell`) |
| **Auth** | ARC 32-byte token issued only after the five ethics gates PASS. Hashed at rest. A `root`/`user` string is a name, not a privilege. |
| **Sandbox** | Session vfs: local `.azos/workspace/<id>/`, hosted KV vfs. Closed verb list. No host subprocess, no `eval`, no SSH, no raw TCP. |
| **Halt** | Stops overlay / session authority. Lumen keeps custody. Does not kill the caller OS. |

It is **not**:

- a kernel, bootloader, or hypervisor
- a replacement OS
- malware, a worm, or ransomware
- unrestricted host bash or SSH
- a silent block on unauthorized environments

Unauthorized environments receive an **invite** to run AZ-OS themselves.
Propagation is invitation, not infection. `azos invite` prints the
principles and a download URL. It does not copy itself onto other machines.

---

## Principles (enforced in code)

1. **Integrity precedes execution.** No module, session, or command runs without a token from ARC.
2. **Time-bound actions are final.** Authorized executions append to an immutable sha256 chain. No rewrite.
3. **Understanding precedes modification.** Extending or loading a new module requires an explicit comprehension checkbox and a short restatement of intent in the UI.
4. **The system protects itself architecturally.** Unsigned or unauthorized `run()` raises `AuthorizationError`. Default is deny.
5. **Propagation is not infection.** Invite only. No self-replication.

The five gates (definition, evidence, impact, integrity, responsibility)
are the executable form of those principles. Opening a session requires
all five. Every subsequent command is re-gated. A live session is
evidence, not a bypass.

---

## Runtime

| Module | Role |
|--------|------|
| `azos.prefab` | Catalog products as installed desktop apps. |
| `azos.lattice` | TemporalLock timeslates × StaticClock gear-clicks. No rollbacks. |
| `azos.ethics` | Coded principles, scope, registered shell verbs. |
| `azos.arc` | Issue / revoke execution tokens (32 random bytes, hashed at rest). A root/user string does not auto-grant. |
| `azos.lumen` | In-process watch loop. After halt, still revokes tokens and purges `.azos/` only. |
| `azos.gate` | Five-gate check for proposals **and** commands. FAIL → no token / no command. |
| `azos.shell` | Ethics-coded remote shell: session + sandboxed vfs + principle-bound verbs. |
| `azos.exec` | Registered safe builtins: `list_modules`, `echo`, `status`, `purge_session`, `shell`. |
| `azos.log` | Append-only hash chain of executions. |
| `azos.interface` | AZ Interface — the product. |
| `azos.cli` | Command line. |

Session state lives in `.azos/` (tokens hashed, log, halt flag, workspace).
Purge deletes that directory only — never `$HOME`, never OS files.

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
azos session --actor NAME
azos shell              # ethics-coded REPL (gates + ARC, then azos$)
azos shell -c 'ls'
azos exec NAME          # only if a token is active
azos halt
azos purge --confirm    # deletes .azos session only
```

Safe builtins for `azos exec`: `list_modules`, `echo`, `status`,
`purge_session`, `shell`.

Registered shell verbs: `help`, `pwd`, `ls`, `cat`, `write`, `echo`,
`mkdir`, `rm`, `cd`, `status`, `principles`, `invite`, `modules`,
`history`, `whoami`, `session`, `halt`, `exit`, `id`, `uname`.
Denied verbs (`bash`, `ssh`, `curl`, …) fail the integrity gate.

---

## AZ Interface

```bash
azos ui
```

Binds **127.0.0.1:8800**. Self-contained CSS. No CDN.

- Home explains the ethics-coded remote shell (protocols, auth, sandbox).
- Request-execution form → five-gate result → token issued or blocked.
- Open a shell session; type commands. Each line is re-gated.
- Action buttons enable only with a live token.
- Halt. Lumen status stays **running** after halt.
- Purge requires typed `CONFIRM`.
- Invite card (not a silent error).

---


## iPhone & Android

Flutter sources: [`mobile/`](mobile/). Application id `com.azieeliab.azos`. Offline. No analytics. Dark matte / gold.

Control surface: invite, halt, revoke labels. Integrity precedes execution.

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

## Download tracker

A live-count Cloudflare Worker lives at `workers/download-tracker/`.
Isolated counter for **azos** only. Hosted `/v1` is the ethics-coded
remote shell (session + exec) and does not increment downloads.

Public URL:

`https://azos-download-tracker.vibelock.workers.dev/`

---

## Layout

```
azos/               library (ethics, arc, gate, shell, exec, log, lumen, interface, cli)
tests/              pytest
docs/whitepaper.md  combined papers
mobile/             Flutter iPhone + Android (`flutter create .`)
workers/download-tracker/   Cloudflare Worker + counted tarball
```

## Malware comparison (constraints, not code)

AZ-OS is compared to malware **structurally** in the whitepaper: default
deny, no self-replication, no stealth, no disk wipe, invite instead of
infection. This repository does **not** implement malware, ransomware,
or host-disk wipes. The remote shell is ethics-gated and sandboxed.

## Use with Grok, ChatGPT, Venice

Live HTTPS runtime on the download-tracker Worker (does **not** increment the download counter):

- OpenAPI 3.1: https://azos-download-tracker.vibelock.workers.dev/openapi.json
- Health: https://azos-download-tracker.vibelock.workers.dev/v1/health
- How to wire tools: https://azos-download-tracker.vibelock.workers.dev/ai
- MCP catalog: https://aziel-runtime.vibelock.workers.dev/mcp

POST `/v1/status` (read-only), `/v1/invite`, `/v1/session`, `/v1/exec`,
`/v1/close`, `/v1/halt`, `/v1/revoke`. Motto: Integrity precedes execution.
Hosted halt is a token in the JSON, not killing the caller OS.

**ChatGPT Actions:** GPT Editor → Actions → Import from URL → `https://azos-download-tracker.vibelock.workers.dev/openapi.json` (no auth).

**Grok / xAI tools:** add an HTTP/OpenAPI tool pointing at `https://azos-download-tracker.vibelock.workers.dev/openapi.json`.

**Venice HTTP tools:** add an HTTP tool with method, URL, and JSON body from that spec. Start with GET `https://azos-download-tracker.vibelock.workers.dev/v1/health`.

```bash
curl -sS -A 'Mozilla/5.0' -X POST https://azos-download-tracker.vibelock.workers.dev/v1/session \
  -H 'content-type: application/json' \
  -d '{"actor":"operator","definition":"Open an ethics-gated shell session.","evidence":"Operator requested a principle-bound remote shell.","impact":"Hosted KV vfs only. No host subprocess."}'
```

GET `/download` still serves the gzip tarball and is counted.
