---
name: AZ-OS
description: Use when calling the AZ-OS ethics-coded remote shell (hosted /v1 or local package). Dual surface: Worker /v1 + catalog MCP. This Worker /v1/mesh/* PROXY to aziel-runtime via AZIEL_RUNTIME. Suite mesh default OFF. QNM-BUILD-1.0 live|locked|isolated. QNS-CD-1.0 photon QNS1 hub cite (qnm-node qnsd; no public proxy). No Node Gate. No auto-heal. Not anonymity. Sessions and commands are principle-bound. Author Aziel Eliab.
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
- Suite mesh: `GET https://azos-download-tracker.vibelock.workers.dev/v1/mesh` (PROXY; default OFF; QNS-CD-1.0 hub cite)

Ops (do **not** increment downloads or views):

- `GET /v1/health` — liveness + scope
- `GET /v1/skill` — this file
- `GET /v1/mesh` — PROXY suite mesh status. Default OFF. QNM live|locked|isolated. QNS-CD-1.0 photon QNS1 hub cite (local qnsd in qnm-node; runtime cites in aziel-runtime). Never enables. No public qnsd proxy.
- `GET /v1/mesh/nodes` — PROXY Live Nodes roster (5-minute presence). Payload includes the QNS-CD-1.0 cross-map.
- `POST /v1/mesh/{enable,disable,join,heartbeat,leave,broadcast}` — PROXY. Bearer required to enable. No auto-heal. Anon-broadcast is not a publish path.
- `POST /v1/status` — read-only status / principles (no exec)
- `POST /v1/session` — open an ethics-gated shell session
- `POST /v1/exec` — run one principle-bound command in that session
- `POST /v1/close` — close a session
- `GET /v1/prefab` — installed catalog apps
- `GET`/`POST /v1/lattice` — TemporalLock × StaticClock integrity lattice
- `GET /v1/newsmap` — joined AZNews and 4DMap probe. Standalone paths exist in the local package. 4DMap is not installed. No news source. Not live. This repo does not claim the aziel-runtime side is done.
- Product POSTs listed in OpenAPI (`invite`, `halt`, `revoke`)

Works with ChatGPT (GPT Actions / OpenAI), Grok (xAI), Venice, Claude (Anthropic), Cursor (MCP), Glama (MCP), Perplexity, Microsoft Copilot / Bing, Google Gemini / Vertex, Mistral, Meta AI, Apple Intelligence surfaces, Amazon Q tooling, DuckAssist, You.com, Cohere, and other MCP/OpenAPI-capable assistants. Import OpenAPI as a custom tool, use GPT Actions, HTTP tools, or MCP. Catalog MCP `mesh_*` + FragGate `slug=mesh`. Suite mesh default OFF. QNM-BUILD-1.0 live|locked|isolated. QNS-CD-1.0 photon QNS1 hub cite (qnm-node qnsd; no public proxy). No Node Gate. No auto-heal. Not anonymity. Author: Aziel Eliab only.

## Example

```bash
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/skill
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/mesh
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

## Offline node client (local package)

AZnet is the sidenet. **AZ Browser** is the browser surface for AZnet. `azos node` is a local hash client for that sidenet. It is not the hosted AZNet engine, it does not include AZ Browser, and it does not add a Softwares desk card. The AZ-OS layers stay `base`, `stacked`, and `standalone`.

| Layer | Need |
|---|---|
| `base` | Host OS stays the host OS. Local garden under `.azos/node/`. |
| `stacked` | Same garden. L0 FragGate HTTPS remains the online door. |
| `standalone` | Same garden. No shell session. Desk unchanged. |

```bash
azos node status
azos node stamp --text hello --layer standalone
azos node probe
```

`stamp` stores a sha256 ref and does not store the text. `probe` is `GET /v1/health` only. It does not call a FragGate op. When the machine is online, FragGate HTTPS at `https://aziel-runtime.vibelock.workers.dev/v1/fraggate/call` is still the door.

## News and the map

AZNews and 4DMap each have a standalone path, and they share a joined path. AZNews can list cited outlets, record weather gaps, and chain a cited tail-event catalog without opening the map. 4DMap can pin a cited tail event without a news article. On the joined path, AZ-OS points at the runtime 4DMap engine (`slug=4dmap`, ops `news_pin` and `news_open`). A news item can become a map pin (date, event, and place), or a pin can open the matching news. This is not a second app and not a copy of the engine. This package does not claim the aziel-runtime side is done. 4DMap is not marked installed. `azos.news_source` can GET a standing feed. That feed has no score and no place, so the news source stays absent and AZNews and 4DMap stay not joined until a complete fetched item lands. A fixture is not that item and does not flip the live flag. The userspace base is present. That is a base, not a boot. The kernel base is absent. This has not booted. This is not installed as an operating system. Internet base is present. Not live. The packet path is not live. The packet path does not run. The alternative internet is not live. An alternative internet does not run. Device-to-device packet carriers stay NOT-READY. WARN-5 stands. The path sentence names what is still missing. Mail is not sent from here. One-click install is not live. This is not a live mesh node. A process receipt, a loopback bind, and a userspace file are not a host kernel. AZ Interface is a separate shell. It is not this kernel and not this boot. `azos news`, `azos map`, and the local page at http://127.0.0.1:8800/ say this in plain language.

Counted download (gzip HTTP 200, no 302): https://azos-download-tracker.vibelock.workers.dev/download?asset=azos-0.3.0.tar.gz
GitHub: https://github.com/AzielEliab/azos

License: Apache-2.0. Forks welcome. No Zenodo DOI is claimed.
