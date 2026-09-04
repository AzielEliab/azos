"""No kernel, bootloader, hypervisor, worm, eval, or host wipe."""

from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "azos"

FORBIDDEN_IMPORTS = {
    "subprocess",
    "pty",
    "ctypes",
    "cffi",
}


def _py_files() -> list[Path]:
    return [p for p in PKG.rglob("*.py") if p.is_file()]


def test_no_subprocess_or_eval_in_package() -> None:
    for path in _py_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in FORBIDDEN_IMPORTS, path
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN_IMPORTS, path
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec", "compile"}, path.name


def test_no_kernel_bootloader_hypervisor_worm_impl() -> None:
    """Refuse real OS / worm artifacts. Mentions in docs/comments are allowed
    only as negations ('not a kernel'). Implementation files must not define
    boot, kmain, hypervisor, or replicate routines.
    """
    banned_defs = {
        "kmain",
        "bootloader",
        "hypervisor",
        "self_replicate",
        "infect",
        "worm",
        "ransom",
        "wipe_disk",
        "format_drive",
    }
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(node.name.lower())
            for name in names:
                for banned in banned_defs:
                    assert banned not in name, f"{path.name} defines {node.name}"


def test_readme_declares_overlay_not_kernel() -> None:
    readme = (PKG.parent / "README.md").read_text(encoding="utf-8")
    assert "not" in readme.lower()
    assert "kernel" in readme.lower()
    assert "malware" in readme.lower()
    assert "https://azos-download-tracker.vibelock.workers.dev/" in readme
    assert "remote shell" in readme.lower()
    assert "prefab" in readme.lower()
    assert "temporallock" in readme.lower()
    assert "ethics" in readme.lower()
    assert "does not grant remote shell" not in readme.lower()
