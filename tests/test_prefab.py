"""Prefab AZ-OS lists catalog hooks. That list is not an OS install."""

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
    assert all(a["hooked"] and a["hook_record"] for a in apps)
    assert all(a["installed"] is False for a in apps)
    assert all(a["author"] == "Aziel Eliab" for a in apps)


def test_status_includes_prefab(runtime: Runtime) -> None:
    st = runtime.status()
    assert st["installed"] is False
    assert st["prefab"]["installed"] is False
    assert isinstance(st["prefab"]["installed"], bool)
    assert st["prefab"]["hook_count"] >= 25
    assert st["prefab"]["hook_count"] == len(st["prefab"]["apps"])
    assert "This is not installed as an operating system." in st["limits_plain"]
    assert st["windows_shell"] is True
    assert "temporallock" in slugs()
    snap = prefab_snapshot()
    assert snap["prefab"] is True
    assert snap["installed"] is False
    assert snap["os_installed"] is False
    assert snap["hook_count"] == len(snap["apps"])
