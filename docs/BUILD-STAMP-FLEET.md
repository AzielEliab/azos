# BUILD-STAMP fleet handoff

AZ-OS already stamps `GET /v1/health`. This file is the patch recipe for the sibling Softwares download-tracker Workers that do not. It is a draft handoff for GitBaby. It is not a second AZ-OS stamp, and it is not a deploy.

Do not open a pull request from this branch until Aziel says yes. Do not deploy from this branch.

## What already works

Canonical implementation (copy these files; do not rewrite them):

- `workers/download-tracker/src/build-stamp.js`
- `workers/download-tracker/scripts/verify-build-stamp.mjs`
- `workers/download-tracker/wrangler.toml` lines under the `BUILD-STAMP-1.0` comment (`[version_metadata]` binding `CF_VERSION_METADATA`)
- Wiring in `workers/download-tracker/src/index.js`: `stampHealth(path, request, response, env)` on the way out of `fetch`

Live AZ-OS (`https://azos-download-tracker.vibelock.workers.dev/v1/health`) already returns the four fields. `git_sha` matches `main` `5b7e79f6ebbf11cf2524fd9722e67a053a245a37`. That landed in #31.

AZInterface (`https://azinterface-download-tracker.vibelock.workers.dev/v1/health`) already returns the same four fields. Leave `AzielEliab/azinterface` alone.

ZionPattern Solver (`https://zsolver-download-tracker.vibelock.workers.dev/v1/health`) already returns `git_sha` from `gitShaOf` (7–40 hex). It does not return `version_id`. It is in the patch list below. Keep `gitShaOf` so `workers/download-tracker/test-health.mjs` stays valid. `stampHealth` overwrites the health body's `git_sha` with the 40-hex reader. A full `git rev-parse HEAD` still matches. A short sha on the health body becomes `null`.

## Field shape

`buildStamp(env)` adds these keys onto the existing JSON body. Other health keys stay.

```json
{
  "git_sha": "5b7e79f6ebbf11cf2524fd9722e67a053a245a37",
  "git_sha_source": "env.GIT_SHA (deploy --var)",
  "version_id": "21c0b388-b17a-449e-800a-bd433ef41380",
  "version_id_source": "cf_version_metadata"
}
```

Unset (no `--var GIT_SHA`, no version metadata binding) is honest null, never a guessed sha:

```json
{
  "git_sha": null,
  "git_sha_source": "unset: deployed without --var GIT_SHA, so live-vs-main cannot be proven",
  "version_id": null,
  "version_id_source": "unset"
}
```

`git_sha` is accepted only when `env.GIT_SHA` matches `/^[0-9a-f]{40}$/` after trim and lowercasing. `version_id` is `env.CF_VERSION_METADATA.id` when that binding is a non-empty string.

## Patch recipe (every repo below)

Work from each repo's `main`. Branch name: `draft/build-stamp-health`. One branch per repo. Commit. Push. Do not open the GitHub PR until Aziel says yes. Do not `wrangler deploy` in this pass.

1. Copy `workers/download-tracker/src/build-stamp.js` from `AzielEliab/azos` at this commit, unchanged.
2. Copy `workers/download-tracker/scripts/verify-build-stamp.mjs` unchanged. In `workers/download-tracker/package.json`, append `node scripts/verify-build-stamp.mjs` to `scripts.test` (or set `scripts.test` to that command when the key is missing). The script imports the Worker default export and `GET /v1/health`. If that fetch touches a binding the health path does not need, mock it the way the script already mocks `DOWNLOADS`. Keep the `stampHealth` assertions either way.
3. Append this to `workers/download-tracker/wrangler.toml` when `[version_metadata]` is absent. Do not commit a `GIT_SHA` value under `[vars]`.

```toml
# BUILD-STAMP-1.0: /v1/health reports git_sha and version_id.
# Deploy with: npx wrangler deploy --keep-vars --var GIT_SHA:$(git rev-parse HEAD)
[version_metadata]
binding = "CF_VERSION_METADATA"
```

4. In the health file from the table, add `import { stampHealth } from "./build-stamp.js";` next to the other local imports.
5. Wrap only the `GET /v1/health` response. `path` in these handlers is already the normalized pathname (`/v1/health` with no trailing slash), which is what `stampHealth` matches.

Block return (`return json({...})` or `return runtimeJson(...)`):

```js
return stampHealth(path, request, json({
  // existing body, unchanged
}), env);
```

One-liner:

```js
if (path === "/v1/health" && request.method === "GET") return stampHealth(path, request, json(EXISTING_ARG), env);
```

`json(...)` and `runtimeJson(...)` in these Workers set `Content-Type: application/json`. `stampHealth` only rewrites that JSON `GET /v1/health` response. Every other response passes through.

6. When the table's `pass env` column is `yes`, the handler does not take `env` today, and the call site does not pass it. Add `env` as the last parameter and pass the `fetch(request, env)` binding through. `stampHealth` reads `env.GIT_SHA` and `env.CF_VERSION_METADATA` from that argument.

```js
export async function handleRuntimeApi(request, url, env) {
```

```js
const runtime = await handleRuntimeApi(request, url, env);
```

Use the real function name from the table (`handleRuntime` or `handleRuntimeApi`).

7. Run `node scripts/verify-build-stamp.mjs` from `workers/download-tracker` (or `npm test` there).

## After Aziel says yes

Open one PR per sibling repo, base `main`, head `draft/build-stamp-health`. Do not open an AZ-OS PR for the stamp itself; #31 is already on `main`. This branch only carries the recipe. Merge the recipe doc only if Aziel wants it in AZ-OS.

Deploy is a separate step, after the sibling PR is merged, from `workers/download-tracker`:

```bash
npx wrangler deploy --keep-vars --var GIT_SHA:$(git rev-parse HEAD)
```

Then `curl -sS -A 'Mozilla/5.0' https://<worker>/v1/health` and check `git_sha` equals `git rev-parse HEAD` and `version_id` is a non-empty string. Until that deploy, a merged stamp still reports `git_sha: null` with the unset source string. That null is the unverified tip.

## Why this launch stopped at AZ-OS

`cursor[bot]` can push `AzielEliab/azos`. `git push` to `AzielEliab/azbot` returned 403 (`Permission to AzielEliab/azbot.git denied to cursor[bot]`). The other sibling repos were not pushed. Line numbers below are `main` as of 2026-10-23 and will drift if those files move.

Live census the same day: 37 catalog `worker_home` URLs on `*-download-tracker.vibelock.workers.dev`. Two return both `git_sha` and `version_id` (azos, azinterface). One returns `git_sha` only (zsolver). Thirty-four return neither key. AZBot is in that thirty-four, so its deployed tip stays unverified.

## Sibling repos to patch

| slug | repo | health file:line | shape | pass env | call site |
| --- | --- | --- | --- | --- | --- |
| `azbot` | `AzielEliab/azbot` | `workers/download-tracker/src/runtime.js:139` | block | no | `workers/download-tracker/src/index.js` `612:const runtime = await handleRuntimeApi(request, url, env);` |
| `4dmap` | `AzielEliab/4dmap` | `workers/download-tracker/src/runtime.js:311` | block | yes | `workers/download-tracker/src/index.js` `349:const runtime = await handleRuntimeApi(request, url);` |
| `ark` | `AzielEliab/ark` | `workers/download-tracker/src/index.js:670` | block | no | `workers/download-tracker/src/index.js` `758:const runtime = await handleRuntime(request, url, env);` |
| `azai` | `AzielEliab/azai` | `workers/download-tracker/src/index.js:734` | block | yes | `workers/download-tracker/src/index.js` `864:const runtime = await handleRuntime(request, url);` |
| `azbrowser` | `AzielEliab/azbrowser` | `workers/download-tracker/src/runtime.js:268` | one-liner | no | `workers/download-tracker/src/index.js` `303:const runtime = await handleRuntimeApi(request, url, env);` |
| `azchat` | `AzielEliab/azchat` | `workers/download-tracker/src/runtime.js:418` | one-liner | no | `workers/download-tracker/src/index.js` `374:const runtime = await handleRuntimeApi(request, url, env);` |
| `azclce` | `AzielEliab/az-clce` | `workers/download-tracker/src/index.js:771` | block | yes | `workers/download-tracker/src/index.js` `918:const runtime = await handleRuntime(request, url);` |
| `azcoherence` | `AzielEliab/AZCoherence` | `workers/download-tracker/src/runtime.js:505` | one-liner | no | `workers/download-tracker/src/index.js` `381:const runtime = await handleRuntimeApi(request, url, env);` |
| `azhub` | `AzielEliab/azhub` | `workers/download-tracker/src/runtime.js:289` | one-liner | no | `workers/download-tracker/src/index.js` `320:const runtime = await handleRuntimeApi(request, url, env);` |
| `azieltether` | `AzielEliab/azieltether` | `workers/download-tracker/src/runtime.js:584` | block | yes | `workers/download-tracker/src/index.js` `659:const runtime = await handleRuntimeApi(request, url);` |
| `azmail` | `AzielEliab/azmail` | `workers/download-tracker/src/runtime.js:289` | block | no | `workers/download-tracker/src/index.js` `303:const runtime = await handleRuntimeApi(request, url, env);` |
| `aznet` | `AzielEliab/aznet` | `workers/download-tracker/src/runtime.js:891` | block | no | `workers/download-tracker/src/index.js` `398:const runtime = await handleRuntimeApi(request, url, env);` |
| `chronolock` | `AzielEliab/chronolock` | `workers/download-tracker/src/runtime.js:364` | block | yes | `workers/download-tracker/src/index.js` `657:const runtime = await handleRuntimeApi(request, url);` |
| `codelock` | `AzielEliab/codelock` | `workers/download-tracker/src/runtime.js:461` | block | no | `workers/download-tracker/src/index.js` `566:const runtime = await handleRuntime(request, url, env);` |
| `decisiongate` | `AzielEliab/decisiongate` | `workers/download-tracker/src/runtime.js:438` | one-liner | yes | `workers/download-tracker/src/index.js` `662:const runtime = await handleRuntimeApi(request, url);` |
| `embryolock` | `AzielEliab/EmbryoLock` | `workers/download-tracker/src/runtime.js:481` | one-liner | no | `workers/download-tracker/src/index.js` `370:const runtime = await handleRuntimeApi(request, url, env);` |
| `employeelock` | `AzielEliab/employeelock` | `workers/download-tracker/src/runtime.js:357` | block | yes | `workers/download-tracker/src/index.js` `629:const runtime = await handleRuntimeApi(request, url);` |
| `foldlock` | `AzielEliab/foldlock` | `workers/download-tracker/src/runtime.js:398` | block | yes | `workers/download-tracker/src/index.js` `613:const runtime = await handleRuntimeApi(request, url);` |
| `forgereceipts` | `AzielEliab/forgereceipts` | `workers/download-tracker/src/runtime.js:413` | block | no | `workers/download-tracker/src/index.js` `583:const runtime = await handleRuntime(request, url, env);` |
| `glossafilter` | `AzielEliab/glossafilter` | `workers/download-tracker/src/runtime.js:670` | block | yes | `workers/download-tracker/src/index.js` `618:const runtime = await handleRuntimeApi(request, url);` |
| `godlock` | `AzielEliab/godlock` | `workers/download-tracker/src/runtime.js:314` | block | no | `workers/download-tracker/src/index.js` `523:const runtime = await handleRuntime(request, url, env);` |
| `mialock` | `AzielEliab/mialock` | `workers/download-tracker/src/runtime.js:456` | block | yes | `workers/download-tracker/src/index.js` `654:const runtime = await handleRuntimeApi(request, url);` |
| `miragegrid` | `AzielEliab/miragegrid` | `workers/download-tracker/src/runtime.js:791` | block | yes | `workers/download-tracker/src/index.js` `485:const runtime = await handleRuntimeApi(request, url);` |
| `peacelock` | `AzielEliab/peacelock` | `workers/download-tracker/src/runtime.js:947` | block | no | `workers/download-tracker/src/index.js` `391:const runtime = await handleRuntimeApi(request, url, env);` |
| `postking` | `AzielEliab/postking-chess` | `workers/download-tracker/src/index.js:735` | block | yes | `workers/download-tracker/src/index.js` `832:const runtime = await handleRuntime(request, url);` |
| `shadowlock` | `AzielEliab/shadowlock` | `workers/download-tracker/src/runtime.js:575` | block | yes | `workers/download-tracker/src/index.js` `405:const runtime = await handleRuntimeApi(request, url);` |
| `spectrallock` | `AzielEliab/spectrallock` | `workers/download-tracker/src/index.js:871` | block | yes | `workers/download-tracker/src/index.js` `1102:const runtime = await handleRuntime(request, url);` |
| `staticclock` | `AzielEliab/staticclock` | `workers/download-tracker/src/runtime.js:532` | block | yes | `workers/download-tracker/src/index.js` `404:const runtime = await handleRuntimeApi(request, url);` |
| `temporallock` | `AzielEliab/temporallock` | `workers/download-tracker/src/runtime.js:683` | block | yes | `workers/download-tracker/src/index.js` `397:const runtime = await handleRuntimeApi(request, url);` |
| `trajectorylock` | `AzielEliab/trajectorylock` | `workers/download-tracker/src/runtime.js:341` | block | yes | `workers/download-tracker/src/index.js` `625:const runtime = await handleRuntimeApi(request, url);` |
| `veillock` | `AzielEliab/veillock` | `workers/download-tracker/src/runtime.js:743` | block | no | `workers/download-tracker/src/index.js` `380:const runtime = await handleRuntime(request, url, env);` |
| `vibelock` | `AzielEliab/vibelock` | `workers/download-tracker/src/runtime.js:1032` | block | no | `workers/download-tracker/src/index.js` `376:const runtime = await handleRuntime(request, url, env);` |
| `whistlelock` | `AzielEliab/whistlelock` | `workers/download-tracker/src/runtime.js:331` | block | yes | `workers/download-tracker/src/index.js` `627:const runtime = await handleRuntimeApi(request, url);` |
| `whitestone` | `AzielEliab/Whitestone` | `workers/download-tracker/src/index.js:742` | block | no | `workers/download-tracker/src/index.js` `810:const runtime = await handleRuntime(request, url, env);` |
| `zsolver` | `AzielEliab/zion-pattern-solver` | `workers/download-tracker/src/index.js:644` | block | no | `workers/download-tracker/src/index.js` `740:const runtime = await handleRuntime(request, url, env);` |

Health URL for each slug is `https://<slug>-download-tracker.vibelock.workers.dev/v1/health`, except the repo name is not always the slug:

- `azbot` → `https://azbot-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/azbot`
- `4dmap` → `https://4dmap-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/4dmap`
- `ark` → `https://ark-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/ark`
- `azai` → `https://azai-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/azai`
- `azbrowser` → `https://azbrowser-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/azbrowser`
- `azchat` → `https://azchat-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/azchat`
- `azclce` → `https://azclce-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/az-clce`
- `azcoherence` → `https://azcoherence-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/AZCoherence`
- `azhub` → `https://azhub-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/azhub`
- `azieltether` → `https://azieltether-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/azieltether`
- `azmail` → `https://azmail-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/azmail`
- `aznet` → `https://aznet-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/aznet`
- `chronolock` → `https://chronolock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/chronolock`
- `codelock` → `https://codelock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/codelock`
- `decisiongate` → `https://decisiongate-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/decisiongate`
- `embryolock` → `https://embryolock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/EmbryoLock`
- `employeelock` → `https://employeelock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/employeelock`
- `foldlock` → `https://foldlock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/foldlock`
- `forgereceipts` → `https://forgereceipts-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/forgereceipts`
- `glossafilter` → `https://glossafilter-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/glossafilter`
- `godlock` → `https://godlock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/godlock`
- `mialock` → `https://mialock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/mialock`
- `miragegrid` → `https://miragegrid-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/miragegrid`
- `peacelock` → `https://peacelock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/peacelock`
- `postking` → `https://postking-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/postking-chess`
- `shadowlock` → `https://shadowlock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/shadowlock`
- `spectrallock` → `https://spectrallock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/spectrallock`
- `staticclock` → `https://staticclock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/staticclock`
- `temporallock` → `https://temporallock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/temporallock`
- `trajectorylock` → `https://trajectorylock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/trajectorylock`
- `veillock` → `https://veillock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/veillock`
- `vibelock` → `https://vibelock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/vibelock`
- `whistlelock` → `https://whistlelock-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/whistlelock`
- `whitestone` → `https://whitestone-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/Whitestone`
- `zsolver` → `https://zsolver-download-tracker.vibelock.workers.dev/v1/health` in `AzielEliab/zion-pattern-solver`

### AZBot (tip unverified)

`AzielEliab/azbot` `workers/download-tracker/src/runtime.js` line 139. Handler already receives `env`: `export async function handleRuntimeApi(request, url, env)`. Call site `workers/download-tracker/src/index.js` already passes `env`. No signature change.

```js
import { stampHealth } from "./build-stamp.js";

if (path === "/v1/health" && request.method === "GET") {
  return stampHealth(path, request, json({
    ok: true, author: "Aziel Eliab",
    // ...existing body, unchanged...
  }), env);
}
```

### Handler that must gain `env`

Eighteen handlers do not take `env` today. Add the parameter and pass it from `fetch`. The `pass env` column is `yes` for those rows. Example, `AzielEliab/4dmap`:

```js
// workers/download-tracker/src/runtime.js
export async function handleRuntimeApi(request, url, env) {
  if (path === "/v1/health" && request.method === "GET") {
    return stampHealth(path, request, json({
      // existing body
    }), env);
  }
}
```

```js
// workers/download-tracker/src/index.js
const runtime = await handleRuntimeApi(request, url, env);
```

### One-liner

These return on the `if` line: azbrowser, azchat, azcoherence, azhub, decisiongate, embryolock. Example, `AzielEliab/azbrowser` `runtime.js:268` (already has `env`):

```js
if (path === "/v1/health" && request.method === "GET") return stampHealth(path, request, json(await dispatch("health", {})), env);
```

`AzielEliab/decisiongate` is a one-liner and does not take `env` yet (`runtime.js:438`, call `index.js` `handleRuntimeApi(request, url)`). Add `env` to the signature and the call, then wrap `json(health())`.

