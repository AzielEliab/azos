# Contributing to AZ-OS + AZ Interface

**Forks are first-class.** This project is Apache-2.0; you do not need
permission to fork, patch, or redistribute.

**Forks are welcome and always allowed.**

## How to run tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

Python 3.10+. Core is stdlib only (`hashlib`, `secrets`, `json`,
`http.server`, `threading`, `shlex`). pytest is the dev extra. No network.

## Ground rules

1. **Overlay, not a kernel.** Do not add a bootloader, hypervisor, kernel,
   scheduler, or anything that replaces a host OS.
2. **Not malware.** Do not add self-replication, worm-like copy, stealth,
   ransomware, or any routine that wipes host disks. `purge` deletes
   `.azos/` only.
3. **Integrity precedes execution.** No new action or command runs without
   an ARC token issued after the five gates pass. Every shell command is
   re-gated. Default deny.
4. **Ethics-coded shell, not host bash.** `azos.shell` is a session vfs
   with a closed verb list. No `eval`, no host `subprocess`, no SSH, no
   raw TCP. Do not add a spawn path.
5. **Append-only log.** Do not add rewrite, pop, or edit of the execution chain.
6. **Invite, not infection.** `azos invite` prints text. It must not copy
   the overlay onto other machines.
7. **UI binds loopback only** (`127.0.0.1`). Do not listen on `0.0.0.0`.
   Self-contained CSS. No CDN.
8. **Lumen survives halt.** Halt stops execution authority; revoke and
   purge of `.azos/` remain available.
9. Keep the dependency list empty in the core. Stdlib only.
10. New behavior needs a test that fails without the change.
11. Stay honest about scope: protocols, auth, sandbox.

## Where to change things

- Coded ethics / scope: `azos/ethics.py`
- Tokens: `azos/arc.py`
- Five gates (proposals + commands): `azos/gate.py`
- Shell session + vfs: `azos/shell.py`
- Builtins: `azos/exec.py` (`SAFE_ACTIONS`)
- Hash chain: `azos/log.py`
- Halt / purge: `azos/lumen.py`
- Control surface: `azos/interface.py`, `azos/templates/ui.html`
- CLI: `azos/cli.py`
- Prefab catalog apps: `azos/prefab.py`
- Integrity lattice: `azos/lattice.py`
- Hosted shell: `workers/download-tracker/src/runtime.js`
- Sigil / brand mark (no words): `azos/templates/sigil.svg`
