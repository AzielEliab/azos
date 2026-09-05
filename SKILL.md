---
name: AZ-OS
description: Use when calling the AZ-OS ethics-coded remote shell (hosted /v1 or local package). Sessions and commands are principle-bound. Author Aziel Eliab.
---

# AZ-OS

Integrity precedes execution. Author: **Aziel Eliab**.

**THIS IS:** prefab AZ-OS — a true remote shell gated by coded ethics. Every catalog product ships as an installed app. Windows-style desktop; sigil / brand mark (rose + star, no words). TemporalLock × StaticClock integrity lattice. Every session and command is principle-bound.

**THIS IS NOT:** a kernel, bootloader, hypervisor, worm, malware, unrestricted host bash, or SSH. Hosted `/v1` does not increment downloads or views.

Always send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.

## Honest scope

| Layer | What it is |
|-------|------------|
| Protocols | HTTPS JSON (this Worker), HTTP loopback `127.0.0.1:8800` (AZ Interface), CLI stdin (`azos shell`) |
| Auth | ARC 32-byte token issued only after the five ethics gates PASS. Hashed at rest. |
| Sandbox | Session vfs (local `.azos/workspace/<id>/`, hosted KV vfs). Closed verb list. No host subprocess. |
| Halt | Stops overlay / session authority. Does not kill the caller OS. |

## Call these URLs

- Worker OpenAPI: https://azos-download-tracker.vibelock.workers.dev/openapi.json
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`
- Live skill (this markdown): `GET https://azos-download-tracker.vibelock.workers.dev/v1/skill`

Ops (do **not** increment downloads or views):

- `GET /v1/health` — liveness + scope
- `GET /v1/skill` — this file
- `POST /v1/status` — read-only status / principles (no exec)
- `POST /v1/session` — open an ethics-gated shell session
- `POST /v1/exec` — run one principle-bound command in that session
- `POST /v1/close` — close a session
- `GET /v1/prefab` — installed catalog apps
- `GET`/`POST /v1/lattice` — TemporalLock × StaticClock integrity lattice
- Product POSTs listed in OpenAPI (`invite`, `halt`, `revoke`)

Grok: import OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Example

```bash
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/skill
curl -s -A 'Mozilla/5.0' -X POST https://azos-download-tracker.vibelock.workers.dev/v1/session \
  -H 'content-type: application/json' \
  -d '{"actor":"operator","definition":"Open an ethics-gated shell session.","evidence":"Operator requested a principle-bound remote shell.","impact":"Hosted KV vfs only. No host subprocess."}'
```

## Local (after one-click install)

```bash
curl -fsSL https://azos-download-tracker.vibelock.workers.dev/install.sh | bash
azos ui
azos shell --actor operator -c 'help'
azos doctor
```

Then open http://127.0.0.1:8800 (loopback only).

Counted download (gzip HTTP 200, no 302): https://azos-download-tracker.vibelock.workers.dev/download?asset=azos-0.3.0.tar.gz
GitHub: https://github.com/AzielEliab/azos

License: Apache-2.0. Forks welcome. No Zenodo DOI is claimed.
