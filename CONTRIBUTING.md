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
`http.server`, `threading`). pytest is the dev extra. No network.

## Ground rules

1. **Overlay, not a kernel.** Do not add a bootloader, hypervisor, kernel,
   scheduler, or anything that replaces a host OS.
2. **Not malware.** Do not add self-replication, worm-like copy, stealth,
   ransomware, or any routine that wipes host disks. `purge` deletes
   `.azos/` only.
3. **Integrity precedes execution.** No new action runs without an ARC
   token issued after the five gates pass. Default deny.
4. **No eval / no subprocess / no shell** in `azos.exec`. Builtins are a
   closed allow-list.
5. **Append-only log.** Do not add rewrite, pop, or edit of the execution chain.
6. **Invite, not infection.** `azos invite` prints text. It must not copy
   the overlay onto other machines.
7. **UI binds loopback only** (`127.0.0.1`). Do not listen on `0.0.0.0`.
   Self-contained CSS. No CDN.
8. **Lumen survives halt.** Halt stops execution authority; revoke and
   purge of `.azos/` remain available.
9. Keep the dependency list empty in the core. Stdlib only.
10. New behavior needs a test that fails without the change.

## Where to change things

- Tokens: `azos/arc.py`
- Five gates: `azos/gate.py`
- Builtins: `azos/exec.py` (`SAFE_ACTIONS`)
- Hash chain: `azos/log.py`
- Halt / purge: `azos/lumen.py`
- Control surface: `azos/interface.py`, `azos/templates/ui.html`
- CLI: `azos/cli.py`
