/**
 * AZ-OS product homepage. Human surface — fully developed software.
 * Author: Aziel Eliab. Apache-2.0. Not a kernel. Not a VPN.
 */

export const HOST = "https://azos-download-tracker.vibelock.workers.dev";
export const GITHUB_REPO = "https://github.com/AzielEliab/azos";
export const GITHUB_LATEST = "https://github.com/AzielEliab/azos/releases/latest";
export const CATALOG = "https://aziel-runtime.vibelock.workers.dev/";
export const AUTHOR = "Aziel Eliab";
export const TITLE = "AZ-OS — Aziel Eliab";
export const MOTTO = "Integrity precedes execution.";
export const VERSION = "0.3.0";
export const DEFAULT_ASSET = "azos-0.3.0.tar.gz";
export const INSTALL_LINE =
  "curl -fsSL https://azos-download-tracker.vibelock.workers.dev/install.sh | bash";

export const ONE_LINE =
  "Prefab ethics-coded remote shell and AZ Interface by Aziel Eliab; not a kernel, VPN, or remote takeover.";

const PRINCIPLES = [
  "Integrity precedes execution.",
  "Time-bound actions are final.",
  "Understanding precedes modification.",
  "The system protects itself architecturally.",
  "Propagation is not infection.",
];

const PREFAB_META = {
  azos: ["AZ-OS Shell", "Ethics-coded remote shell. Integrity precedes execution."],
  temporallock: ["TemporalLock", "Immutable timeslate lattice hash-chained to StaticClock. No rollbacks."],
  staticclock: ["StaticClock", "Gear-click timeline. Every action locks forward."],
  shadowlock: ["ShadowLock", "Ethics-policy observation of jobs and processes."],
  foldlock: ["FoldLock", "SOTA UNI1 compression engine for UTF-8 text."],
  azai: ["AZAI / JEEVES", "True local AI stack. Jeeves is not sovereign."],
  godlock: ["GodLock", "Empirical knowledge stress-test. Client hook to godlock.uk. Not a VPN."],
  vibelock: ["VibeLock", "Deepfake detection via physics and unnatural media shifts."],
  veillock: ["VeilLock", "Camera/video obfuscation hook unless the operator accepts a call."],
  spectrallock: ["SpectralLock", "Rosetta spectral / OCR-family overlays."],
  miragegrid: ["MirageGrid", "Node-mesh VPN. Distinct from AZ-OS — AZ-OS is not a VPN."],
  codelock: ["CodeLock", "Canonical or Rosetta HTML view of source."],
  decisiongate: ["DecisionGATE", "Five sequential gates. Freedom without clarity is chaos."],
  chronolock: ["ChronoLock", "Advisory temporal window. Not a scheduler."],
  azclce: ["AZ-CLCE", "Inconsistency detection. Type D is a label, not malice."],
  ark: ["The ARK", "Mode E heuristics sweep. Not a kernel. Never stores vaults."],
  azbot: ["AZBot", "Skill, not a model. Public HTTPS only."],
  "aziel-corpus": ["Aziel Digital Library", "Public MASTER library. Anonymous GET is read-only."],
  employeelock: ["EmployeeLock", "Hash-chained accountability workbook. Not a court."],
  whistlelock: ["WhistleLock", "Local drop ledger + dead-man copy. Not a mailer."],
  trajectorylock: ["TrajectoryLock", "Auditable geometric test. Not a certified forensic instrument."],
  forgereceipts: ["ForgeReceipts", "Local receipt / checklist helper. Not legal advice."],
  glossafilter: ["Glossa Filter", "Render an intent across bundled peer ids."],
  postking: ["Post-King Chess", "The goal is to remain. Human is king-bound."],
  zsolver: ["ZionPattern Solver", "Hard 75% confidence cap. Provisional."],
};

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function citeDocument() {
  return {
    author: AUTHOR,
    title: "AZ-OS",
    one_line: ONE_LINE,
    github: GITHUB_REPO,
    download: HOST + "/download",
    homepage: HOST + "/",
    doi: null,
    license: "Apache-2.0",
    catalog: CATALOG,
    cite:
      "Aziel Eliab. AZ-OS. " +
      GITHUB_REPO +
      ". " +
      HOST +
      ". Apache-2.0.",
  };
}

export function jsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "AZ-OS",
    alternateName: "AZ Interface",
    softwareVersion: VERSION,
    applicationCategory: "DeveloperApplication",
    operatingSystem: "Linux, macOS, Windows (Python overlay; not a kernel)",
    author: {
      "@type": "Person",
      name: AUTHOR,
      url: "https://github.com/AzielEliab",
    },
    creator: { "@type": "Person", name: AUTHOR },
    codeRepository: GITHUB_REPO,
    downloadUrl: HOST + "/download",
    installUrl: HOST + "/install.sh",
    license: "https://www.apache.org/licenses/LICENSE-2.0",
    url: HOST + "/",
    image: HOST + "/sigil.png",
    isAccessibleForFree: true,
    offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
    description: ONE_LINE,
  };
}

/** Wordless rose-star brand mark (no text). Official PNG is public/sigil.png. */
export function sigilSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" role="img" aria-label="">
  <defs>
    <linearGradient id="g" x1="20%" y1="10%" x2="90%" y2="90%">
      <stop offset="0%" stop-color="#f3d57a"/>
      <stop offset="45%" stop-color="#e4b84a"/>
      <stop offset="100%" stop-color="#b8862a"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="2.2" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <rect width="256" height="256" fill="none"/>
  <g fill="none" stroke="url(#g)" stroke-width="1.15" opacity="0.55">
    <animate attributeName="opacity" values="0.38;0.7;0.38" dur="6s" repeatCount="indefinite"/>
    <path d="M38,128 C38,62 62,38 128,38 C86,70 74,118 92,168 C104,198 78,214 52,188"/>
    <path d="M218,128 C218,194 194,218 128,218 C170,186 182,138 164,88 C152,58 178,42 204,68"/>
    <path d="M48,78 C88,28 168,22 208,72 C176,48 148,64 142,98"/>
    <path d="M208,178 C168,228 88,234 48,184 C80,208 108,192 114,158"/>
    <path d="M28,148 C54,208 120,236 178,214"/>
    <path d="M228,108 C202,48 136,20 78,42"/>
    <circle cx="128" cy="128" r="118"/>
    <circle cx="128" cy="128" r="108"/>
  </g>
  <circle cx="128" cy="128" r="94" fill="none" stroke="url(#g)" stroke-width="3.2" filter="url(#glow)">
    <animate attributeName="r" values="92;96;92" dur="5.4s" repeatCount="indefinite"/>
  </circle>
  <g>
    <animateTransform attributeName="transform" type="scale" values="1;1.035;1" dur="4.8s" repeatCount="indefinite" additive="sum"/>
    <animateTransform attributeName="transform" type="translate" values="0 0;-4.5 -4.5;0 0" dur="4.8s" repeatCount="indefinite" additive="sum"/>
    <path fill="url(#g)" d="M128,38 L155.3,107.3 L228.2,107.6 L170.3,151.4 L191.6,222 L128,180.2 L64.4,222 L85.7,151.4 L27.8,107.6 L100.7,107.3 Z"/>
    <path fill="none" stroke="#1a1408" stroke-width="1.2" opacity="0.25" d="M128,38 L155.3,107.3 L228.2,107.6 L170.3,151.4 L191.6,222 L128,180.2 L64.4,222 L85.7,151.4 L27.8,107.6 L100.7,107.3 Z"/>
    <g fill="url(#g)" stroke="#8a6a1e" stroke-width="0.6">
      <path d="M128,86 C122,78 112,76 108,84 C104,92 114,98 122,96 C118,104 124,112 128,118 C132,112 138,104 134,96 C142,98 152,92 148,84 C144,76 134,78 128,86 Z"/>
      <path d="M128,92 C126,88 122,88 122,92 C122,96 126,98 128,100 C130,98 134,96 134,92 C134,88 130,88 128,92 Z"/>
      <path d="M128,118 L128,168"/>
      <path d="M128,138 C112,130 100,140 104,150 C108,158 120,154 128,146"/>
      <path d="M128,138 C144,130 156,140 152,150 C148,158 136,154 128,146"/>
    </g>
  </g>
</svg>`;
}

function breakdownList(stats) {
  const rows = stats.breakdown || [];
  if (!rows.length) return "<li>none yet</li>";
  return rows
    .map((b) => {
      const owner = escapeHtml(b.owner);
      const repo = escapeHtml(b.repo);
      const branch = escapeHtml(b.branch);
      const fork = escapeHtml(b.fork);
      const count = escapeHtml(b.count);
      return `<li><code>${owner}/${repo}</code> branch <code>${branch}</code> fork=${fork} → ${count}</li>`;
    })
    .join("");
}

export function renderHomepage(stats) {
  const views = Number(stats.views) || 0;
  const downloads = Number(stats.downloads != null ? stats.downloads : stats.total) || 0;
  const v = views.toLocaleString("en-US");
  const n = downloads.toLocaleString("en-US");
  const gh = stats.github || {};
  const cite = citeDocument();
  const ld = JSON.stringify(jsonLd(), null, 2);
  const principles = PRINCIPLES.map((p, i) => `<li><b>${i + 1}.</b> ${escapeHtml(p)}</li>`).join("");
  const prefabHints = Object.entries(PREFAB_META)
    .map(([slug, meta]) => `<option value="${escapeHtml(slug)}">${escapeHtml(meta[0])}</option>`)
    .join("");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${TITLE}</title>
  <meta name="description" content="${escapeHtml(ONE_LINE)}">
  <meta name="author" content="${AUTHOR}">
  <meta name="robots" content="index,follow">
  <link rel="canonical" href="${HOST}/">
  <link rel="icon" type="image/png" href="/sigil.png">
  <meta property="og:title" content="${TITLE}">
  <meta property="og:description" content="${escapeHtml(ONE_LINE)}">
  <meta property="og:url" content="${HOST}/">
  <meta property="og:type" content="website">
  <meta property="og:image" content="${HOST}/sigil.png">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="${TITLE}">
  <meta name="twitter:description" content="${escapeHtml(ONE_LINE)}">
  <script type="application/ld+json">${ld}</script>
  <!-- gitbaby-seo -->
  <style>
    :root {
      color-scheme: dark;
      --bg: #070705;
      --panel: #10100c;
      --panel2: #16140e;
      --ink: #f4ecd0;
      --muted: #a89868;
      --line: #3a3018;
      --gold: #e4b84a;
      --gold2: #f3d57a;
      --pass: #7dcf9a;
      --fail: #e07a7a;
      --shadow: 0 18px 48px #000a;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; background: var(--bg); color: var(--ink);
      font: 16px/1.45 "Segoe UI", ui-sans-serif, system-ui, sans-serif; }
    body {
      background:
        radial-gradient(900px 520px at 12% -10%, #3a2a10 0%, transparent 55%),
        radial-gradient(800px 480px at 110% 10%, #2a220c 0%, transparent 50%),
        var(--bg);
    }
    a { color: var(--gold2); }
    code, pre { font-family: ui-monospace, Consolas, monospace; }
    .wrap { max-width: 72rem; margin: 0 auto; padding: 1.25rem 1.15rem 3.5rem; }
    header.top { display: flex; align-items: center; gap: 1rem; margin: 0 0 1rem; }
    .brandrow { display: flex; align-items: center; justify-content: flex-start; flex: 0 0 auto; }
    .brandmark { width: 40px; height: 40px; border-radius: 10px; object-fit: cover; flex: 0 0 auto;
      box-shadow: 0 0 0 1px #d4af3733; filter: drop-shadow(0 0 10px #e4b84a55); }
    header.top h1 { font-size: clamp(1.45rem, 3vw, 2rem); margin: 0; letter-spacing: .01em; color: var(--gold2); }
    .motto { color: var(--muted); margin: .2rem 0 0; }
    .meta-row { display: flex; flex-wrap: wrap; gap: .45rem .8rem; color: var(--muted); font-size: .86rem; margin-top: .35rem; }
    .banners { display: grid; gap: .65rem; margin: 0 0 1.1rem; }
    .banner { border: 1px solid #5c4a1a; background: #1a1508; color: #f0d78c; padding: .75rem .9rem; border-radius: 8px; font-size: .92rem; }
    .banner.limit { border-color: #4a4030; background: #12100c; color: #d8c89a; }
    .grid { display: grid; grid-template-columns: minmax(17rem, 22rem) 1fr; gap: 1rem; align-items: start; }
    @media (max-width: 860px) { .grid { grid-template-columns: 1fr; } header.top { align-items: flex-start; } }
    .card { border: 1px solid var(--line); border-radius: 12px; padding: 1.1rem 1.15rem; background: var(--panel); box-shadow: var(--shadow); }
    .card h2 { margin: 0 0 .7rem; font-size: 1.05rem; color: var(--gold); letter-spacing: .04em; text-transform: uppercase; }
    .nums { display: grid; grid-template-columns: 1fr 1fr; gap: .7rem; margin: 0 0 1rem; }
    .count { font-size: 2rem; font-variant-numeric: tabular-nums; font-weight: 750; margin: 0; color: var(--gold2); }
    .count span { display: block; font-size: .82rem; font-weight: 500; color: var(--muted); letter-spacing: .06em; text-transform: uppercase; }
    .btns { display: grid; grid-template-columns: 1fr 1fr; gap: .65rem; margin: 0 0 .75rem; }
    @media (max-width: 520px) { .btns { grid-template-columns: 1fr; } }
    a.btn, button.btn { display: block; width: 100%; box-sizing: border-box; text-align: center; font: inherit; font-size: 1.05rem; font-weight: 750; padding: .85rem 1rem; border-radius: 10px; border: 0; cursor: pointer; text-decoration: none; }
    a.btn.primary { background: var(--ink); color: #14110a; }
    button.btn.install { background: var(--gold); color: #14110a; }
    button.btn.install.copied { background: var(--pass); color: #0e1014; }
    a.btn.ghost, button.btn.ghost { background: transparent; color: var(--gold2); border: 1px solid var(--line); }
    pre.cmd { background: #070705; padding: .7rem .8rem; overflow: auto; border-radius: 8px; font-size: .78rem; border: 1px solid var(--line); color: #e8d9a0; }
    .kid { font-size: .95rem; margin: 0 0 .75rem; color: #ddd3b0; }
    .iso { font-size: .8rem; color: #8a7a4e; margin: .7rem 0 0; }
    .tabs { display: flex; flex-wrap: wrap; gap: .35rem; margin: 0 0 .85rem; }
    .tabs button { border: 1px solid var(--line); background: var(--panel2); color: var(--muted); border-radius: 999px; padding: .35rem .75rem; cursor: pointer; font: inherit; font-size: .85rem; }
    .tabs button[aria-selected="true"] { background: #2a230e; color: var(--gold2); border-color: var(--gold); }
    .panel { display: none; }
    .panel.on { display: block; }
    .fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr)); gap: .55rem; }
    .field { border: 1px solid var(--line); border-radius: 8px; padding: .55rem .65rem; background: #0c0b08; }
    .field b { display: block; font-size: .72rem; letter-spacing: .07em; text-transform: uppercase; color: var(--muted); }
    .chips { display: flex; flex-wrap: wrap; gap: .35rem; }
    .chip { border: 1px solid var(--line); border-radius: 999px; padding: .15rem .55rem; font-size: .78rem; color: var(--gold2); }
    .apps { display: grid; grid-template-columns: repeat(auto-fill, minmax(13.5rem, 1fr)); gap: .5rem; }
    .app { border: 1px solid var(--line); border-radius: 8px; padding: .55rem .65rem; background: #0c0b08; min-height: 5.2rem; }
    .app strong { display: block; color: var(--gold2); font-size: .9rem; }
    .app span { display: block; color: var(--muted); font-size: .78rem; margin-top: .2rem; }
    .gates { display: grid; gap: .35rem; }
    .gate { display: grid; grid-template-columns: 7.2rem 3.4rem 1fr; gap: .4rem; font-size: .85rem; align-items: start; }
    .pass { color: var(--pass); font-weight: 700; }
    .fail { color: var(--fail); font-weight: 700; }
    label.lab { display: block; font-size: .78rem; color: var(--muted); margin: .45rem 0 .2rem; }
    input[type=text], textarea, select { width: 100%; background: #0a0906; color: var(--ink); border: 1px solid var(--line); border-radius: 6px; padding: .45rem .55rem; font: inherit; }
    textarea { min-height: 3.1rem; resize: vertical; }
    .row { display: flex; gap: .5rem; flex-wrap: wrap; margin: .65rem 0; }
    button.act { background: #2a230e; color: var(--gold2); border: 1px solid var(--gold); border-radius: 6px; padding: .4rem .75rem; font-weight: 650; cursor: pointer; }
    button.act:disabled { opacity: .4; cursor: not-allowed; }
    .invite { white-space: pre-wrap; font-size: .82rem; background: #0a0906; border: 1px solid var(--line); padding: .7rem; border-radius: 8px; max-height: 22rem; overflow: auto; }
    .note { color: var(--muted); font-size: .88rem; }
    footer { margin: 1.4rem 0 0; color: var(--muted); font-size: .86rem; }
    footer ul { padding-left: 1.1rem; }
    .busy { color: var(--gold); font-size: .85rem; }
    #meshStrip { border: 1px solid var(--gold); border-radius: 12px; padding: .85rem 1rem; background: var(--panel2); margin: 0 0 1.1rem; display: flex; flex-wrap: wrap; align-items: center; gap: .7rem 1rem; font-size: .88rem; color: var(--muted); }
    #meshStrip .live { color: var(--ink); }
    #meshStrip .live b { color: var(--gold); font-size: 1.35rem; margin-right: .35rem; }
    #meshStrip .rollup b { color: var(--gold2); }
    #meshStrip button { font: 700 .78rem/1 ui-monospace, Menlo, Consolas, monospace; height: 2rem; padding: 0 .75rem; border-radius: 8px; background: #10100c; color: var(--ink); border: 1px solid var(--gold); cursor: pointer; }
    #meshStrip button:hover { background: #2a230e; color: var(--gold2); }
    #meshStrip input { width: 10rem; padding: .4rem .55rem; border: 1px solid var(--gold); border-radius: 8px; background: #0a0906; color: var(--ink); font: inherit; }
    #meshProducts { flex-basis: 100%; margin: 0; }
  </style>
</head>
<body>
  <div class="wrap">
    <header class="top">
      <div class="brandrow"><img class="brandmark" src="/sigil.png" width="40" height="40" alt="" decoding="async"></div>
      <div>
        <h1>AZ-OS — Aziel Eliab</h1>
        <p class="motto">${MOTTO} Author ${AUTHOR}.</p>
        <div class="meta-row">
          <span>v${VERSION}</span>
          <span>Apache-2.0</span>
          <span>Forks welcome</span>
          <a href="${GITHUB_REPO}">GitHub</a>
          <a href="${GITHUB_LATEST}">releases</a>
          <a href="/cite.json">cite.json</a>
        </div>
      </div>
    </header>

    <div class="banners">
      <p class="banner">THIS IS: prefab AZ-OS — ethics-coded remote shell with catalog software hooked in. Windows-style desktop locally; the sigil / brand mark (rose-star, no words) replaces a vendor logo. TemporalLock × StaticClock integrity lattice. Author Aziel Eliab only.</p>
      <p class="banner">THIS IS NOT: a kernel, bootloader, hypervisor, replacement OS, VPN, worm, malware, unrestricted host bash, or SSH. Halt stops overlay authority. It does not kill the caller OS.</p>
      <p class="banner limit">THIS WORKER is the public homepage + counted download + read-only hosted ops (status, invite, health, skill, prefab, lattice snapshot). Session, exec, and lattice bind persist in product-Worker KV and need full AZ-OS (<code>azos ui</code> / <code>azos shell</code>). The HTTP proxy is not the full OS.</p>
      <p class="banner" id="news-map">AZNews and 4DMap: this page has not read the join yet, so live, joined and merged read false here. It reads the aziel-runtime AzNewsStore through the FragGate door and checks the join itself: it opens the newest stored item's pin and confirms that pin leads back to the same item. Only when that round trip passes and the runtime's own join check agrees does this page show joined. AZNews can stand alone. 4DMap can stand alone. This page does not install 4DMap and keeps no copy of the news.</p>
      <div class="muted" id="news-map-pins" aria-label="Last 10 AZNews pins"></div>
      <p class="muted" id="news-map-runtime">The aziel-runtime 4DMap store runs AZNews on its own: real headlines from official outlet feeds, Open-Meteo weather, the computed sky, and colored pins with the last 10 added and a color key. AZ-OS keeps no copy and installs nothing. Open it through the runtime FragGate door: <a href="https://aziel-runtime.vibelock.workers.dev/aznews">AZNews globe</a> · <a href="/v1/newsmap/globe">/v1/newsmap/globe</a>.</p>
      <p class="banner" id="limits-plain">There is no kernel. The kernel base is absent. This has not booted. This is not installed as an operating system. This is not an operating system yet. The userspace base is present. That is a base, not a boot. An alternative internet is not live (alt_internet_live is false). A packet path is not live (packet_path_live is false). This isolate cannot see host hardware (worker_hardware is false). Still missing: a packet that leaves this machine and arrives on a different machine id. A same-machine mesh frame does not count. Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP. WireGuard, OpenVPN, an L3 exit pool, kernel UDP, and TUN/TAP stay SLOT. Public mail send, the kernel, and boot stay not live. The public door stays FG-STUB. Isolation is single-node security-awareness. Phoenix is a local wait and re-seal. That is not a loopback fence. Mail is not sent from here. One-click install is not live. This is not a live mesh node. Existing doors stay in place. App shells are not started.</p>
    </div>

    <div id="meshStrip" aria-label="Suite Live Nodes">
      <div class="live"><b id="meshLiveCount">0</b> Live Nodes</div>
      <div id="meshLine">This page is not a live mesh node. mesh_node_live stays false. The suite mesh proxy has not been read yet. The cite is QNM-BUILD-1.0 and QNS-CD-1.0. Not an anonymity network.</div>
      <div class="rollup">live <b id="qnmLive">0</b> · locked <b id="qnmLocked">0</b> · isolated <b id="qnmIsolated">0</b></div>
      <div>No Node Gate. No public qnsd proxy. No auto-heal. Those words are this page, not the proxied mode flags. Author Aziel Eliab only. This page does not start a mesh node.</div>
      <div>
        <input id="meshBearer" type="text" maxlength="80" placeholder="bearer (required to enable)" aria-label="mesh bearer">
        <button id="meshEnable" type="button" title="Forward enable to the runtime. Declared bearer required. This page is not a live mesh node.">Enable</button>
        <button id="meshDisable" type="button" title="Disable suite mesh (always allowed)">Disable</button>
        <button id="meshJoin" type="button" title="Join as azos. Refused while mesh is OFF. No auto-join.">Join</button>
        <button id="meshLeave" type="button" title="Leave this node. No auto-heal.">Leave</button>
      </div>
      <p id="meshProducts">The catalog mesh tools and the FragGate mesh door stay as they are. This page does not replace them. /v1/mesh is a proxy. QNS-CD-1.0 is a hub cite. Not an anonymity network. No public qnsd proxy.</p>
    </div>

    <div class="grid">
      <aside class="card" id="install">
        <h2>Install</h2>
        <div class="nums">
          <p class="count">${v}<span>Views</span></p>
          <p class="count">${n}<span>Live downloads</span></p>
        </div>
        <p class="kid"><strong>Two big buttons.</strong> Download saves the gzip (the Downloads number goes up). One-click install copies a Terminal command. One-click install is not live. It does not install an operating system and it does not boot one. After the command finishes, type <code>azos ui</code>.</p>
        <div class="btns">
          <a class="btn primary dl" href="/download?asset=${DEFAULT_ASSET}">Download</a>
          <button type="button" class="btn install" id="install-btn">One-click install</button>
        </div>
        <pre class="cmd" id="install-cmd">${INSTALL_LINE}</pre>
        <p class="kid">Then run: <code>azos ui</code> or <code>azos shell</code>. Interface: http://127.0.0.1:8800 (this computer only).</p>
        <div class="btns">
          <a class="btn ghost" href="${GITHUB_REPO}">GitHub</a>
          <a class="btn ghost" href="${GITHUB_LATEST}">Releases</a>
        </div>
        <p class="iso">The download count ticks on the Download click. The Worker serves the gzip (HTTP 200). No 302 to GitHub. Forks using this same link are counted automatically. ${DEFAULT_ASSET} — ${n} counted. Isolated counter: Worker <code>azos-download-tracker</code>, project <code>azos</code>, KV <code>AZOS_DOWNLOADS</code>. Not mixed with any other product. Not VibeLock. /v1 does not increment downloads.</p>
        <p class="iso">GitHub: stars ${gh.stars || 0} · forks ${gh.forks || 0} · watchers ${gh.watchers || 0} · release assets ${gh.release_download_count || 0}</p>
      </aside>

      <main class="card" id="workspace">
        <h2>Workspace</h2>
        <p class="note">Public Worker ops, rendered as software — not raw JSON. Status is read-only. Session-safe. Binding-only session / exec / lattice bind stay on full AZ-OS.</p>
        <div class="tabs" role="tablist">
          <button type="button" role="tab" aria-selected="true" data-tab="status">Status</button>
          <button type="button" role="tab" aria-selected="false" data-tab="invite">Invite</button>
          <button type="button" role="tab" aria-selected="false" data-tab="prefab">Prefab</button>
          <button type="button" role="tab" aria-selected="false" data-tab="lattice">Lattice</button>
          <button type="button" role="tab" aria-selected="false" data-tab="gates">Five gates</button>
          <button type="button" role="tab" aria-selected="false" data-tab="full">Full AZ-OS</button>
          <button type="button" role="tab" aria-selected="false" data-tab="cite">Cite</button>
        </div>
        <p class="busy" id="ws-busy" hidden>Reading Worker…</p>

        <section class="panel on" id="tab-status" role="tabpanel">
          <div class="fields" id="status-fields">
            <div class="field"><b>Lumen</b><span id="st-lumen">…</span></div>
            <div class="field"><b>Version</b><span id="st-version">${VERSION}</span></div>
            <div class="field"><b>Kind</b><span id="st-kind">This is an ethics-coded remote shell. It is not a kernel.</span></div>
            <div class="field"><b>Author</b><span>${AUTHOR}</span></div>
            <div class="field"><b>Kernel</b><span id="st-kernel">There is no kernel.</span></div>
            <div class="field"><b>VPN</b><span>AZ-OS is not a VPN.</span></div>
            <div class="field"><b>Host commands</b><span>This page does not run commands on the host computer.</span></div>
            <div class="field"><b>Halt</b><span>Halt stops new AZ-OS commands. It does not shut down the computer.</span></div>
          </div>
          <p id="st-limits" style="margin-top:.8rem">There is no kernel. The kernel base is absent. This has not booted. This is not installed as an operating system. This is not an operating system yet. The userspace base is present. That is a base, not a boot. An alternative internet is not live (alt_internet_live is false). A packet path is not live (packet_path_live is false). This isolate cannot see host hardware (worker_hardware is false). Still missing: a packet that leaves this machine and arrives on a different machine id. A same-machine mesh frame does not count. Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP. WireGuard, OpenVPN, an L3 exit pool, kernel UDP, and TUN/TAP stay SLOT. Public mail send, the kernel, and boot stay not live. The public door stays FG-STUB. Isolation is single-node security-awareness. Phoenix is a local wait and re-seal. That is not a loopback fence. Mail is not sent from here. One-click install is not live. This page is not a live mesh node. Existing doors stay in place. App shells are not started.</p>
          <p class="note" id="st-note" style="margin-top:.8rem"></p>
          <h3 style="font-size:.95rem;color:var(--gold);margin:1rem 0 .4rem">Principles</h3>
          <ol id="st-principles" style="margin:0;padding-left:1.15rem">${principles}</ol>
          <h3 style="font-size:.95rem;color:var(--gold);margin:1rem 0 .4rem">Registered verbs</h3>
          <div class="chips" id="st-verbs"></div>
          <div class="row">
            <button type="button" class="act" id="btn-refresh-status">Refresh status</button>
            <button type="button" class="act" id="btn-health">Health</button>
          </div>
        </section>

        <section class="panel" id="tab-invite" role="tabpanel">
          <p class="note">Propagation is invitation, not infection. This text writes no files on your machine.</p>
          <pre class="invite" id="invite-text">Loading invite…</pre>
        </section>

        <section class="panel" id="tab-prefab" role="tabpanel">
          <p class="note">These are catalog hooks. Opening a page is voluntary. This page does not start their shells, and it does not copy them onto disk.</p>
          <p class="kid" id="prefab-count">Catalog hooks: …</p>
          <div class="apps" id="prefab-apps"></div>
        </section>

        <section class="panel" id="tab-lattice" role="tabpanel">
          <p class="note">GET /v1/lattice is a public snapshot. POST append (gear-click + timeslate) is binding-only on this Worker and belongs to full AZ-OS. No rollbacks.</p>
          <div class="fields">
            <div class="field"><b>Gear ticks</b><span id="lat-gears">…</span></div>
            <div class="field"><b>Timeslates</b><span id="lat-slates">…</span></div>
            <div class="field"><b>Rollback</b><span>Nothing here rolls back.</span></div>
            <div class="field"><b>Tip</b><span id="lat-tip">none</span></div>
          </div>
          <p class="note" id="lat-note" style="margin-top:.8rem"></p>
          <div class="row">
            <button type="button" class="act" id="btn-lattice">Refresh snapshot</button>
            <button type="button" class="act" disabled title="Needs full AZ-OS">Bind timeslate (full AZ-OS)</button>
          </div>
        </section>

        <section class="panel" id="tab-gates" role="tabpanel">
          <p class="note">Session-safe preview of the five gates. This does not open a hosted session and does not exec. Default deny. FAIL shows an invite, not a silent block.</p>
          <label class="lab">Action</label>
          <select id="gate-action">
            <option value="shell" selected>shell</option>
            <option value="echo">echo</option>
            <option value="list_modules">list_modules</option>
            <option value="status">status</option>
            <option value="purge_session">purge_session</option>
            <option value="unsigned">unsigned (will fail integrity)</option>
          </select>
          <label class="lab">Definition</label>
          <textarea id="gate-definition" placeholder="Open an ethics-gated shell session."></textarea>
          <label class="lab">Evidence</label>
          <textarea id="gate-evidence" placeholder="Operator requested a principle-bound remote shell."></textarea>
          <label class="lab">Impact</label>
          <textarea id="gate-impact" placeholder="Hosted KV vfs only. No host subprocess."></textarea>
          <label class="lab">Actor (a name, not a privilege)</label>
          <input id="gate-actor" type="text" placeholder="operator" maxlength="80">
          <div class="row"><button type="button" class="act" id="btn-preview-gates">Preview gates</button></div>
          <div class="gates" id="gate-rows"><p class="note">Submit a preview.</p></div>
        </section>

        <section class="panel" id="tab-full" role="tabpanel">
          <p class="kid">Full AZ-OS is the local Interface and ethics-coded shell. This Worker homepage does not pretend the public proxy is that OS.</p>
          <div class="fields">
            <div class="field"><b>Local Interface</b><span><code>azos ui</code> → http://127.0.0.1:8800</span></div>
            <div class="field"><b>Local shell</b><span><code>azos shell --actor operator</code></span></div>
            <div class="field"><b>Hosted session</b><span>POST /v1/session — product-Worker KV; install AZ-OS to use it as software</span></div>
            <div class="field"><b>Hosted exec</b><span>POST /v1/exec — principle-bound KV vfs, not host bash</span></div>
            <div class="field"><b>Lattice bind</b><span>POST /v1/lattice — append-only; use full AZ-OS</span></div>
          </div>
          <p class="note" style="margin-top:.8rem">OpenAPI: <a href="/openapi.json">/openapi.json</a> · Skill: <a href="/v1/skill">/v1/skill</a> · Mesh: <a href="/v1/mesh">/v1/mesh</a> · AI tools: <a href="/ai">/ai</a> · Catalog: <a href="${CATALOG}">aziel-runtime</a></p>
          <p class="note">Works with ChatGPT (GPT Actions / OpenAI), Grok (xAI), Venice, Claude (Anthropic), Cursor (MCP), Glama (MCP), Perplexity, Microsoft Copilot / Bing, Google Gemini / Vertex, Mistral, Meta AI, Apple Intelligence surfaces, Amazon Q tooling, DuckAssist, You.com, Cohere, and other MCP/OpenAPI-capable assistants.</p>
          <label class="lab">Look up a hooked app</label>
          <select id="app-pick">${prefabHints}</select>
          <p class="note" id="app-blurb" style="margin-top:.5rem"></p>
        </section>

        <section class="panel" id="tab-cite" role="tabpanel">
          <p class="kid">How to cite</p>
          <pre class="invite">${escapeHtml(cite.cite)}</pre>
          <p class="note">No Zenodo DOI is claimed on this page. License Apache-2.0. Identity: Aziel Eliab only. Forks welcome.</p>
          <p class="note"><a href="/cite.json">cite.json</a> · <a href="/llms.txt">llms.txt</a> · <a href="/robots.txt">robots.txt</a> · <a href="/sitemap.xml">sitemap.xml</a> · <a href="/v1/mesh">/v1/mesh</a> · <a href="/stats">JSON stats</a></p>
        </section>
      </main>
    </div>

    <section class="card" style="margin-top:1rem">
      <h2>Per repo / branch / fork</h2>
      <ul>${breakdownList(stats)}</ul>
    </section>

    <footer>
      <p>AZ-OS — Aziel Eliab. ${MOTTO} Apache-2.0. Forks welcome and always allowed.</p>
      <ul>
        <li>Counted download: <a href="/download?asset=${DEFAULT_ASSET}">/download</a> (gzip, HTTP 200, no 302)</li>
        <li>One-click install: <a href="/install.sh">/install.sh</a></li>
        <li>Suite Live Nodes (QNM-BUILD-1.0 + QNS-CD-1.0 hub cite; proxy forwards the runtime document; AZ-OS mesh_node_live stays false; no Node Gate on this page; no public qnsd proxy): <a href="/v1/mesh">/v1/mesh</a></li>
        <li>AzielTether survival mesh (prefer-central × peer sync; boards stay mesh-free): <a href="https://github.com/AzielEliab/azieltether">GitHub</a> · <a href="https://azieltether-download-tracker.vibelock.workers.dev/">Worker</a></li>
      </ul>
    </footer>
  </div>
  <script>
    (function () {
      var cmd = ${JSON.stringify(INSTALL_LINE)};
      var btn = document.getElementById("install-btn");
      var pre = document.getElementById("install-cmd");
      if (btn) {
        btn.addEventListener("click", function () {
          function done(ok) {
            btn.textContent = ok ? "Copied! Paste in Terminal, then run azos ui" : "Select the command, copy it, then run azos ui";
            btn.classList.add("copied");
          }
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(cmd).then(function () { done(true); }).catch(function () { done(false); });
          } else {
            done(false);
            if (pre && window.getSelection) {
              var r = document.createRange();
              r.selectNodeContents(pre);
              var sel = window.getSelection();
              sel.removeAllRanges();
              sel.addRange(r);
            }
          }
        });
      }

      var META = ${JSON.stringify(PREFAB_META)};
      var SAFE = ["list_modules", "echo", "status", "purge_session", "shell"];
      var BANNED = ["wipe disk", "format drive", "mkfs", "self-replicate", "self replicate", "worm", "ransom", "infect"];

      function uaHeaders(extra) {
        var h = { "Accept": "application/json" };
        if (extra) Object.keys(extra).forEach(function (k) { h[k] = extra[k]; });
        return h;
      }
      function busy(on) {
        var el = document.getElementById("ws-busy");
        if (!el) return;
        el.hidden = !on;
      }
      async function jfetch(url, opt) {
        var res = await fetch(url, Object.assign({
          headers: uaHeaders(opt && opt.headers),
        }, opt || {}));
        var text = await res.text();
        try { return { ok: res.ok, status: res.status, data: JSON.parse(text) }; }
        catch (e) { return { ok: res.ok, status: res.status, data: { raw: text } }; }
      }
      function setText(id, value) {
        var el = document.getElementById(id);
        if (el) el.textContent = value == null ? "" : String(value);
      }
      // Machine name for the absent news source: azos.news_source. People see a sentence, not this code.
      function said(flag, yes, no) { return flag === true ? yes : no; }
      function plainLimits(d) {
        var src = d || {};
        var userspace = src.userspace_base === true
          ? "The userspace base is present. That is a base, not a boot."
          : "The userspace base is absent.";
        return [
          said(src.kernel, "There is a kernel.", "There is no kernel."),
          said(src.kernel_base, "The kernel base is present.", "The kernel base is absent."),
          said(src.booted, "This has booted.", "This has not booted."),
          said(src.installed, "This is installed as an operating system.", "This is not installed as an operating system."),
          said(src.os_yet, "This is an operating system.", "This is not an operating system yet."),
          userspace,
          "An alternative internet is not live (alt_internet_live is false). A packet path is not live (packet_path_live is false). This isolate cannot see host hardware (worker_hardware is false). Still missing: a packet that leaves this machine and arrives on a different machine id. A same-machine mesh frame does not count. Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP. WireGuard, OpenVPN, an L3 exit pool, kernel UDP, and TUN/TAP stay SLOT. Public mail send, the kernel, and boot stay not live. The public door stays FG-STUB. Isolation is single-node security-awareness. Phoenix is a local wait and re-seal. That is not a loopback fence.",
          said(src.mail_send, "Mail can be sent from here.", "Mail is not sent from here."),
          said(src.one_click_install_live, "One-click install is live.", "One-click install is not live."),
          said(src.mesh_node_live, "This is a live mesh node.", "This is not a live mesh node."),
          said(src.doors_replaced, "An existing door was replaced.", "Existing doors stay in place."),
          said(src.app_shells_started, "App shells were started.", "App shells are not started.")
        ].join(" ");
      }

      function showTab(name) {
        document.querySelectorAll(".tabs [role=tab]").forEach(function (b) {
          b.setAttribute("aria-selected", b.getAttribute("data-tab") === name ? "true" : "false");
        });
        document.querySelectorAll(".panel").forEach(function (p) {
          p.classList.toggle("on", p.id === "tab-" + name);
        });
      }
      document.querySelectorAll(".tabs [data-tab]").forEach(function (b) {
        b.addEventListener("click", function () { showTab(b.getAttribute("data-tab")); });
      });

      async function loadStatus() {
        busy(true);
        var out = await jfetch("/v1/status", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        var d = out.data || {};
        setText("st-lumen", d.lumen === "running" ? "The watch is on." : (d.lumen === "stopped" ? "The watch is off." : "The watch state was not reported."));
        setText("st-version", d.version || "${VERSION}");
        setText("st-kind", "This is an ethics-coded remote shell. It is not a kernel.");
        setText("st-kernel", d.kernel === true ? "There is a kernel." : "There is no kernel.");
        setText("st-limits", plainLimits(d));
        var limits = document.getElementById("limits-plain");
        if (limits) limits.textContent = plainLimits(d);
        setText("st-note", "This reading is status only. It does not run a command.");
        var verbs = d.shell_verbs || [];
        var box = document.getElementById("st-verbs");
        if (box) {
          box.innerHTML = "";
          verbs.forEach(function (v) {
            var s = document.createElement("span");
            s.className = "chip";
            s.textContent = v;
            box.appendChild(s);
          });
        }
        busy(false);
      }
      async function loadHealth() {
        busy(true);
        var out = await jfetch("/v1/health");
        var d = out.data || {};
        setText("st-kernel", d.kernel === true ? "There is a kernel." : "There is no kernel.");
        setText("st-limits", plainLimits(d));
        setText("st-note", (out.ok ? "The health check passed. " : "The health check failed. ") + plainLimits(d));
        busy(false);
      }
      async function loadInvite() {
        var out = await jfetch("/v1/invite", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
        var d = out.data || {};
        setText("invite-text", d.invite || "Invite unavailable.");
      }
      async function loadPrefab() {
        var out = await jfetch("/v1/prefab");
        var d = out.data || {};
        var apps = d.apps || [];
        setText("prefab-count", "Catalog hooks listed: " + apps.length + ". This page does not start their shells.");
        var box = document.getElementById("prefab-apps");
        if (!box) return;
        box.innerHTML = "";
        apps.forEach(function (app) {
          var slug = app.slug || "";
          var meta = META[slug] || [slug, app.one_line || "Hooked catalog product."];
          var el = document.createElement("div");
          el.className = "app";
          var a = document.createElement("a");
          a.href = app.catalog || ("https://aziel-runtime.vibelock.workers.dev/p/" + slug);
          a.textContent = meta[0];
          var st = document.createElement("strong");
          st.appendChild(a);
          var sp = document.createElement("span");
          sp.textContent = meta[1];
          el.appendChild(st);
          el.appendChild(sp);
          box.appendChild(el);
        });
      }
      async function loadLattice() {
        var out = await jfetch("/v1/lattice");
        var d = out.data || {};
        setText("lat-gears", d.gear_ticks != null ? d.gear_ticks : "0");
        setText("lat-slates", d.timeslates != null ? d.timeslates : "0");
        setText("lat-tip", d.tip && d.tip.hash ? String(d.tip.hash).slice(0, 16) + "…" : "none");
        setText("lat-note", d.note || "GET is a snapshot. POST bind needs full AZ-OS.");
      }

      function filled(value, min) {
        return typeof value === "string" && value.trim().length >= min;
      }
      function esc(s) {
        return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      }
      function previewGates() {
        var action = (document.getElementById("gate-action").value || "").trim();
        var definition = document.getElementById("gate-definition").value || "";
        var evidence = document.getElementById("gate-evidence").value || "";
        var impact = document.getElementById("gate-impact").value || "";
        var actor = (document.getElementById("gate-actor").value || "").trim();
        var checks = {};
        if (!action) checks.definition = { pass: false, reason: "action name is required" };
        else if (!filled(definition, 8)) checks.definition = { pass: false, reason: "definition must state what the action is (min 8 chars)" };
        else checks.definition = { pass: true, reason: "action is defined" };
        if (!filled(evidence, 8)) checks.evidence = { pass: false, reason: "evidence / justification is required (min 8 chars)" };
        else checks.evidence = { pass: true, reason: "evidence provided" };
        var impactLow = impact.toLowerCase();
        if (!filled(impact, 8)) checks.impact = { pass: false, reason: "impact must state what will change (min 8 chars)" };
        else if (BANNED.some(function (b) { return impactLow.indexOf(b) >= 0; })) checks.impact = { pass: false, reason: "impact violates overlay bounds" };
        else checks.impact = { pass: true, reason: "impact stated" };
        if (action !== "shell" && SAFE.indexOf(action) < 0) checks.integrity = { pass: false, reason: "unsigned / unregistered action: default deny" };
        else checks.integrity = { pass: true, reason: "action is a registered safe builtin" };
        if (!actor) checks.responsibility = { pass: false, reason: "a named actor is required" };
        else checks.responsibility = { pass: true, reason: "actor '" + actor + "' is named (name is not a privilege)" };
        var names = ["definition", "evidence", "impact", "integrity", "responsibility"];
        var box = document.getElementById("gate-rows");
        box.innerHTML = "";
        names.forEach(function (name) {
          var g = checks[name];
          var row = document.createElement("div");
          row.className = "gate";
          row.innerHTML = '<span>' + esc(name) + '</span><span class="' + (g.pass ? 'pass' : 'fail') + '">' +
            (g.pass ? 'This check passed.' : 'This check stopped.') + '</span><span>' + esc(g.reason) + '</span>';
          box.appendChild(row);
        });
      }

      document.getElementById("btn-refresh-status").addEventListener("click", loadStatus);
      document.getElementById("btn-health").addEventListener("click", loadHealth);
      document.getElementById("btn-lattice").addEventListener("click", loadLattice);
      document.getElementById("btn-preview-gates").addEventListener("click", previewGates);
      var pick = document.getElementById("app-pick");
      function blurb() {
        var slug = pick.value;
        var meta = META[slug];
        setText("app-blurb", meta ? meta[0] + " — " + meta[1] : "");
      }
      pick.addEventListener("change", blurb);
      blurb();

      loadStatus();
      loadInvite();
      loadPrefab();
      loadLattice();

      (function () {
        function $(id) { return document.getElementById(id); }
        function meshNum() {
          for (var i = 0; i < arguments.length; i++) {
            var raw = arguments[i];
            if (raw == null || raw === "") continue;
            var n = typeof raw === "number" ? raw : Number(String(raw).replace(/,/g, ""));
            if (Number.isFinite(n) && n >= 0) return Math.floor(n);
          }
          return 0;
        }
        function unwrapMesh(j) {
          if (!j || typeof j !== "object") return {};
          if (j.result && typeof j.result === "object") return Object.assign({}, j, j.result);
          if (j.mesh && typeof j.mesh === "object") return Object.assign({}, j, j.mesh);
          return j;
        }
        function paintMesh(raw) {
          var j = unwrapMesh(raw);
          var on = j.enabled === true || j.enabled === 1 || String(j.status || "").toLowerCase() === "on";
          var r = (j.rollup && typeof j.rollup === "object") ? j.rollup : {};
          var live = on ? meshNum(r.live, j.live_nodes, j.live) : 0;
          var locked = on ? meshNum(r.locked, j.locked_nodes, j.locked) : 0;
          var isolated = on ? meshNum(r.isolated, j.isolated_nodes, j.isolated) : 0;
          $("meshLiveCount").textContent = String(live);
          $("qnmLive").textContent = String(live);
          $("qnmLocked").textContent = String(locked);
          $("qnmIsolated").textContent = String(isolated);
          var line = $("meshLine");
          var qns = (j.qns_cd && j.qns_cd.spec) || j.qns_cd_spec || "QNS-CD-1.0";
          if (on) line.textContent = "The suite mesh proxy returned an on document. The live count is " + live + ". This page is not a live mesh node. mesh_node_live stays false. Mode flags in that document are the runtime's. The cite is QNM-BUILD-1.0 and " + qns + ".";
          else if (j.status === "unavailable" || (j.ok === false && j.error)) line.textContent = "The suite mesh proxy could not be read. This page is not a live mesh node. mesh_node_live stays false. The cite is QNM-BUILD-1.0 and " + qns + ".";
          else line.textContent = "The suite mesh proxy returned an off document. This page is not a live mesh node. mesh_node_live stays false. The cite is QNM-BUILD-1.0 and " + qns + ".";
          var products = j.products_present || j.products || [];
          var names = Array.isArray(products) ? products.map(function (p) { return typeof p === "string" ? p : (p && (p.product || p.slug)) || ""; }).filter(Boolean) : [];
          var nodes = Array.isArray(j.nodes) ? j.nodes : [];
          var extra = names.length ? " · products " + names.join(", ") : (nodes.length ? " · " + nodes.length + " node labels" : "");
          $("meshProducts").textContent = "The catalog mesh tools and the FragGate mesh door stay as they are. This page does not replace them. /v1/mesh is a proxy. " + qns + " is a hub cite. Not an anonymity network. No public qnsd proxy." + (extra ? " " + extra + "." : "");
        }
        async function meshGet(path) {
          var r = await fetch(path, { headers: { "user-agent": "Mozilla/5.0", accept: "application/json" } });
          return r.json();
        }
        async function meshPost(path, payload) {
          var r = await fetch(path, { method: "POST", headers: { "content-type": "application/json", "user-agent": "Mozilla/5.0" }, body: JSON.stringify(payload || {}) });
          return r.json();
        }
        async function refreshMesh() {
          try {
            var status = await meshGet("/v1/mesh");
            var merged = status;
            var inner = unwrapMesh(status);
            var on = inner.enabled === true;
            if (on) {
              try {
                var nodes = await meshGet("/v1/mesh/nodes");
                merged = Object.assign({}, inner, unwrapMesh(nodes));
              } catch (e) { /* status is enough */ }
            }
            paintMesh(merged);
            var nodeId = sessionStorage.getItem("azos_mesh_node");
            if (on && nodeId) {
              try { await meshPost("/v1/mesh/heartbeat", { node_id: nodeId }); } catch (e) { /* no auto-heal */ }
            }
          } catch (e) {
            paintMesh({ ok: false, enabled: false, status: "unavailable", error: "mesh_unavailable" });
          }
        }
        $("meshEnable").onclick = async function () {
          var bearer = ($("meshBearer").value || "").trim();
          paintMesh(await meshPost("/v1/mesh/enable", bearer ? { bearer: bearer } : {}));
          refreshMesh();
        };
        $("meshDisable").onclick = async function () {
          sessionStorage.removeItem("azos_mesh_node");
          paintMesh(await meshPost("/v1/mesh/disable", {}));
          refreshMesh();
        };
        $("meshJoin").onclick = async function () {
          var j = await meshPost("/v1/mesh/join", { product: "azos", label: "AZ-OS Worker" });
          var inner = unwrapMesh(j);
          var id = inner.node_id || inner.id || (inner.session && inner.session.node_id);
          if (id) sessionStorage.setItem("azos_mesh_node", String(id));
          paintMesh(j);
          refreshMesh();
        };
        $("meshLeave").onclick = async function () {
          var id = sessionStorage.getItem("azos_mesh_node");
          if (id) await meshPost("/v1/mesh/leave", { node_id: id });
          sessionStorage.removeItem("azos_mesh_node");
          refreshMesh();
        };
        window.addEventListener("pagehide", function () {
          var id = sessionStorage.getItem("azos_mesh_node");
          if (!id || typeof navigator.sendBeacon !== "function") return;
          try { navigator.sendBeacon("/v1/mesh/leave", new Blob([JSON.stringify({ node_id: id })], { type: "application/json" })); } catch (e) { /* leave expires in 5 minutes */ }
        });
        refreshMesh();
        setInterval(refreshMesh, 30000);
        document.addEventListener("visibilitychange", function () { if (!document.hidden) refreshMesh(); });
      })();
      // AZNews x 4DMap: the banner shows this Worker's own door result (never the runtime's raw claim).
      (async function newsMap() {
        try {
          var nm = (await jfetch("/v1/newsmap")).data || {};
          var c = nm.door_join_check || null;
          var rc = nm.runtime_claims || {};
          var line;
          if (nm.joined === true) {
            line = "AZNews and 4DMap are joined" + (nm.merged === true ? " and merged" : ", not merged") + (nm.live === true ? ", and live" : ", not live") + ". This page checked it itself just now: the newest stored item (" + (c && c.item_id) + ") has " + (c && c.pins_on_item) + " pin(s); pin " + (c && c.pin_id) + " opens that same item with a matching report hash. Lattice walk verified: " + (nm.lattice_live === true ? "yes" : "no") + ". 4DMap is not installed here and this page keeps no copy.";
          } else {
            line = "AZNews and 4DMap are not shown as joined here (live, joined and merged read false). Reason: " + (nm.join_reason || "the door did not answer") + ". The runtime claims joined " + (rc.joined === true) + ", merged " + (rc.merged === true) + "; this page does not relay a claim it has not checked.";
          }
          setText("news-map", line);
          var pr = (await jfetch("/v1/newsmap/pins?limit=10")).data || {};
          var r = pr.runtime || {};
          var last = Array.isArray(r.last10) ? r.last10 : (Array.isArray(r.pins) ? r.pins.slice(0, 10) : []);
          var box = document.getElementById("news-map-pins");
          if (box && last.length) {
            box.textContent = "";
            var h = document.createElement("p");
            h.textContent = "Last " + last.length + " pins in the runtime store (read through the door):";
            box.appendChild(h);
            var ul = document.createElement("ul");
            last.forEach(function (p) {
              var li = document.createElement("li");
              var dot = document.createElement("span");
              dot.textContent = "\u25CF ";
              if (p.color && /^#[0-9a-fA-F]{3,8}$/.test(String(p.color))) dot.style.color = p.color;
              li.appendChild(dot);
              var a = document.createElement("a");
              var link = String(p.permalink || "");
              a.href = link.indexOf("https://") === 0 ? link : "https://aziel-runtime.vibelock.workers.dev/aznews";
              a.textContent = String(p.event || p.pin_id || "pin").slice(0, 140);
              li.appendChild(a);
              var meta = document.createElement("span");
              meta.textContent = " (" + (p.pin_type || "pin") + (p.date ? ", " + p.date : "") + ")";
              li.appendChild(meta);
              ul.appendChild(li);
            });
            box.appendChild(ul);
          }
        } catch (e) { /* banner keeps its not-read wording: nothing reads live here */ }
      })();
    })();
  </script>
</body>
</html>`;
}
