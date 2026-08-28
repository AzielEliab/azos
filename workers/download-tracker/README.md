# AZ-OS download tracker (Cloudflare Worker)

Counts GitHub-release downloads for AZ-OS across the canonical
repository, other branches, and forks. Forks are identified by GitHub
`owner/repo`.

**This worker must not be deployed from this tree** until the KV
namespace id in `wrangler.toml` is a real id. It is the placeholder
`REPLACE_ME`.

Intended public URL after a human deploys it:

`https://azos-download-tracker.vibelock.workers.dev/`

Until then, send people to
[GitHub Releases](https://github.com/AzielEliab/azos/releases).

No secrets belong in this directory.

Integrity precedes execution. Isolated counter: this Worker and its KV
only. Not mixed with VibeLock or any other *Lock.

## Bindings

| Binding     | Type | Purpose |
|-------------|------|---------|
| `DOWNLOADS` | KV   | Counters keyed `project|owner|repo|branch|fork` |

## Deploy (human; not from this agent)

```bash
cd workers/download-tracker
npx wrangler login
npx wrangler kv namespace create DOWNLOADS
# paste the id into wrangler.toml replacing REPLACE_ME
npx wrangler deploy
```

Do not deploy from this tree until KV is a real id.

## Routes

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/` | Index page with live download count |
| GET | `/count` | JSON `{project, total}` for THIS project only |
| GET | `/download?repo=&tag=&asset=` | Increment KV, 302 to the hosted asset |
| GET | `/stats` | JSON totals plus per-repo and per-branch breakdown |
| POST | `/event` | A fork reports a download |

Default asset: `azos-0.1.0.tar.gz`. Canonical repo: `AzielEliab/azos`.

## Use with Grok, ChatGPT, Venice

This Worker also hosts the product runtime API (CORS `*`). `/v1` routes do **not** increment `DOWNLOADS`.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/v1/health` | Liveness |
| GET | `/openapi.json` | OpenAPI 3.1 |
| GET | `/ai` | ChatGPT Actions, Grok/xAI tools, Venice HTTP tools; MCP catalog |

See the product README section **Use with Grok, ChatGPT, Venice**.
OpenAPI: https://azos-download-tracker.vibelock.workers.dev/openapi.json
