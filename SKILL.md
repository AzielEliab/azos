---
name: AZ-OS
description: Use when calling AZ-OS hosted /v1 or installing the local package. Author Aziel Eliab.
---

# AZ-OS

Integrity precedes execution. Author: **Aziel Eliab**.

**THIS IS:** a portable ethical overlay and local control surface (AZ Interface).

**THIS IS NOT:** a kernel, bootloader, hypervisor, worm, or malware. Hosted `/v1` does not increment downloads or views.

Always send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.

## Call these URLs

- Worker OpenAPI: https://azos-download-tracker.vibelock.workers.dev/openapi.json
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`
- Live skill (this markdown): `GET https://azos-download-tracker.vibelock.workers.dev/v1/skill`

Ops (do **not** increment downloads or views):

- `GET /v1/health` — liveness
- `GET /v1/skill` — this file
- Product POSTs listed in OpenAPI

Grok: import OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Example

```bash
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/skill
```

## Local (after one-click install)

```bash
curl -fsSL https://azos-download-tracker.vibelock.workers.dev/install.sh | bash
azos ui
azos doctor
```

Then open http://127.0.0.1:8800 (loopback only).

Counted download (gzip HTTP 200, no 302): https://azos-download-tracker.vibelock.workers.dev/download?asset=azos-0.1.0.tar.gz
GitHub: https://github.com/AzielEliab/azos

Paper: DOI https://doi.org/10.5281/zenodo.21431711 · https://zenodo.org/records/21431711 · Apache-2.0. Forks welcome.
