"""Session directory helpers. Purge touches .azos only."""

from __future__ import annotations

from pathlib import Path

from azos.errors import AzosError

SESSION_DIRNAME = ".azos"

# Parents we will never delete a session from (OS paths, not user homes).
_PROTECTED_PARENTS = frozenset(
    {
        Path("/"),
        Path("/etc"),
        Path("/usr"),
        Path("/bin"),
        Path("/sbin"),
        Path("/boot"),
        Path("/sys"),
        Path("/proc"),
        Path("/dev"),
        Path("/lib"),
        Path("/lib64"),
        Path("/opt"),
        Path("/var"),
        Path("/root"),
        Path("/tmp"),
    }
)


def session_dir(root: Path | str | None = None) -> Path:
    """Return <root>/.azos (default: cwd). Does not create it."""
    base = Path(root) if root is not None else Path.cwd()
    return base / SESSION_DIRNAME


def safe_purge(target: Path | str) -> Path:
    """Delete a .azos session directory only. Never $HOME or OS files.

    Raises AzosError rather than touching anything else.
    """
    path = Path(target).resolve()
    home = Path.home().resolve()
    if path == home:
        raise AzosError("refusing to purge $HOME")
    if path == Path("/").resolve():
        raise AzosError("refusing to purge filesystem root")
    if path.name != SESSION_DIRNAME:
        raise AzosError(
            f"purge only deletes a {SESSION_DIRNAME} session directory, not {path}"
        )
    if path.parent in _PROTECTED_PARENTS or path in _PROTECTED_PARENTS:
        raise AzosError(f"refusing to purge an OS path: {path}")
    if path.exists():
        if not path.is_dir():
            raise AzosError(f"session path is not a directory: {path}")
        import shutil

        shutil.rmtree(path)
    return path
