# AZ-OS

AZ-OS runs registered commands in a session folder on this machine, after an ethics check.

**Author:** Aziel Eliab  
**License:** [Apache-2.0](LICENSE)

## Start

1. Install (Python 3.10+):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

2. Start the local app:

```bash
azos ui
```

3. Open http://127.0.0.1:8800/ and choose **Open shell**.

`azos doctor` checks this install. `azos --help` lists commands. Add `--json` when a program needs the machine record (`azos status --json`).

## One-click install

```bash
curl -fsSL https://azos-download-tracker.vibelock.workers.dev/install.sh | bash
azos ui
```

The script downloads the counted tarball (User-Agent `Mozilla/5.0`), extracts it, and installs. Then open http://127.0.0.1:8800/ and choose **Open shell**.

## Commands

Start here:

| Command | What it does |
|---|---|
| `azos` | Welcome and the next commands |
| `azos ui` | Local app at http://127.0.0.1:8800/ (this machine only) |
| `azos shell` | Session prompt. `azos shell -c 'ls'` runs one command |
| `azos status` | Ready or halted, watch, session folder |
| `azos doctor` | Local self-check |

Advanced (same command names as before):

| Command | What it does |
|---|---|
| `azos session --actor NAME` | Open a session and print its id |
| `azos exec NAME` | One registered builtin, with a live token |
| `azos halt` | Stop new commands. The watch stays on |
| `azos purge --confirm` | Delete the `.azos` folder in this directory |
| `azos invite` | Adoption text and download URL. Writes no files |
| `azos import FILE` | Read JSON into `.azos-state.json` |
| `azos export FILE` | Write `.azos-state.json` |
| `azos version` | Package version |

`--json` on `status`, `doctor`, `session`, `exec`, `halt`, `purge`, `import`, and `export` prints the machine record. `azos --json` prints status.

Builtins for `azos exec`: `list_modules`, `echo`, `status`, `purge_session`, `shell`.

Shell commands: `help`, `pwd`, `ls`, `cat`, `write`, `echo`, `mkdir`, `rm`, `cd`, `status`, `principles`, `invite`, `modules`, `history`, `whoami`, `session`, `halt`, `exit`, `id`, `uname`.

## Local app

`azos ui` prints `Open http://127.0.0.1:8800/` and serves AZ Interface on that address.

The first screen has one primary action, **Open shell**. Help sits beside it. Halt, purge, the ethics form, catalog hooks, the lattice, and the log are under **Advanced**. Light and dark follow the system. Keyboard focus uses a gold ring. The layout fits a narrow phone width.

A program can send `Accept: application/json` on `GET /` for the status record. Other `/api/` routes are unchanged.

## Notes

Integrity precedes execution.

This package is a prefab of catalog hooks, including TemporalLock timeslates chained to StaticClock. The local program is the ethics-gated remote shell. There is no kernel in this repository, and there is no malware routine.

| Layer | What it does |
|---|---|
| Protocols | HTTPS JSON on the Worker, HTTP on `127.0.0.1:8800`, and CLI stdin (`azos shell`) |
| Auth | A token is issued only after five checks pass: definition, evidence, impact, integrity, responsibility. The token is hashed at rest. A name is not a privilege. |
| Sandbox | Session folder: local `.azos/workspace/<id>/`. Closed command list. |
| Halt | Stops new commands. The watch (Lumen) stays on and can still revoke a token or purge `.azos`. |
| Purge | Deletes the `.azos` folder in this directory only. |

Principles, as enforced in code:

1. Integrity precedes execution.
2. Time-bound actions are final.
3. Understanding precedes modification.
4. The system protects itself architecturally.
5. Propagation is not infection.

`azos invite` prints those principles and a download URL. It does not copy this program onto another machine.

Session state lives in `.azos/` (hashed tokens, log, halt flag, workspace).

Counted download: https://azos-download-tracker.vibelock.workers.dev/

- Tarball: https://azos-download-tracker.vibelock.workers.dev/download?asset=azos-0.3.0.tar.gz
- Install script: https://azos-download-tracker.vibelock.workers.dev/install.sh
- OpenAPI: https://azos-download-tracker.vibelock.workers.dev/openapi.json
- GitHub: https://github.com/AzielEliab/azos

No Zenodo DOI is claimed. `/v1` on the Worker does not increment downloads.

Suite mesh: https://azos-download-tracker.vibelock.workers.dev/v1/mesh — read-only proxy, default off. QNS-CD-1.0 is a cite. GET does not enable it.

Papers: [docs/whitepaper.md](docs/whitepaper.md). Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).

### Programs

Import `https://azos-download-tracker.vibelock.workers.dev/openapi.json`. Health: `GET /v1/health`. Local status for a program: `azos status --json`.

```bash
curl -sS -A 'Mozilla/5.0' -X POST https://azos-download-tracker.vibelock.workers.dev/v1/session \
  -H 'content-type: application/json' \
  -d '{"actor":"operator","definition":"Open an ethics-gated shell session.","evidence":"Operator requested a principle-bound remote shell.","impact":"Hosted KV vfs only. No host subprocess."}'
```

### Phone sources

Flutter sources are in [`mobile/`](mobile/). Application id `com.azieeliab.azos`. The `android/` and `ios/` folders are skeleton notes until `flutter create .` is run.

### Tests

```bash
pip install -e ".[dev]"
python -m pytest -q
```

### Layout

```
azos/               library and local app
tests/              pytest
docs/whitepaper.md  papers
mobile/             Flutter sources
workers/download-tracker/   counted download Worker
```
