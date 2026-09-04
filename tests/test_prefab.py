"""Prefab AZ-OS ships every catalog product as an installed app."""

from __future__ import annotations

from azos.prefab import prefab_apps, prefab_snapshot, slugs
from azos.runtime import Runtime


REQUIRED = {
    "foldlock",
    "temporallock",
    "staticclock",
    "shadowlock",
    "veillock",
    "vibelock",
    "spectrallock",
    "miragegrid",
    "azai",
    "godlock",
    "azos",
}


def test_prefab_installs_catalog() -> None:
    apps = prefab_apps()
    assert len(apps) >= 25
    found = {a["slug"] for a in apps}
    assert REQUIRED <= found
    assert all(a["installed"] and a["hooked"] for a in apps)
    assert all(a["author"] == "Aziel Eliab" for a in apps)


def test_status_includes_prefab(runtime: Runtime) -> None:
    st = runtime.status()
    assert st["prefab"]["installed"] >= 25
    assert st["windows_shell"] is True
    assert "temporallock" in slugs()
    snap = prefab_snapshot()
    assert snap["prefab"] is True
