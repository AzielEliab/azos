/**
 * AZ-DESIGN-TOKENS-1.0: tokens -> CSS. Pure; no imports, so AZInterface and AZ-OS vendor this
 * file byte-for-byte (pinned by SHA-256 in their LOCKSTEP.pin.json).
 * Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
 */
export function tokensCss(tokens) {
  const vars = [];
  for (const group of ["color", "type", "radius", "space", "layout"]) {
    const g = (tokens && tokens[group]) || {};
    for (const k of Object.keys(g).sort()) vars.push(`--az-${group === "color" ? "" : group + "-"}${k}:${g[k]}`);
  }
  return [
    `:root{color-scheme:dark;${vars.join(";")}}`,
    ".az-honesty{border:1px solid var(--az-warm-border);background:var(--az-warm-bg);color:var(--az-gold-ink);padding:var(--az-space-md) 1.05rem;border-radius:var(--az-radius-md)}",
    ".az-card{border:1px solid var(--az-line);border-radius:var(--az-radius-lg);padding:1.1rem 1.2rem;background:var(--az-card)}",
    ".az-banner{border:1px solid var(--az-warm-line);background:var(--az-warm-panel);color:var(--az-gold-soft);padding:var(--az-space-sm) .7rem;border-radius:var(--az-radius-sm)}",
    ".az-cta{display:inline-flex;align-items:center;min-height:var(--az-layout-tap);background:var(--az-warm-bg);color:var(--az-gold-ink);border:1px solid var(--az-warm-border);border-radius:var(--az-radius-sm);padding:.4rem .85rem;font-weight:600;text-decoration:none}",
    ".az-cta:hover,.az-cta:focus{background:var(--az-warm-hover)}",
    ".az-ok{color:var(--az-ok)}.az-fail{color:var(--az-fail)}.az-muted{color:var(--az-muted)}",
    ".az-lockstep[data-state=agree]{border-color:var(--az-ok)}.az-lockstep[data-state=drift],.az-lockstep[data-state=absent]{border-color:var(--az-fail)}",
  ].join("\n") + "\n";
}

/** Inline style for the shared first-run hints popup (MESH-HINTS-UI-1.0). Same on all three legs. */
export const HINTS_STYLE =
  "position:fixed;right:1rem;bottom:1rem;max-width:22rem;z-index:50;background:var(--az-warm-panel,#16120a);color:var(--az-ink,#e8eaef);border:1px solid var(--az-warm-border,#5c4a1a);border-radius:var(--az-radius-md,10px);padding:.9rem 1rem;box-shadow:0 4px 18px rgba(0,0,0,.45);font:var(--az-type-small,14px/1.4 system-ui,sans-serif)";
