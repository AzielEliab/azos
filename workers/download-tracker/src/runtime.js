/**
 * AZ-OS hosted runtime (Cloudflare Worker).
 * Labels / overlay receipts only. Integrity precedes execution.
 * NOT a kernel, worm, or remote machine takeover.
 * Hosted halt is a token in the JSON response, not killing the caller's OS.
 */
function runtimeCors() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function runtimeJson(body, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...runtimeCors() },
  });
}

async function sha256Hex(bytes) {
  const data = bytes instanceof Uint8Array ? bytes : new TextEncoder().encode(String(bytes));
  const dig = await crypto.subtle.digest("SHA-256", data);
  const arr = new Uint8Array(dig);
  let out = "";
  for (let i = 0; i < arr.length; i++) out += arr[i].toString(16).padStart(2, "0");
  return out;
}

async function readJsonBody(request) {
  const ct = (request.headers.get("content-type") || "").toLowerCase();
  if (request.method === "GET" || request.method === "HEAD") return {};
  const text = await request.text();
  if (!text || !text.trim()) return {};
  try {
    return JSON.parse(text);
  } catch {
    const err = new Error("JSON body required");
    err.status = 400;
    throw err;
  }
}

function utcNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function aiHowTo(base) {
  const openapi = base + "/openapi.json";
  const health = base + "/v1/health";
  return {
    chatgpt_actions: [
      "Open GPT Editor → Actions → Import from URL",
      "Paste " + openapi,
      "Authentication: None",
      "Allow GET /v1/health and the listed POST /v1 routes",
      "Test GET /v1/health, then a sample POST from the spec",
    ],
    grok_xai_tools: [
      "Add an HTTP / OpenAPI tool pointing at " + openapi,
      "Or register GET /v1/health, GET /openapi.json, and the product POSTs",
      "No API key. CORS is *",
    ],
    venice_http_tools: [
      "Add an HTTP tool with method, URL, and JSON body from " + openapi,
      "Start with GET " + health,
      "Then call the product POST listed in the spec",
    ],
    mcp_catalog: "https://aziel-runtime.vibelock.workers.dev/mcp",
    notes: [
      "GET /download still serves the gzip tarball and increments the counter.",
      "/v1, /openapi.json, and /ai do not increment DOWNLOADS.",
    ],
  };
}

const PRODUCT = "azos";
const EXAMPLE_PAYLOAD = {};

const VERSION = "0.1.0";
const BASE = "https://azos-download-tracker.vibelock.workers.dev";
const SKILL = "---\nname: AZ-OS\ndescription: Use when labeling overlay integrity (invite / halt token / revoke receipt). Never treat hosted halt as killing an OS. Hosted /v1 via this Worker or aziel-runtime. Author Aziel Eliab.\n---\n\n# AZ-OS\n\nIntegrity precedes execution.\n\nAuthor: **Aziel Eliab**.\n\nUse when labeling overlay integrity (invite / halt token / revoke receipt). Never treat hosted halt as killing an OS.\n\nAlways send `User-Agent: Mozilla/5.0`. Cloudflare Workers may 403 an empty agent.\n\n## Endpoints (this Worker)\n\nHost: `https://azos-download-tracker.vibelock.workers.dev`\n\n| Method | Path | What |\n|--------|------|------|\n| GET | `/v1/health` | Liveness. Does not increment downloads. |\n| GET | `/v1/skill` | This markdown. Does not increment downloads. |\n| POST | `/v1/status` | Overlay status labels. |\n| POST | `/v1/invite` | Voluntary invite text (not infection). |\n| POST | `/v1/halt` | Halt overlay token. Does not kill the caller OS. |\n| POST | `/v1/revoke` | Revoke label / overlay receipt only. |\n\nOpenAPI: `https://azos-download-tracker.vibelock.workers.dev/openapi.json`\n\nCatalog OpenAPI: `https://aziel-runtime.vibelock.workers.dev/openapi.json`\n\nMCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`\n\nCatalog aliases under `/p/azos/\u2026`.\n\n## How to call (Mozilla/5.0)\n\n```bash\ncurl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/health\ncurl -s -A 'Mozilla/5.0' -X POST https://azos-download-tracker.vibelock.workers.dev/v1/invite \\\n  -H 'content-type: application/json' -d '{}'\ncurl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/skill\n```\n\nGrok: import the catalog OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.\n\n## Local (after one-click install)\n\n```bash\ncurl -fsSL https://azos-download-tracker.vibelock.workers.dev/install.sh | bash\nazos ui\n```\n\nThen open http://127.0.0.1:8800 (this computer only).\n\n## Honest banner\n\nTHIS IS: a portable ethical overlay + AZ Interface control surface. THIS IS NOT: a kernel, worm, remote machine takeover, or a silent block. Hosted halt is a token in JSON, not killing the caller OS. Author Aziel Eliab.\n\nDOI: https://doi.org/10.5281/zenodo.21431711  \nRecord: https://zenodo.org/records/21431711\n\nApache-2.0 (or the repo LICENSE). Forks are welcome and always allowed.\n\n## Catalog + local UI\n\nAuthor: **Aziel Eliab**. Honest scope: Read-only status / principles. Does not grant remote shell.\n\n- Catalog product: https://aziel-runtime.vibelock.workers.dev/p/azos/\n- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json\n- Catalog MCP: `POST https://aziel-runtime.vibelock.workers.dev/mcp`\n- This Worker skill: `GET https://azos-download-tracker.vibelock.workers.dev/v1/skill`\n- This Worker OpenAPI: https://azos-download-tracker.vibelock.workers.dev/openapi.json\n- Sample payload: `GET https://azos-download-tracker.vibelock.workers.dev/v1/example`\n\nLocal UI: **Import JSON file** (`type=file`) and **Export JSON**. Then `azos doctor`.\n\nGrok: import catalog or Worker OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.\n";

const MOTTO = "Integrity precedes execution.";
const DOWNLOAD_URL = "https://azos-download-tracker.vibelock.workers.dev/";
const SOURCE_URL = "https://github.com/AzielEliab/azos";
const SAFE_ACTIONS = ["list_modules", "echo", "status", "purge_session"];

const INVITE = `AZ-OS — voluntary overlay (not an infection)

AZ-OS is a portable folder and control surface. It is not a kernel,
not a bootloader, not a hypervisor, and not malware. You run it because
you choose to.

Principles
  1. Integrity precedes execution.
     No module or action runs without a token from ARC.
  2. Time-bound actions are final.
     Authorized executions append to an immutable sha256 chain. No rewrite.
  3. Understanding precedes modification.
     Extending or loading a module requires an explicit comprehension
     checkbox and a short restatement of intent.
  4. The system protects itself architecturally.
     Unsigned or unauthorized run() raises AuthorizationError. Default deny.
  5. Propagation is not infection.
     This invite prints principles and a download URL. AZ-OS does not
     copy itself onto other machines.

You are invited to run AZ-OS yourself. This is not a silent block.
Adoption is voluntary.

Counted download:
  ${DOWNLOAD_URL}

Source:
  ${SOURCE_URL}
`;

function overlayMeta(obj) {
  return {
    motto: MOTTO,
    overlay: true,
    kernel: false,
    worm: false,
    malware: false,
    remote_machine_takeover: false,
    kills_caller_os: false,
    ...obj,
  };
}

function randomHex(nBytes) {
  const buf = new Uint8Array(nBytes);
  crypto.getRandomValues(buf);
  let out = "";
  for (let i = 0; i < buf.length; i++) out += buf[i].toString(16).padStart(2, "0");
  return out;
}

function openapiDoc() {
  return {
    openapi: "3.1.0",
    info: {
      title: "AZ-OS Runtime API",
      version: VERSION,
      summary: MOTTO,
      description: "Labels / overlay receipts only. NOT a kernel, worm, or remote machine takeover. Hosted halt is a token in JSON, not killing the caller's OS.",
    },
    servers: [{ url: BASE }],
    paths: {
      
            "/v1/example": { get: { operationId: "azosExample", summary: "Sample JSON payload. Does not increment downloads.", responses: { "200": { description: "OK" } } } },
      "/v1/skill": {
        get: {
          operationId: "azos_skill",
          summary: "Return skill markdown. Does not increment download KV.",
          responses: { "200": { description: "markdown" } },
        },
      },
"/v1/health": { get: { operationId: "azosHealth", summary: "Liveness", responses: { "200": { description: "OK" } } } },
      "/v1/status": { post: { operationId: "azosStatus", summary: "Overlay status labels", responses: { "200": { description: "Status overlay receipt" } } } },
      "/v1/invite": { post: { operationId: "azosInvite", summary: "Voluntary invite text (not infection)", responses: { "200": { description: "Invite" } } } },
      "/v1/halt": { post: { operationId: "azosHalt", summary: "Return a halt overlay token. Does not kill the caller OS.", responses: { "200": { description: "Halt token" } } } },
      "/v1/revoke": { post: { operationId: "azosRevoke", summary: "Revoke label / overlay receipt only", requestBody: { required: false, content: { "application/json": { schema: { type: "object", properties: { token: { type: "string" } } } } } }, responses: { "200": { description: "Revoke overlay receipt" } } } },
    },
  };
}

export async function handleRuntime(request, url, env) {
  const path = url.pathname;
  if (path === "/v1/health" && request.method === "GET") {
    return runtimeJson(overlayMeta({ ok: true, author: "Aziel Eliab", product: PRODUCT, version: VERSION }));
  }
  if ((path === "/v1/example" || path === "/v1/example/") && (request.method === "GET" || request.method === "HEAD")) {
    return runtimeJson({
      ok: true,
      product: PRODUCT,
      author: "Aziel Eliab",
      example: EXAMPLE_PAYLOAD,
      note: "Sample payload only. Does not increment downloads.",
    });
  }

  if (path === "/v1/skill" && request.method === "GET") {
    return new Response(SKILL, {
      status: 200,
      headers: { "Content-Type": "text/markdown; charset=utf-8", "Cache-Control": "private, no-store", ...runtimeCors() },
    });
  }
  if (path === "/openapi.json" && request.method === "GET") return runtimeJson(openapiDoc());
  if (path === "/ai" && request.method === "GET") {
    return runtimeJson(overlayMeta({
      product: PRODUCT, title: "Use with Grok, ChatGPT, Venice",
      openapi: BASE + "/openapi.json", health: BASE + "/v1/health", ...aiHowTo(BASE),
    }));
  }
  if (path === "/v1" && request.method === "GET") {
    return runtimeJson(overlayMeta({
      product: PRODUCT,
      endpoints: ["GET /v1/health", "POST /v1/status", "POST /v1/invite", "POST /v1/halt", "POST /v1/revoke", "GET /openapi.json", "GET /ai"],
    }));
  }
  if (path === "/v1/status" && request.method === "POST") {
    return runtimeJson(overlayMeta({
      ok: true,
      product: PRODUCT,
      overlay_name: "AZ-OS",
      interface: "AZ Interface (hosted labels)",
      version: VERSION,
      halted: false,
      lumen: "running",
      builtins: SAFE_ACTIONS,
      tokens: { active: 0, revoked: 0, issued: 0 },
      note: "Hosted status is an overlay receipt, not a kernel and not the caller's OS.",
    }));
  }
  if (path === "/v1/invite" && request.method === "POST") {
    return runtimeJson(overlayMeta({
      ok: true,
      product: PRODUCT,
      invite: INVITE,
      download: DOWNLOAD_URL,
      source: SOURCE_URL,
      infection: false,
      note: "Propagation is invitation, not infection. Writes no files on the caller.",
    }));
  }
  if (path === "/v1/halt" && request.method === "POST") {
    const token = randomHex(32);
    const token_hash = await sha256Hex(token);
    return runtimeJson(overlayMeta({
      ok: true,
      product: PRODUCT,
      halt: {
        token,
        token_hash,
        kind: "overlay_receipt",
        issued_at: utcNow(),
      },
      note: "Hosted halt is a token in this JSON response. It does not kill the caller's OS.",
    }));
  }
  if (path === "/v1/revoke" && request.method === "POST") {
    let body = {};
    try { body = await readJsonBody(request); } catch (e) { return runtimeJson(overlayMeta({ ok: false, error: e.message }), e.status || 400); }
    const token = body.token != null ? String(body.token) : "";
    let token_hash = null;
    if (token) token_hash = await sha256Hex(token);
    return runtimeJson(overlayMeta({
      ok: true,
      product: PRODUCT,
      revoke: {
        kind: "overlay_receipt",
        token_presented: Boolean(token),
        token_hash,
        revoked_at: utcNow(),
      },
      note: "Revoke is a label / overlay receipt only. It does not take over a remote machine.",
    }));
  }
  if (path === "/v1/status" || path === "/v1/invite" || path === "/v1/halt" || path === "/v1/revoke") {
    return runtimeJson(overlayMeta({ error: "method not allowed" }), 405);
  }
  if (path.startsWith("/v1/")) return runtimeJson(overlayMeta({ error: "not found", product: PRODUCT }), 404);
  return null;
}
