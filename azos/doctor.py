"""Self-check for AZ-OS. No telemetry.

The door check reads the same refusals the runtime publishes.
It does not treat a receipt, a loopback bind, or a userspace file as a kernel.

    azos doctor
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Callable

from azos import __version__

AUTHOR = "Aziel Eliab"
Check = tuple[str, bool, str]


def _ok(name: str, detail: str = "") -> Check:
    return name, True, detail


def _fail(name: str, detail: str) -> Check:
    return name, False, detail


def _check_version() -> Check:
    if __version__:
        return _ok("version", str(__version__))
    return _fail("version", "missing")


def _check_identity() -> Check:
    try:
        mod = __import__(__name__.split(".")[0])
        author = str(getattr(mod, "__author__", AUTHOR))
    except Exception as exc:  # noqa: BLE001
        return _fail("identity", str(exc))
    blob = author + " " + AUTHOR
    forbidden = ("Col" + "lin H" + "orton", "Ja" + "ck Al" + "tman", "GodLock" + ".AZ", "Reve" + "aler")
    if any(x in blob for x in forbidden):
        return _fail("identity", "forbidden identity label")
    if "Aziel Eliab" not in blob:
        return _fail("identity", author)
    return _ok("identity", AUTHOR)



def _check_prefab_lattice() -> Check:
    try:
        from azos.lattice import IntegrityLattice
        from azos.prefab import prefab_apps
    except Exception as exc:  # noqa: BLE001
        return _fail("prefab-lattice", str(exc))
    if len(prefab_apps()) < 25:
        return _fail("prefab-lattice", "catalog short")
    lat = IntegrityLattice()
    lat.bind("doctor", summary="self-check", evidence="doctor")
    if not lat.verify():
        return _fail("prefab-lattice", "lattice verify")
    return _ok("prefab-lattice", f"{len(prefab_apps())} apps")


def _check_ethics_shell() -> Check:
    try:
        from azos.ethics import KIND, SHELL_VERBS, scope_dict
        from azos.shell import Shell
    except Exception as exc:  # noqa: BLE001
        return _fail("ethics-shell", str(exc))
    if KIND != "ethics_coded_remote_shell":
        return _fail("ethics-shell", KIND)
    if "ls" not in SHELL_VERBS or "bash" in SHELL_VERBS:
        return _fail("ethics-shell", "verb list")
    scope = scope_dict()
    if scope.get("host_subprocess") is not False:
        return _fail("ethics-shell", "host subprocess must be false")
    if not getattr(Shell, "execute", None):
        return _fail("ethics-shell", "Shell.execute missing")
    return _ok("ethics-shell", KIND)


def _check_json_roundtrip() -> Check:
    from azos.jsonio import export_json, import_json

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.json"
        out = Path(tmp) / "out.json"
        src.write_text(json.dumps({"product": "azos", "author": AUTHOR, "ok": True}, indent=2), encoding="utf-8")
        rec = import_json(src)
        if not rec.get("ok"):
            return _fail("import", str(rec))
        rec2 = export_json(out)
        if not rec2.get("ok") or not out.exists():
            return _fail("export", str(rec2))
        doc = json.loads(out.read_text(encoding="utf-8"))
        if doc.get("author") != AUTHOR:
            return _fail("export author", str(doc.get("author")))
        return _ok("json import/export", "roundtrip")


def _check_offline_node() -> Check:
    try:
        from azos.node import LAYERS, L0_DOOR, OfflineNode
        from azos.prefab import slugs
    except Exception as exc:  # noqa: BLE001
        return _fail("offline-node", str(exc))
    if tuple(LAYERS) != ("base", "stacked", "standalone"):
        return _fail("offline-node", "layers")
    with tempfile.TemporaryDirectory() as tmp:
        record = OfflineNode(root=tmp).status()
    if record.get("sidenet") != "aznet" or record.get("sidenet_is_aznet") is not True:
        return _fail("offline-node", "sidenet")
    if record.get("browser_surface") != "AZ Browser" or record.get("browser_role") != "browser surface for AZnet":
        return _fail("offline-node", "browser surface")
    if record.get("browser_is_layer") is not False or record.get("layers_additive") is not True:
        return _fail("offline-node", "layers")
    if record.get("browser_in_this_package") is not False or "azbrowser" in slugs():
        return _fail("offline-node", "browser package")
    if record.get("l0_executed") is not False or record.get("l0_replaced") is not False:
        return _fail("offline-node", "l0")
    if record.get("payload_host") is not False or record.get("softwares_desk") != "frozen":
        return _fail("offline-node", "desk")
    if "azos-node" in slugs() or L0_DOOR.endswith("/v1/fraggate/call") is False:
        return _fail("offline-node", "prefab")
    return _ok("offline-node", "aznet client")


def _check_news_map() -> Check:
    try:
        from azos.newsmap import ABSENT_MODULE, ENGINE_SLUG, NewsMap
        from azos.prefab import prefab_apps, slugs
    except Exception as exc:  # noqa: BLE001
        return _fail("news-map", str(exc))
    if "4dmap" in slugs() or "aznews" in slugs():
        return _fail("news-map", "prefab slug")
    for app in prefab_apps():
        if app.get("slug") in {"4dmap", "aznews"} and app.get("installed"):
            return _fail("news-map", "installed")
    with tempfile.TemporaryDirectory() as tmp:
        record = NewsMap(root=tmp).status()
    if record.get("installed") or record.get("engine_installed") or record.get("source_present"):
        return _fail("news-map", "flags")
    if record.get("live") or record.get("merged") or record.get("lattice_live"):
        return _fail("news-map", "live")
    if record.get("engine_slug") != ENGINE_SLUG or record.get("absent") != ABSENT_MODULE:
        return _fail("news-map", "door")
    if record.get("engine_copy") or record.get("second_app"):
        return _fail("news-map", "copy")
    if record.get("runtime_done") is not False or record.get("cross_tether") is not True:
        return _fail("news-map", "runtime")
    paths = record.get("paths") if isinstance(record.get("paths"), dict) else {}
    if not paths.get("joined") or not paths.get("aznews_standalone") or not paths.get("fourdmap_standalone"):
        return _fail("news-map", "paths")
    not_live = record.get("not_live") if isinstance(record.get("not_live"), dict) else {}
    for key in ("internet", "mail", "kernel", "one_click_install", "mesh_node"):
        if not_live.get(key) is not False:
            return _fail("news-map", key)
    return _ok("news-map", "runtime join, source absent")


def _check_doors() -> Check:
    try:
        from azos.doors import prove, scope_follows
    except Exception as exc:  # noqa: BLE001
        return _fail("doors", str(exc))
    with tempfile.TemporaryDirectory() as tmp:
        try:
            proof = prove(Path(tmp))
            scope_follows(proof)
        except Exception as exc:  # noqa: BLE001
            return _fail("doors", str(exc))
    flags = proof["flags"]
    if flags.get("userspace_base") is not True:
        return _fail("doors", "userspace")
    if proof["doors"]["userspace_base"].get("booted") is True:
        return _fail("doors", "booted")
    for name in ("kernel", "booted", "installed", "internet", "mail_send", "mesh_node_live", "one_click_install_live"):
        if flags.get(name) is not False:
            return _fail("doors", name)
        if proof["doors"][name].get("refused") is not True:
            return _fail("doors", name)
    if flags.get("join_live") is True:
        return _fail("doors", "join")
    if proof["doors"]["join_live"].get("code") != "AZNEWS-SOURCE-ABSENT":
        return _fail("doors", "join")
    if proof["doors"]["kernel"].get("host_kernel") is True or proof["doors"]["kernel"].get("kernel_base") is True:
        return _fail("doors", "host kernel")
    if proof["doors"]["mail_send"].get("public_mta") is True or proof["doors"]["mail_send"].get("sent") is True:
        return _fail("doors", "public mail")
    if proof["doors"]["mesh_node_live"].get("public_bind") is True or proof["doors"]["mesh_node_live"].get("live") is True:
        return _fail("doors", "public bind")
    if proof["doors"]["installed"].get("fourdmap_installed") is True:
        return _fail("doors", "4dmap")
    if proof["doors"]["booted"].get("booted") is True:
        return _fail("doors", "booted")
    return _ok("doors", "userspace base, not a boot")


CHECKS: tuple[Callable[[], Check], ...] = (
    _check_version,
    _check_identity,
    _check_ethics_shell,
    _check_prefab_lattice,
    _check_json_roundtrip,
    _check_offline_node,
    _check_news_map,
    _check_doors,
)


def run_doctor(*, as_json: bool = False) -> int:
    results = []
    failed = 0
    for fn in CHECKS:
        name, ok, detail = fn()
        results.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            failed += 1
        mark = "ok" if ok else "FAIL"
        if not as_json:
            print(f"[{mark}] {name}" + (f" — {detail}" if detail else ""))
    payload = {
        "ok": failed == 0,
        "failed": failed,
        "checks": results,
        "version": __version__,
        "author": AUTHOR,
        "kind": "ethics_coded_remote_shell",
        "network": False,
        "telemetry": False,
    }
    if as_json:
        print(json.dumps(payload, indent=2))
    else:
        print("doctor", "passed" if failed == 0 else "failed")
        if failed == 0:
            print("Next: azos ui")
        else:
            print("Next: azos doctor --json")
    return 0 if failed == 0 else 1
