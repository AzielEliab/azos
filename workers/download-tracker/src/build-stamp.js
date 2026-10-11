/**
 * BUILD-STAMP-1.0: stamp /v1/health with the deployed git_sha and version_id, the same
 * way aziel-runtime does. GIT_SHA is injected at deploy:
 *   npx wrangler deploy --keep-vars --var GIT_SHA:$(git rev-parse HEAD)
 * version_id comes from the CF_VERSION_METADATA binding. Missing values read null with a
 * source that says so; nothing is guessed.
 */
const HEX40 = /^[0-9a-f]{40}$/;

export function buildStamp(env) {
  const raw = env && typeof env.GIT_SHA === "string" ? env.GIT_SHA.trim().toLowerCase() : "";
  const git_sha = HEX40.test(raw) ? raw : null;
  const meta = env && env.CF_VERSION_METADATA && typeof env.CF_VERSION_METADATA === "object" ? env.CF_VERSION_METADATA : null;
  const version_id = meta && typeof meta.id === "string" && meta.id ? meta.id : null;
  return {
    git_sha,
    git_sha_source: git_sha ? "env.GIT_SHA (deploy --var)" : "unset: deployed without --var GIT_SHA, so live-vs-main cannot be proven",
    version_id,
    version_id_source: version_id ? "cf_version_metadata" : "unset",
  };
}

/** Add the stamp to a JSON /v1/health response. Anything else passes through untouched. */
export async function stampHealth(path, request, res, env) {
  if (path !== "/v1/health" || request.method !== "GET" || !res || !String(res.headers.get("content-type") || "").includes("json")) return res;
  let body;
  try {
    body = await res.clone().json();
  } catch {
    return res;
  }
  if (!body || typeof body !== "object" || Array.isArray(body)) return res;
  Object.assign(body, buildStamp(env));
  const headers = new Headers(res.headers);
  headers.delete("content-length");
  return new Response(JSON.stringify(body, null, 2), { status: res.status, headers });
}
