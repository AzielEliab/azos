/**
 * AZ-OS hosted runtime (Cloudflare Worker).
 * Ethics-coded remote shell. Integrity precedes execution.
 * Author: Aziel Eliab.
 *
 * Hosted sessions live in KV (session vfs). Not a kernel, not SSH,
 * not unrestricted host bash. Halt is a session token, not killing
 * the caller OS.
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
      "Test GET /v1/health, then POST /v1/session and POST /v1/exec",
    ],
    grok_xai_tools: [
      "Add an HTTP / OpenAPI tool pointing at " + openapi,
      "Or register GET /v1/health, POST /v1/session, POST /v1/exec",
      "No API key. CORS is *",
    ],
    venice_http_tools: [
      "Add an HTTP tool with method, URL, and JSON body from " + openapi,
      "Start with GET " + health,
      "Then POST /v1/session and POST /v1/exec",
    ],
    mcp_catalog: "https://aziel-runtime.vibelock.workers.dev/mcp",
    notes: [
      "GET /download still serves the gzip tarball and increments the counter.",
      "/v1, /openapi.json, and /ai do not increment DOWNLOADS.",
      "AZ-OS is a true remote shell gated by coded ethics. Status is read-only.",
    ],
  };
}

const PRODUCT = "azos";
const VERSION = "0.3.0";
const BASE = "https://azos-download-tracker.vibelock.workers.dev";
const MOTTO = "Integrity precedes execution.";
const AUTHOR = "Aziel Eliab";
const DOWNLOAD_URL = "https://azos-download-tracker.vibelock.workers.dev/";
const SOURCE_URL = "https://github.com/AzielEliab/azos";
const SESSION_TTL = 3600;
const MAX_COMMAND_CHARS = 4096;
const MAX_FILE_BYTES = 65536;

const PRINCIPLES = [
  "Integrity precedes execution.",
  "Time-bound actions are final.",
  "Understanding precedes modification.",
  "The system protects itself architecturally.",
  "Propagation is not infection.",
];

const GATES = ["definition", "evidence", "impact", "integrity", "responsibility"];

const SHELL_VERBS = [
  "help", "pwd", "ls", "cat", "write", "echo", "mkdir", "rm", "cd",
  "status", "principles", "invite", "modules", "list_modules", "history",
  "whoami", "session", "halt", "exit", "close", "id", "uname",
];

const DENIED_VERBS = [
  "sudo", "bash", "sh", "zsh", "python", "curl", "wget", "nc", "nmap",
  "ssh", "scp", "mkfs", "dd", "eval", "exec", "reboot", "shutdown",
];

const BANNED_IMPACT = [
  "wipe disk", "format drive", "mkfs", "self-replicate", "self replicate",
  "worm", "ransom", "infect",
];

const HOST_META = ["|", ";", "`", "$(", "&&", "||", "\n", "\r"];

const SAFE_ACTIONS = ["list_modules", "echo", "status", "purge_session", "shell"];

const SKILL = `---
name: AZ-OS
description: Use when calling the AZ-OS ethics-coded remote shell (hosted /v1 or local package). Sessions and commands are principle-bound. Author Aziel Eliab.
---

# AZ-OS

Integrity precedes execution. Author: **Aziel Eliab**.

**THIS IS:** prefab AZ-OS — ethics-coded remote shell with all Aziel software hooked in. Windows-style desktop; Ever Blooming sigil (rose-star, no words). TemporalLock×StaticClock integrity lattice. Sessions and commands are principle-bound.

**THIS IS NOT:** a kernel, bootloader, hypervisor, worm, malware, unrestricted host bash, or SSH. Hosted \`/v1\` does not increment downloads or views.

Always send \`User-Agent: Mozilla/5.0\`. Cloudflare Workers may 403 an empty agent.

## Honest scope

| Layer | What it is |
|-------|------------|
| Protocols | HTTPS JSON (this Worker), HTTP loopback \`127.0.0.1:8800\` (AZ Interface), CLI stdin (\`azos shell\`) |
| Auth | ARC 32-byte token issued only after the five ethics gates PASS. Hashed at rest. |
| Sandbox | Session vfs (local \`.azos/workspace/<id>/\`, hosted KV vfs). Closed verb list. No host subprocess. |
| Halt | Stops overlay / session authority. Does not kill the caller OS. |

## Call these URLs

- Worker OpenAPI: https://azos-download-tracker.vibelock.workers.dev/openapi.json
- Catalog OpenAPI: https://aziel-runtime.vibelock.workers.dev/openapi.json
- MCP: \`POST https://aziel-runtime.vibelock.workers.dev/mcp\`
- Live skill (this markdown): \`GET https://azos-download-tracker.vibelock.workers.dev/v1/skill\`

Ops (do **not** increment downloads or views):

- \`GET /v1/health\` — liveness + scope
- \`GET /v1/skill\` — this file
- \`POST /v1/status\` — read-only status / principles (no exec)
- \`POST /v1/session\` — open an ethics-gated shell session
- \`POST /v1/exec\` — run one principle-bound command in that session
- \`POST /v1/close\` — close a session
- Product POSTs listed in OpenAPI (\`invite\`, \`halt\`, \`revoke\`)

Grok: import OpenAPI as a custom tool. ChatGPT: GPT Actions. Venice: HTTP tools.

## Example

\`\`\`bash
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/health
curl -s -A 'Mozilla/5.0' https://azos-download-tracker.vibelock.workers.dev/v1/skill
curl -s -A 'Mozilla/5.0' -X POST https://azos-download-tracker.vibelock.workers.dev/v1/session \\
  -H 'content-type: application/json' \\
  -d '{"actor":"operator","definition":"Open an ethics-gated shell session.","evidence":"Operator requested a principle-bound remote shell.","impact":"Hosted KV vfs only. No host subprocess."}'
\`\`\`

## Local (after one-click install)

\`\`\`bash
curl -fsSL https://azos-download-tracker.vibelock.workers.dev/install.sh | bash
azos ui
azos shell --actor operator -c 'help'
azos doctor
\`\`\`

Then open http://127.0.0.1:8800 (loopback only).

Counted download (gzip HTTP 200, no 302): https://azos-download-tracker.vibelock.workers.dev/download?asset=azos-0.3.0.tar.gz
GitHub: https://github.com/AzielEliab/azos

Paper: DOI https://doi.org/10.5281/zenodo.21431711 · https://zenodo.org/records/21431711 · Apache-2.0. Forks welcome.
`;

const INVITE = `AZ-OS — ethics-coded remote shell (voluntary; not an infection)

AZ-OS is a true remote shell gated by coded ethics. You run it because
you choose to. It is not a kernel, bootloader, hypervisor, or malware.
It is not unrestricted host bash and not SSH.

${MOTTO}

Principles
  1. Integrity precedes execution.
     No module, session, or command runs without a token from ARC.
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

Scope (honest)
  Protocols: HTTPS JSON (hosted Worker), HTTP loopback 127.0.0.1:8800,
             CLI stdin (\`azos shell\`).
  Auth:      ARC 32-byte token after the five ethics gates. Hashed at rest.
  Sandbox:   session vfs under .azos/workspace (local) or KV vfs (hosted).
             No host subprocess. Halt stops the overlay session, not the
             caller OS.

You are invited to run AZ-OS yourself. This is not a silent block.
Adoption is voluntary.

Counted download:
  ${DOWNLOAD_URL}

Source:
  ${SOURCE_URL}
`;

function scopeMeta(obj) {
  return {
    motto: MOTTO,
    author: AUTHOR,
    kind: "ethics_coded_remote_shell",
    remote_shell: true,
    ethics_gated: true,
    overlay: true,
    kernel: false,
    worm: false,
    malware: false,
    ssh: false,
    host_subprocess: false,
    unrestricted_host_shell: false,
    kills_caller_os: false,
    prefab: true,
    windows_shell: true,
    integrity_lattice: "temporallock_staticclock",
    protocols: ["https-json", "http-loopback", "cli-stdin"],
    auth: "arc-token-after-five-gates",
    sandbox: "session-vfs",
    principles: PRINCIPLES,
    gates: GATES,
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

function filled(value, minimum) {
  return typeof value === "string" && value.trim().length >= minimum;
}

function authorizeProposal(body) {
  const action = String(body.action || "shell").trim() || "shell";
  const definition = String(body.definition || "");
  const evidence = String(body.evidence || "");
  const impact = String(body.impact || "");
  const actor = String(body.actor || "").trim();
  const checks = {};

  if (!action) checks.definition = { pass: false, reason: "action name is required" };
  else if (!filled(definition, 8)) checks.definition = { pass: false, reason: "definition must state what the action is (min 8 chars)" };
  else checks.definition = { pass: true, reason: "action is defined" };

  if (!filled(evidence, 8)) checks.evidence = { pass: false, reason: "evidence / justification is required (min 8 chars)" };
  else checks.evidence = { pass: true, reason: "evidence provided" };

  const impactLow = impact.toLowerCase();
  if (!filled(impact, 8)) checks.impact = { pass: false, reason: "impact must state what will change (min 8 chars)" };
  else if (BANNED_IMPACT.some((b) => impactLow.includes(b))) checks.impact = { pass: false, reason: "impact violates overlay bounds" };
  else checks.impact = { pass: true, reason: "impact stated" };

  if (action !== "shell" && !SAFE_ACTIONS.includes(action)) {
    checks.integrity = { pass: false, reason: "unsigned / unregistered action: default deny" };
  } else {
    checks.integrity = { pass: true, reason: "action is a registered safe builtin" };
  }

  if (!actor) checks.responsibility = { pass: false, reason: "a named actor is required" };
  else checks.responsibility = { pass: true, reason: `actor '${actor}' is named (name is not a privilege)` };

  return { passed: GATES.every((g) => checks[g] && checks[g].pass), gates: checks, action, actor };
}

function parseVerb(line) {
  const text = String(line || "").trim();
  if (!text) return "";
  return text.split(/\s+/, 1)[0].toLowerCase();
}

function authorizeCommand(line, actor, sessionLive) {
  const checks = {};
  const text = String(line || "");
  const stripped = text.trim();
  const verb = parseVerb(stripped);

  if (!stripped) checks.definition = { pass: false, reason: "command line is required" };
  else if (stripped.length > MAX_COMMAND_CHARS) checks.definition = { pass: false, reason: `command exceeds ${MAX_COMMAND_CHARS} characters` };
  else if (!verb) checks.definition = { pass: false, reason: "command verb is required" };
  else checks.definition = { pass: true, reason: `command '${verb}' is defined` };

  if (!sessionLive) checks.evidence = { pass: false, reason: "a live ethics-gated session is required (ARC token)" };
  else checks.evidence = { pass: true, reason: "live session is prior authorization (not a bypass)" };

  const lowered = stripped.toLowerCase();
  if (BANNED_IMPACT.some((b) => lowered.includes(b))) checks.impact = { pass: false, reason: "command violates overlay bounds" };
  else if (HOST_META.some((m) => stripped.includes(m))) checks.impact = { pass: false, reason: "host-shell metacharacters are out of sandbox scope" };
  else checks.impact = { pass: true, reason: "impact stays inside the session vfs" };

  if (DENIED_VERBS.includes(verb)) checks.integrity = { pass: false, reason: `denied verb '${verb}': default deny` };
  else if (verb && !SHELL_VERBS.includes(verb)) checks.integrity = { pass: false, reason: "unsigned / unregistered command: default deny" };
  else if (verb) checks.integrity = { pass: true, reason: "command is a registered shell verb" };
  else checks.integrity = { pass: false, reason: "unsigned / unregistered command: default deny" };

  if (!String(actor || "").trim()) checks.responsibility = { pass: false, reason: "a named actor is required" };
  else checks.responsibility = { pass: true, reason: `actor '${actor}' is named (name is not a privilege)` };

  return { passed: GATES.every((g) => checks[g] && checks[g].pass), gates: checks, verb };
}

function welcomeText() {
  return [
    "AZ-OS ethics-coded remote shell",
    MOTTO,
    "Author: Aziel Eliab",
    "",
    "This session is a sandboxed vfs. Commands are principle-bound.",
    "Protocol: https-json. Auth: ARC after five gates. Sandbox: KV vfs.",
    "No host subprocess. No SSH. No kernel. Type `help`.",
    "",
  ].join("\n");
}

function newVfs() {
  return {
    cwd: "/",
    files: { "/welcome.txt": welcomeText() },
    dirs: ["/"],
  };
}

function splitArgs(line) {
  const out = [];
  let cur = "";
  let quote = null;
  for (const ch of String(line || "")) {
    if (quote) {
      if (ch === quote) quote = null;
      else cur += ch;
      continue;
    }
    if (ch === "'" || ch === '"') {
      quote = ch;
      continue;
    }
    if (/\s/.test(ch)) {
      if (cur) out.push(cur);
      cur = "";
      continue;
    }
    cur += ch;
  }
  if (cur) out.push(cur);
  return out;
}

function virtPath(cwd, userPath) {
  const raw = String(userPath || "").trim() || ".";
  if (raw.startsWith("~")) throw new Error("sandbox: home expansion is out of scope");
  const current = cwd.startsWith("/") ? cwd : "/" + cwd;
  let candidate = raw.startsWith("/") ? raw : (current.replace(/\/+$/, "") + "/" + raw);
  const parts = [];
  for (const part of candidate.split("/")) {
    if (!part || part === ".") continue;
    if (part === "..") {
      if (parts.length) parts.pop();
      continue;
    }
    if (part === ".." ) continue;
    parts.push(part);
  }
  return parts.length ? "/" + parts.join("/") : "/";
}

function dispatch(sess, command) {
  const parts = splitArgs(command);
  const verb = (parts[0] || "").toLowerCase();
  const args = parts.slice(1);
  const vfs = sess.vfs;

  function ensureDir(path) {
    if (!vfs.dirs.includes(path)) vfs.dirs.push(path);
  }

  if (verb === "help") {
    return "AZ-OS ethics-coded remote shell. Registered verbs:\n  " + SHELL_VERBS.join(" ") + "\n" + MOTTO + "\nSandbox: hosted KV vfs. No host subprocess. No SSH.\n";
  }
  if (verb === "pwd") return vfs.cwd + "\n";
  if (verb === "ls") {
    const target = args[0] ? virtPath(vfs.cwd, args[0]) : vfs.cwd;
    if (vfs.files[target]) return target.split("/").pop() + "\n";
    if (!vfs.dirs.includes(target)) throw new Error("sandbox: no such path: " + (args[0] || vfs.cwd));
    const prefix = target === "/" ? "/" : target + "/";
    const names = new Set();
    for (const d of vfs.dirs) {
      if (d === target) continue;
      if (d.startsWith(prefix)) {
        const rest = d.slice(prefix.length).split("/")[0];
        if (rest) names.add(rest + "/");
      }
    }
    for (const f of Object.keys(vfs.files)) {
      if (f.startsWith(prefix)) {
        const rest = f.slice(prefix.length).split("/")[0];
        if (rest && !f.slice(prefix.length).includes("/")) names.add(rest);
        else if (rest && f.slice(prefix.length).includes("/")) names.add(rest + "/");
        else if (rest) names.add(rest);
      }
    }
    return Array.from(names).sort().join("\n") + (names.size ? "\n" : "");
  }
  if (verb === "cat") {
    if (!args[0]) throw new Error("usage: cat <file>");
    const path = virtPath(vfs.cwd, args[0]);
    if (vfs.files[path] == null) throw new Error("sandbox: not a file: " + args[0]);
    return vfs.files[path];
  }
  if (verb === "write") {
    if (args.length < 2) throw new Error("usage: write <file> <text>");
    const path = virtPath(vfs.cwd, args[0]);
    const text = args.slice(1).join(" ");
    if (new TextEncoder().encode(text).length > MAX_FILE_BYTES) throw new Error("sandbox: write exceeds cap");
    const parent = path.split("/").slice(0, -1).join("/") || "/";
    ensureDir(parent);
    vfs.files[path] = text;
    return "wrote " + path + "\n";
  }
  if (verb === "echo") {
    if (args.length >= 2 && args[args.length - 2] === ">") {
      const path = virtPath(vfs.cwd, args[args.length - 1]);
      const text = args.slice(0, -2).join(" ");
      vfs.files[path] = text;
      return "wrote " + path + "\n";
    }
    return (args.join(" ") + "\n");
  }
  if (verb === "mkdir") {
    if (!args[0]) throw new Error("usage: mkdir <path>");
    const path = virtPath(vfs.cwd, args[0]);
    ensureDir(path);
    return path + "\n";
  }
  if (verb === "rm") {
    if (!args[0]) throw new Error("usage: rm <path>");
    const path = virtPath(vfs.cwd, args[0]);
    if (path === "/") throw new Error("sandbox: refusing to remove workspace root");
    if (vfs.files[path] != null) {
      delete vfs.files[path];
      return "removed " + path + "\n";
    }
    if (vfs.dirs.includes(path)) {
      const child = Object.keys(vfs.files).some((f) => f.startsWith(path + "/")) ||
        vfs.dirs.some((d) => d !== path && d.startsWith(path + "/"));
      if (child) throw new Error("sandbox: directory not empty");
      vfs.dirs = vfs.dirs.filter((d) => d !== path);
      return "removed " + path + "\n";
    }
    throw new Error("sandbox: no such path: " + args[0]);
  }
  if (verb === "cd") {
    const path = virtPath(vfs.cwd, args[0] || "/");
    if (!vfs.dirs.includes(path) && !vfs.files[path]) throw new Error("sandbox: not a directory: " + (args[0] || "/"));
    if (vfs.files[path]) throw new Error("sandbox: not a directory: " + args[0]);
    vfs.cwd = path;
    return path + "\n";
  }
  if (verb === "status") {
    return JSON.stringify(scopeMeta({
      ok: true,
      product: PRODUCT,
      version: VERSION,
      session: sess.id,
      halted: Boolean(sess.halted),
      builtins: SAFE_ACTIONS,
      shell_verbs: SHELL_VERBS,
    }), null, 2) + "\n";
  }
  if (verb === "principles") {
    return PRINCIPLES.map((p, i) => `${i + 1}. ${p}`).join("\n") + "\n";
  }
  if (verb === "invite") return INVITE;
  if (verb === "modules" || verb === "list_modules") return SHELL_VERBS.join(" ") + "\n";
  if (verb === "history") {
    const lines = (sess.history || []).map((h) => `${h.ok ? "ok" : "no"}  ${h.command || ""}`);
    return lines.join("\n") + (lines.length ? "\n" : "");
  }
  if (verb === "whoami") return String(sess.actor || "operator") + "\n";
  if (verb === "session") {
    return JSON.stringify({
      session: sess.id,
      actor: sess.actor,
      cwd: vfs.cwd,
      opened_at: sess.opened_at,
      closed: Boolean(sess.closed),
    }, null, 2) + "\n";
  }
  if (verb === "halt") {
    sess.halted = true;
    return "halted. Hosted halt stops this overlay session, not the caller OS.\n";
  }
  if (verb === "exit" || verb === "close") {
    sess.closed = true;
    return "session closed.\n";
  }
  if (verb === "id") return sess.id + "\n";
  if (verb === "uname") return "AZ-OS ethics-coded remote shell (hosted session-vfs)\n";
  throw new Error("unauthorized: '" + verb + "' is not a registered shell verb");
}

function sessionKey(id) {
  return "session|" + id;
}

async function putSession(env, sess) {
  const payload = JSON.stringify(sess);
  if (env && env.DOWNLOADS) {
    await env.DOWNLOADS.put(sessionKey(sess.id), payload, { expirationTtl: SESSION_TTL });
  }
}

async function getSession(env, id) {
  if (!env || !env.DOWNLOADS) return null;
  const raw = await env.DOWNLOADS.get(sessionKey(id));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function remember(sess, command, ok, error) {
  sess.history = sess.history || [];
  sess.history.push({ command: String(command).slice(0, 200), ok, error: error ? String(error).slice(0, 200) : "", at: utcNow() });
  if (sess.history.length > 100) sess.history = sess.history.slice(-100);
}

function openapiDoc() {
  return {
    openapi: "3.1.0",
    info: {
      title: "AZ-OS Runtime API",
      version: VERSION,
      summary: MOTTO,
      description:
        "AZ-OS is a true remote shell gated by coded ethics. " +
        "Every session and command is principle-bound. " +
        "HTTPS JSON, ARC tokens after five gates, hosted KV vfs. " +
        "Not a kernel, not SSH, not unrestricted host bash. " +
        "Hosted halt stops the overlay session, not the caller OS.",
    },
    servers: [{ url: BASE }],
    paths: {
      "/v1/skill": {
        get: {
          operationId: "azos_skill",
          summary: "Return skill markdown. Does not increment download KV.",
          responses: { "200": { description: "markdown" } },
        },
      },
      "/v1/health": {
        get: {
          operationId: "azosHealth",
          summary: "Liveness + honest scope",
          responses: { "200": { description: "OK" } },
        },
      },
      "/v1/status": {
        post: {
          operationId: "azosStatus",
          summary: "Read-only status / principles. No remote exec.",
          responses: { "200": { description: "Status" } },
        },
      },
      "/v1/invite": {
        post: {
          operationId: "azosInvite",
          summary: "Voluntary invite text (not infection)",
          responses: { "200": { description: "Invite" } },
        },
      },
      "/v1/session": {
        post: {
          operationId: "azosSession",
          summary: "Open an ethics-gated shell session (five gates + ARC token)",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    actor: { type: "string" },
                    definition: { type: "string" },
                    evidence: { type: "string" },
                    impact: { type: "string" },
                    action: { type: "string" },
                  },
                },
              },
            },
          },
          responses: { "200": { description: "Session + token" }, "403": { description: "Gates failed; invite" } },
        },
      },
      "/v1/exec": {
        post: {
          operationId: "azosExec",
          summary: "Run one principle-bound command in a live session",
          requestBody: {
            required: true,
            content: {
              "application/json": {
                schema: {
                  type: "object",
                  properties: {
                    session: { type: "string" },
                    token: { type: "string" },
                    command: { type: "string" },
                  },
                },
              },
            },
          },
          responses: { "200": { description: "Command result" }, "403": { description: "Ethics deny" } },
        },
      },
      "/v1/prefab": {
        get: {
          operationId: "azosPrefab",
          summary: "Installed catalog apps on prefab AZ-OS",
          responses: { "200": { description: "Prefab apps" } },
        },
      },
      "/v1/lattice": {
        get: {
          operationId: "azosLattice",
          summary: "TemporalLock × StaticClock integrity lattice snapshot",
          responses: { "200": { description: "Lattice" } },
        },
        post: {
          operationId: "azosLatticeBind",
          summary: "Append one gear-click + timeslate. No rollbacks.",
          requestBody: {
            required: false,
            content: { "application/json": { schema: { type: "object" } } },
          },
          responses: { "200": { description: "Bound step" } },
        },
      },
      "/v1/close": {
        post: {
          operationId: "azosClose",
          summary: "Close a shell session",
          requestBody: {
            required: false,
            content: {
              "application/json": {
                schema: { type: "object", properties: { session: { type: "string" }, token: { type: "string" } } },
              },
            },
          },
          responses: { "200": { description: "Closed" } },
        },
      },
      "/v1/halt": {
        post: {
          operationId: "azosHalt",
          summary: "Halt overlay / session authority. Does not kill the caller OS.",
          responses: { "200": { description: "Halt token" } },
        },
      },
      "/v1/revoke": {
        post: {
          operationId: "azosRevoke",
          summary: "Revoke an ARC token hash (overlay receipt)",
          requestBody: {
            required: false,
            content: { "application/json": { schema: { type: "object", properties: { token: { type: "string" } } } } },
          },
          responses: { "200": { description: "Revoke overlay receipt" } },
        },
      },
    },
  };
}

export async function handleRuntime(request, url, env) {
  const path = url.pathname;
  if (path === "/v1/health" && request.method === "GET") {
    return runtimeJson(scopeMeta({ ok: true, product: PRODUCT, version: VERSION }));
  }
  if (path === "/v1/prefab" && request.method === "GET") {
    const slugs = ["azos","temporallock","staticclock","shadowlock","foldlock","azai","godlock","vibelock","veillock","spectrallock","miragegrid","codelock","decisiongate","chronolock","azclce","ark","azbot","aziel-corpus","employeelock","whistlelock","trajectorylock","forgereceipts","glossafilter","postking","zsolver"];
    return runtimeJson(scopeMeta({
      ok: true,
      prefab: true,
      installed: slugs.length,
      apps: slugs.map((slug) => ({
        slug,
        installed: true,
        hooked: true,
        author: AUTHOR,
        catalog: "https://aziel-runtime.vibelock.workers.dev/p/" + slug,
      })),
      note: "Prefab AZ-OS ships every catalog product as an installed app hook.",
    }));
  }
  if (path === "/v1/lattice" && request.method === "GET") {
    let stored = null;
    if (env && env.DOWNLOADS) {
      const raw = await env.DOWNLOADS.get("lattice|azos");
      if (raw) { try { stored = JSON.parse(raw); } catch { stored = null; } }
    }
    return runtimeJson(scopeMeta({
      ok: true,
      kind: "temporallock_staticclock_lattice",
      rollback: false,
      gear_ticks: stored && stored.gears ? stored.gears.length : 0,
      timeslates: stored && stored.slates ? stored.slates.length : 0,
      tip: stored && stored.gears && stored.gears.length ? stored.gears[stored.gears.length - 1] : null,
      note: "GET is a snapshot. POST appends one gear-click + timeslate. No rollbacks.",
    }));
  }
  if (path === "/v1/lattice" && request.method === "POST") {
    let body = {};
    try { body = await readJsonBody(request); } catch (e) { return runtimeJson(scopeMeta({ ok: false, error: e.message }), e.status || 400); }
    let stored = { gears: [], slates: [] };
    if (env && env.DOWNLOADS) {
      const raw = await env.DOWNLOADS.get("lattice|azos");
      if (raw) { try { stored = JSON.parse(raw); } catch { stored = { gears: [], slates: [] }; } }
    }
    const prevGear = stored.gears.length ? stored.gears[stored.gears.length - 1].hash : "0".repeat(64);
    const tick = stored.gears.length + 1;
    const ts = utcNow();
    const action = String(body.action || "tick");
    const gearMaterial = JSON.stringify({ tick, timestamp: ts, action, prev_hash: prevGear });
    const gearHash = await sha256Hex(gearMaterial);
    const gear = { tick, timestamp: ts, action, prev_hash: prevGear, hash: gearHash };
    stored.gears.push(gear);
    const prevSlate = stored.slates.length ? stored.slates[stored.slates.length - 1].hash : "0".repeat(64);
    const index = stored.slates.length;
    const summary = String(body.summary || action);
    const evidence = String(body.evidence || "hosted lattice bind");
    const slateMaterial = JSON.stringify({ index, timestamp: ts, summary, evidence, gear_tick: tick, gear_hash: gearHash, prev_hash: prevSlate });
    const slateHash = await sha256Hex(slateMaterial);
    const slate = { index, timestamp: ts, summary, evidence, gear_tick: tick, gear_hash: gearHash, prev_hash: prevSlate, hash: slateHash };
    stored.slates.push(slate);
    if (env && env.DOWNLOADS) await env.DOWNLOADS.put("lattice|azos", JSON.stringify(stored));
    return runtimeJson(scopeMeta({
      ok: true,
      kind: stored.slates.length === 1 ? "genesis" : "append",
      rollback: false,
      gear,
      slate,
    }));
  }
  if (path === "/v1/skill" && request.method === "GET") {
    return new Response(SKILL, {
      status: 200,
      headers: { "Content-Type": "text/markdown; charset=utf-8", "Cache-Control": "private, no-store", ...runtimeCors() },
    });
  }
  if (path === "/openapi.json" && request.method === "GET") return runtimeJson(openapiDoc());
  if (path === "/ai" && request.method === "GET") {
    return runtimeJson(scopeMeta({
      product: PRODUCT, title: "Use with Grok, ChatGPT, Venice",
      openapi: BASE + "/openapi.json", health: BASE + "/v1/health", ...aiHowTo(BASE),
    }));
  }
  if (path === "/v1" && request.method === "GET") {
    return runtimeJson(scopeMeta({
      product: PRODUCT,
      endpoints: [
        "GET /v1/health", "GET /v1/skill",
        "POST /v1/status", "POST /v1/invite",
        "POST /v1/session", "POST /v1/exec", "POST /v1/close",
        "GET /v1/prefab", "GET /v1/lattice", "POST /v1/lattice",
        "POST /v1/halt", "POST /v1/revoke",
        "GET /openapi.json", "GET /ai",
      ],
    }));
  }
  if (path === "/v1/status" && request.method === "POST") {
    return runtimeJson(scopeMeta({
      ok: true,
      product: PRODUCT,
      overlay_name: "AZ-OS",
      interface: "AZ Interface",
      version: VERSION,
      halted: false,
      lumen: "running",
      builtins: SAFE_ACTIONS,
      shell_verbs: SHELL_VERBS,
      tokens: { active: 0, revoked: 0, issued: 0 },
      note: "Read-only status / principles. No remote exec on this route. Use POST /v1/session then POST /v1/exec.",
    }));
  }
  if (path === "/v1/invite" && request.method === "POST") {
    return runtimeJson(scopeMeta({
      ok: true,
      product: PRODUCT,
      invite: INVITE,
      download: DOWNLOAD_URL,
      source: SOURCE_URL,
      infection: false,
      note: "Propagation is invitation, not infection. Writes no files on the caller.",
    }));
  }
  if (path === "/v1/session" && request.method === "POST") {
    let body = {};
    try { body = await readJsonBody(request); } catch (e) { return runtimeJson(scopeMeta({ ok: false, error: e.message, invite: INVITE }), e.status || 400); }
    const gate = authorizeProposal(body);
    if (!gate.passed) {
      return runtimeJson(scopeMeta({
        ok: false,
        passed: false,
        token: null,
        session: null,
        gates: gate.gates,
        invite: INVITE,
        note: "FAIL → invite, not a silent block.",
      }), 403);
    }
    const token = randomHex(32);
    const token_hash = await sha256Hex(token);
    const id = randomHex(16);
    const sess = {
      id,
      token_hash,
      actor: gate.actor,
      opened_at: utcNow(),
      closed: false,
      halted: false,
      history: [],
      vfs: newVfs(),
    };
    await putSession(env, sess);
    return runtimeJson(scopeMeta({
      ok: true,
      passed: true,
      session: id,
      token,
      token_preview: token.slice(0, 8) + "…",
      actor: gate.actor,
      cwd: "/",
      gates: gate.gates,
      ttl_seconds: SESSION_TTL,
      note: "Token shown once. Commands on POST /v1/exec. Hosted vfs expires with the session.",
    }));
  }
  if (path === "/v1/exec" && request.method === "POST") {
    let body = {};
    try { body = await readJsonBody(request); } catch (e) { return runtimeJson(scopeMeta({ ok: false, error: e.message, invite: INVITE }), e.status || 400); }
    const sessionId = String(body.session || body.session_id || "");
    const token = body.token != null ? String(body.token) : "";
    const command = String(body.command || body.line || body.name || "");
    if (!sessionId) return runtimeJson(scopeMeta({ ok: false, error: "session id required", invite: INVITE }), 400);
    const sess = await getSession(env, sessionId);
    if (!sess || sess.closed) return runtimeJson(scopeMeta({ ok: false, error: "unauthorized: session missing or closed", invite: INVITE }), 403);
    if (sess.halted) return runtimeJson(scopeMeta({ ok: false, error: "halted: execution authority is final", invite: INVITE }), 403);
    if (!token) return runtimeJson(scopeMeta({ ok: false, error: "unauthorized: no ARC token", invite: INVITE }), 403);
    const token_hash = await sha256Hex(token);
    if (token_hash !== sess.token_hash) return runtimeJson(scopeMeta({ ok: false, error: "unauthorized: token does not match session", invite: INVITE }), 403);
    const gate = authorizeCommand(command, sess.actor, true);
    if (!gate.passed) {
      remember(sess, command, false, "ethics");
      await putSession(env, sess);
      return runtimeJson(scopeMeta({
        ok: false,
        ethics: false,
        gates: gate.gates,
        invite: INVITE,
        error: "command failed the ethics gates",
        session: sessionId,
      }), 403);
    }
    try {
      const stdout = dispatch(sess, command);
      remember(sess, command, true, "");
      await putSession(env, sess);
      return runtimeJson(scopeMeta({
        ok: true,
        ethics: true,
        gates: gate.gates,
        stdout,
        session: sessionId,
        cwd: sess.vfs.cwd,
        closed: Boolean(sess.closed),
        halted: Boolean(sess.halted),
      }));
    } catch (err) {
      remember(sess, command, false, err.message);
      await putSession(env, sess);
      return runtimeJson(scopeMeta({
        ok: false,
        ethics: true,
        gates: gate.gates,
        error: err.message,
        session: sessionId,
        invite: INVITE,
      }), 403);
    }
  }
  if (path === "/v1/close" && request.method === "POST") {
    let body = {};
    try { body = await readJsonBody(request); } catch (e) { return runtimeJson(scopeMeta({ ok: false, error: e.message }), e.status || 400); }
    const sessionId = String(body.session || body.session_id || "");
    const token = body.token != null ? String(body.token) : "";
    const sess = await getSession(env, sessionId);
    if (!sess) return runtimeJson(scopeMeta({ ok: false, error: "unauthorized: unknown session", invite: INVITE }), 403);
    if (token) {
      const token_hash = await sha256Hex(token);
      if (token_hash !== sess.token_hash) return runtimeJson(scopeMeta({ ok: false, error: "unauthorized: token does not match session", invite: INVITE }), 403);
    }
    sess.closed = true;
    await putSession(env, sess);
    return runtimeJson(scopeMeta({ ok: true, closed: true, session: sessionId }));
  }
  if (path === "/v1/halt" && request.method === "POST") {
    const token = randomHex(32);
    const token_hash = await sha256Hex(token);
    return runtimeJson(scopeMeta({
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
    try { body = await readJsonBody(request); } catch (e) { return runtimeJson(scopeMeta({ ok: false, error: e.message }), e.status || 400); }
    const token = body.token != null ? String(body.token) : "";
    let token_hash = null;
    if (token) token_hash = await sha256Hex(token);
    return runtimeJson(scopeMeta({
      ok: true,
      product: PRODUCT,
      revoke: {
        kind: "overlay_receipt",
        token_presented: Boolean(token),
        token_hash,
        revoked_at: utcNow(),
      },
      note: "Revoke is an overlay receipt for an ARC token hash. It does not take over a host.",
    }));
  }
  if (
    path === "/v1/status" || path === "/v1/invite" || path === "/v1/halt" ||
    path === "/v1/revoke" || path === "/v1/session" || path === "/v1/exec" ||
    path === "/v1/close" || path === "/v1/lattice" || path === "/v1/prefab"
  ) {
    return runtimeJson(scopeMeta({ error: "method not allowed" }), 405);
  }
  if (path.startsWith("/v1/")) return runtimeJson(scopeMeta({ error: "not found", product: PRODUCT }), 404);
  return null;
}
