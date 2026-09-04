"""Prefab AZ-OS: every catalog product ships as an installed app.

Hooks are local metadata + Worker URLs. Prefab does not download other
repos at runtime. Author: Aziel Eliab.
"""

from __future__ import annotations

from typing import Any

AUTHOR = "Aziel Eliab"
CATALOG = "https://aziel-runtime.vibelock.workers.dev/v1/catalog.json"

# slug, name, one_line, primary op, worker host prefix
_APPS: tuple[tuple[str, str, str, str], ...] = (
    ("azos", "AZ-OS Shell", "Ethics-coded remote shell. Integrity precedes execution.", "session"),
    ("temporallock", "TemporalLock", "Immutable timeslate lattice hash-chained to StaticClock. No rollbacks.", "genesis"),
    ("staticclock", "StaticClock", "Gear-click timeline. Every action locks forward. AZ-OS integrity hook.", "advisory"),
    ("shadowlock", "ShadowLock", "OS-hook into AZ-OS for ethics-policy observation of jobs/processes.", "observe"),
    ("foldlock", "FoldLock", "SOTA UNI1 compression engine for UTF-8 text. zip-class in the prose lane.", "fold-preview"),
    ("azai", "AZAI / JEEVES", "True local AI stack on Ollama. OpenAI-compatible. Jeeves is not sovereign.", "lamb-check"),
    ("godlock", "GodLock", "Empirical Knowledge stress-test. Client hook to https://godlock.uk. Not a VPN.", "score"),
    ("vibelock", "VibeLock", "SOTA deepfake detection via physics + unnatural image/video/audio shifts.", "analyze"),
    ("veillock", "VeilLock", "Camera/video obfuscation hook unless the operator accepts a call via AZ-OS.", "pulse"),
    ("spectrallock", "SpectralLock", "Rosetta spectral / OCR-family overlays (zero, tazel, vyrn, uv, rosetta…).", "overlay"),
    ("miragegrid", "MirageGrid", "True node-mesh VPN and anonymity network. Peer mesh routing.", "assign"),
    ("codelock", "CodeLock", "Canonical or Rosetta HTML view of source. Alters perception, not meaning.", "render"),
    ("decisiongate", "DecisionGATE", "Five sequential gates. Freedom without clarity is chaos.", "check"),
    ("chronolock", "ChronoLock", "Advisory temporal window. Distinct from TemporalLock. Not a scheduler.", "advisory"),
    ("azclce", "AZ-CLCE", "Inconsistency detection. Type D is a label, not a finding of malice.", "score"),
    ("ark", "The ARK", "Mode E heuristics sweep. Not a kernel. Never stores vaults.", "sweep"),
    ("azbot", "AZBot", "Skill, not a model. Tether to aziel-runtime and public HTTPS only.", "skill"),
    ("aziel-corpus", "Aziel Digital Library", "Public MASTER library. Anonymous GET is read-only.", "search"),
    ("employeelock", "EmployeeLock", "Hash-chained accountability workbook. Not a court. Hosted never stores xlsx.", "append-preview"),
    ("whistlelock", "WhistleLock", "Local drop ledger + dead-man copy. Not a mailer. Hosted never holds files.", "hash-preview"),
    ("trajectorylock", "TrajectoryLock", "Auditable geometric test. Not a certified forensic instrument.", "analyze"),
    ("forgereceipts", "ForgeReceipts", "Local receipt / checklist helper. Not legal advice. No court connection.", "receipt"),
    ("glossafilter", "Glossa Filter", "Render an intent across bundled peer ids. Tools remain tools.", "render"),
    ("postking", "Post-King Chess", "The goal is to remain. Human is king-bound; AI has a Node, not a king.", "new"),
    ("zsolver", "ZionPattern Solver", "Hard 75% confidence cap. Provisional. Does not solve any case.", "score"),
)


def _worker_host(slug: str) -> str:
    if slug == "aziel-corpus":
        return "https://www.azielcorpuslibrary.net"
    return f"https://{slug}-download-tracker.vibelock.workers.dev"


def prefab_apps() -> list[dict[str, Any]]:
    """All catalog products, marked installed on the prefab desktop."""
    apps: list[dict[str, Any]] = []
    for slug, name, one_line, op in _APPS:
        host = _worker_host(slug)
        apps.append(
            {
                "slug": slug,
                "name": name,
                "one_line": one_line,
                "installed": True,
                "hooked": True,
                "author": AUTHOR,
                "op": op,
                "worker": host,
                "skill": f"{host}/v1/skill",
                "health": f"{host}/v1/health" if slug != "aziel-corpus" else f"{host}/v1/health",
                "download": f"{host}/download",
                "github": f"https://github.com/AzielEliab/{slug}",
                "catalog": f"https://aziel-runtime.vibelock.workers.dev/p/{slug}",
                "client_hook": "https://godlock.uk" if slug == "godlock" else None,
            }
        )
    return apps


def prefab_snapshot() -> dict[str, Any]:
    apps = prefab_apps()
    return {
        "prefab": True,
        "author": AUTHOR,
        "catalog": CATALOG,
        "installed": len(apps),
        "apps": apps,
        "note": "Prefab AZ-OS ships every catalog product as an installed app hook. It does not silently copy other repos onto disk.",
    }


def slugs() -> tuple[str, ...]:
    return tuple(row[0] for row in _APPS)
