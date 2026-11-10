"""AZ-OS adoption of the runtime signed install/update path.

Calls the AZ-UPDATE-MANIFEST-1.0 verifier and the AZ-AUTO-UPDATE-1.0 apply
engine. Default OFF (``auto_update`` is not true, and ``AUTO_UPDATE`` is not
``on``). ``live`` stays false. A userspace tree under ``.azos/update`` is not
a kernel boot and not an operating-system install.

Operator trust is the only key source. This module does not generate a
release key, does not invent a release URL, and does not print key material.
The published runtime pin is accepted only for product ``aziel-runtime``.

Mesh membership is not delivery. Wi-Fi, Bluetooth, RF, and photon are absent
on this process. Paid satellite relay stays HELD. A file inbox uses the same
signature check as an internet envelope and is not a second device.

Boundary (this slice does not pretend these are done):
- ``image/init`` does not run Python. QEMU PID 1 stays AZOS-BOOT-1, guardian absent.
- Activation does not swap the kernel or the running interpreter.
- AZInterface does not vendor this path.
- Track 2 LAN sessions are not implemented. ``mesh:file`` is a local inbox.
- Worker ``/v1/version`` on AZ-OS stays a lockstep gap.
- No published ``auto-update-manifest.json`` is assumed to exist.
- Runtime PR 387 is not modified.
- The empty-artifact recover hole is in this host. The copied engine does not
  share it: ``tools/auto_update_updater.py`` ``apply_offer`` compares length and
  hash, and ``src/auto-update/node-host.js`` has no generation recover
  (``healthCheck`` returns false). Those files stay in aziel-runtime.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

try:
    import fcntl
except ImportError:  # pragma: no cover - Linux has fcntl
    fcntl = None  # type: ignore[assignment]

from azos import update_engine as U
from azos import update_verify as V
from azos.paths import SESSION_DIRNAME

TRUST_SPEC = "AZOS-UPDATE-TRUST-1.0"
PRODUCTS = frozenset({"azos", "aziel-runtime"})
ABS_MAX = 32 * 1024 * 1024
DEFAULT_MAX = 8 * 1024 * 1024
ENVELOPE_MAX = 64 * 1024
MEMBER_CAP = 512
NAME_CAP = 200
ESTABLISHED_RELEASE_API = "https://api.github.com/repos/AzielEliab/aziel-runtime/releases/latest"
RELEASE_MANIFEST_NAME = "auto-update-manifest.json"
GITHUB_HOSTS = frozenset(
    {
        "api.github.com",
        "github.com",
        "objects.githubusercontent.com",
        "release-assets.githubusercontent.com",
    }
)
_FORBIDDEN_TRUST = frozenset(
    {"private_key", "private", "pem", "seed", "secret", "signing_key", "AUTO_UPDATE_SIGNING_KEY"}
)
_URL_CAP = 512

TRUST_NEED: tuple[str, ...] = (
    "Create .azos/update/trust.json. Never put a private key, seed, or PEM in that file.",
    "spec must be AZOS-UPDATE-TRUST-1.0.",
    "product must be azos or aziel-runtime.",
    "public_key must be the raw 32-byte Ed25519 release public key, base64url. AZ-OS does not generate one and does not ship an azos pin.",
    "The published runtime pin vouches for product aziel-runtime only. Its fingerprint is "
    + V.RELEASE_KEY_FINGERPRINT
    + ". Using that pin for product azos is UPDATE-NO-KEY. Omit public_key only when product is aziel-runtime and that published pin is the operator's choice.",
    "auto_update must be true to apply. The default is false (UPDATE-OFF). The environment variable AUTO_UPDATE=on is the same switch.",
    "Offline artifact directory: .azos/update/incoming/ with manifest.json, manifest.sig, and the file named by artifact.name. envelope.json is accepted in place of the two manifest files.",
    "A peer file inbox is .azos/update/peer-inbox/ with the same files. It uses the same signature check. It is not a radio, not LAN hardware, and not a second device.",
    "release_url, when set, must be an https URL of an auto-update envelope the operator already holds. AZ-OS does not invent one. http, redirects, and URLs with userinfo are refused.",
    "For product aziel-runtime, established_runtime_release true fetches "
    + ESTABLISHED_RELEASE_API
    + " and the asset "
    + RELEASE_MANIFEST_NAME
    + ". No such asset is assumed to exist. The fetch fails closed when it is missing.",
    "max_bytes is optional and cannot exceed 33554432. Declared sizes above the cap are UPDATE-BOUND and are not downloaded.",
    "Paid satellite_relay stays HELD. mesh_node, alt_internet, and packet_path membership do not make a carrier present.",
    "trust.json must be a regular file owned by this user, not a symlink, and not writable by group or other (mode 0600). .azos and .azos/update must match. Mode 0666 is refused.",
)

LOCK_WAIT_SECONDS = 2.0
LOCK_STALE_SECONDS = 30.0

BOUNDARY: tuple[str, ...] = (
    "image/init does not run this module. QEMU PID 1 stays AZOS-BOOT-1 with guardian absent.",
    "Activation is a userspace tree under .azos/update/generations. It does not swap the kernel or the running interpreter.",
    "The published runtime pin vouches for product aziel-runtime only. No AZ-OS release key is shipped.",
    "AZInterface does not vendor this updater.",
    "Track 2 LAN sessions are not implemented. mesh:file is a local inbox, not a second device and not a radio.",
    "Paid satellite_relay stays HELD. Carrier hardware on this process is absent.",
    "Worker /v1/version on AZ-OS stays a lockstep gap. This slice does not re-pin lockstep.",
    "No published auto-update-manifest.json is assumed. A missing asset is UPDATE-NO-RELEASE.",
    "Runtime PR 387 (851cc8d90fbdfa578198a112e6482f31bb5de8e0) is not modified.",
)

NEXT: tuple[str, ...] = (
    "Operator writes .azos/update/trust.json with a real release public key and auto_update true.",
    "A signed stable manifest and artifact, offline in incoming/, or an operator https release_url.",
    "AZInterface adoption of the same manifest verifier and apply engine.",
    "Capability 3: start this module from the boot image after PID 1. image/init does not do that.",
    "A Track 2 session with a demonstrated LAN peer before mesh:lan can mean hardware.",
    "A real stable auto-update-manifest.json on AzielEliab/aziel-runtime. Not assumed here.",
    "Upstream node healthCheck still rolls back inside aziel-runtime. This repo does not change that.",
)


class _Bound(Exception):
    """Declared size or a read exceeded the cap. Nothing was activated."""


class _Transport(Exception):
    """The release fetch did not return a body."""


class _Unsafe(Exception):
    """The archive is not safe to unpack."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise _Transport("redirect refused")


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _update_home(root: Path) -> Path:
    return Path(root) / SESSION_DIRNAME / "update"


def _https_url(url: object, *, hosts: frozenset[str] | None = None) -> str | None:
    if not isinstance(url, str) or not url or len(url) > _URL_CAP:
        return None
    if any(ch in url for ch in ("\n", "\r", " ")):
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower()
    if not host:
        return None
    if hosts is not None and host not in hosts:
        return None
    return url


def _cap_of(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_MAX
    if value < 1:
        return DEFAULT_MAX
    return min(value, ABS_MAX)


def _auto_on(trust_flag: object) -> bool:
    if trust_flag is True:
        return True
    return os.environ.get("AUTO_UPDATE") == "on"


def _artifact_matches(manifest: object, data: bytes | bytearray) -> bool:
    """True only when ``data`` is exactly the signed size and sha256, including empty."""
    if not isinstance(manifest, dict) or not isinstance(data, (bytes, bytearray)):
        return False
    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        return False
    size = artifact.get("size")
    digest = artifact.get("sha256")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        return False
    if not isinstance(digest, str) or V.HEX64.fullmatch(digest) is None:
        return False
    raw = bytes(data)
    if len(raw) != size:
        return False
    return hashlib.sha256(raw).hexdigest() == digest


def _anchor_component(path: Path, *, want_file: bool) -> str | None:
    """Refuse a symlink, a wrong type, group/other write, or a different owner."""
    if path.is_symlink():
        return "symlink"
    try:
        info = path.lstat()
    except OSError:
        return "unreadable"
    if want_file and not stat.S_ISREG(info.st_mode):
        return "not a regular file"
    if not want_file and not stat.S_ISDIR(info.st_mode):
        return "not a directory"
    if info.st_mode & 0o022:
        return "writable by group or other"
    if hasattr(os, "geteuid"):
        try:
            owner = os.geteuid()
        except OSError:
            owner = None
        if owner is not None and info.st_uid != owner:
            return "owner is not this user"
    return None


def _trust_anchor_reason(path: Path, root: Path) -> str | None:
    """None when the file is missing or safe to read. A string refuses the anchor."""
    if not path.exists() and not path.is_symlink():
        return None
    try:
        relative = path.relative_to(root)
    except ValueError:
        return "path escapes the update root"
    cursor = Path(root)
    for part in relative.parts[:-1]:
        cursor = cursor / part
        if not cursor.exists() and not cursor.is_symlink():
            return None
        reason = _anchor_component(cursor, want_file=False)
        if reason:
            return reason
    reason = _anchor_component(path, want_file=True)
    if reason:
        return reason
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError:
        return "symlink or unreadable"
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022:
            return "writable by group or other"
        if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
            return "owner is not this user"
    finally:
        os.close(fd)
    return None


def _read_regular(path: Path, cap: int) -> bytes:
    """Read a regular file without following a symlink swapped in underneath."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise OSError("not a regular file")
        if info.st_size > cap:
            raise _Bound
        chunks: list[bytes] = []
        remaining = cap + 1
        while remaining:
            piece = os.read(fd, min(65536, remaining))
            if not piece:
                break
            chunks.append(piece)
            remaining -= len(piece)
            if sum(len(item) for item in chunks) > cap:
                raise _Bound
        return b"".join(chunks)
    finally:
        os.close(fd)


class UpdateLock:
    """Serialize recover and apply across processes.

    ``flock`` drops when the holder exits, including a crash, so a dead
    process does not stick the critical section. A live holder is not
    evicted. This does not delete generations or the lock file to steal
    the section.
    """

    def __init__(self, home: Path) -> None:
        self.home = home
        self.path = home / "update.lock"
        self.fd: int | None = None
        self._held = False
        self._slot: Path | None = None

    def acquire(self) -> bool:
        try:
            self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        except OSError:
            return False
        if self.path.is_symlink():
            return False
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            self.fd = os.open(self.path, flags, 0o600)
        except OSError:
            return False
        try:
            os.fchmod(self.fd, 0o600)
        except OSError:
            pass
        if fcntl is None:
            return self._acquire_directory()
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while True:
            try:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.05)
                continue
            except OSError:
                return False
            self._held = True
            self._write_record()
            return True

    def _write_record(self) -> None:
        if self.fd is None:
            return
        payload = json.dumps({"pid": os.getpid(), "started": time.time()}).encode("ascii")
        os.ftruncate(self.fd, 0)
        os.lseek(self.fd, 0, os.SEEK_SET)
        os.write(self.fd, payload)
        os.fsync(self.fd)

    def _acquire_directory(self) -> bool:
        """Fallback when flock is missing. A live pid is never removed."""
        slot = self.home / "update.lock.d"
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while True:
            try:
                os.mkdir(slot, 0o700)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    return False
                if _lock_dir_is_dead(slot) and _age_seconds(slot) >= LOCK_STALE_SECONDS:
                    try:
                        owner = slot / "owner"
                        if owner.is_file() and not owner.is_symlink():
                            owner.unlink()
                        os.rmdir(slot)
                    except OSError:
                        return False
                    continue
                time.sleep(0.05)
                continue
            try:
                (slot / "owner").write_text(
                    json.dumps({"pid": os.getpid(), "started": time.time()}),
                    encoding="ascii",
                )
            except OSError:
                return False
            self._slot = slot
            self._held = True
            return True

    def release(self) -> None:
        if self._slot is not None and self._held:
            owner = self._slot / "owner"
            try:
                if owner.is_file() and not owner.is_symlink():
                    owner.unlink()
                os.rmdir(self._slot)
            except OSError:
                pass
            self._slot = None
        if self.fd is None:
            self._held = False
            return
        try:
            if self._held and fcntl is not None:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            os.close(self.fd)
            self.fd = None
            self._held = False


def _age_seconds(path: Path) -> float:
    try:
        return max(0.0, time.time() - path.stat().st_mtime)
    except OSError:
        return 0.0


def _lock_dir_is_dead(slot: Path) -> bool:
    owner = slot / "owner"
    try:
        record = json.loads(owner.read_text(encoding="ascii"))
        pid = int(record.get("pid"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return _age_seconds(slot) >= LOCK_STALE_SECONDS
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except PermissionError:
        return False
    except OSError:
        return False
    return False


def load_trust(root: Path | str) -> dict[str, Any]:
    """Read operator trust. Missing or refused trust does not invent a key."""
    path = _update_home(Path(root)) / "trust.json"
    base: dict[str, Any] = {
        "configured": False,
        "enabled": _auto_on(False),
        "product": "azos",
        "public_key": None,
        "key_fingerprint": None,
        "release_url": None,
        "established_runtime_release": False,
        "max_bytes": DEFAULT_MAX,
        "code": "UPDATE-NO-KEY",
        "need": list(TRUST_NEED),
        "trust_refused": False,
    }
    if os.environ.get("AUTO_UPDATE") == "on":
        base["enabled"] = True
    anchor = _trust_anchor_reason(path, Path(root))
    if anchor:
        base["code"] = "UPDATE-TRUST-REFUSED"
        base["trust_refused"] = True
        base["enabled"] = False
        base["need"] = [
            "trust.json was refused ("
            + anchor
            + "). It must be a regular file owned by this user, mode 0600, not a symlink. .azos and .azos/update must match."
        ]
        return base
    if not path.exists():
        return base
    try:
        raw_bytes = _read_regular(path, ENVELOPE_MAX)
        raw = raw_bytes.decode("utf-8")
        loaded = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, _Bound):
        base["code"] = "UPDATE-TRUST-REFUSED"
        base["trust_refused"] = True
        base["enabled"] = False
        return base
    if not isinstance(loaded, dict):
        base["code"] = "UPDATE-TRUST-REFUSED"
        base["trust_refused"] = True
        base["enabled"] = False
        return base
    if _FORBIDDEN_TRUST.intersection(loaded):
        base["code"] = "UPDATE-TRUST-REFUSED"
        base["trust_refused"] = True
        base["enabled"] = False
        base["need"] = [
            "trust.json contains a private-key field. Remove it. AZ-OS accepts only a public key."
        ]
        return base
    if loaded.get("spec") != TRUST_SPEC or loaded.get("product") not in PRODUCTS:
        base["code"] = "UPDATE-TRUST-REFUSED"
        base["trust_refused"] = True
        base["enabled"] = False
        return base
    product = str(loaded["product"])
    base["product"] = product
    base["enabled"] = _auto_on(loaded.get("auto_update") is True)
    base["max_bytes"] = _cap_of(loaded.get("max_bytes"))
    established = loaded.get("established_runtime_release") is True and product == "aziel-runtime"
    base["established_runtime_release"] = established
    release = _https_url(loaded.get("release_url")) if isinstance(loaded.get("release_url"), str) else None
    base["release_url"] = release
    key_text = loaded.get("public_key")
    if key_text in (None, "") and product == "aziel-runtime":
        key_text = V.RELEASE_PUBLIC_KEY
    if not isinstance(key_text, str) or "PRIVATE" in key_text or "BEGIN " in key_text:
        base["public_key"] = None
        base["code"] = "UPDATE-NO-KEY"
        return base
    digest = V.fingerprint(key_text.strip())
    if digest is None:
        base["public_key"] = None
        base["code"] = "UPDATE-NO-KEY"
        return base
    if key_text.strip() == V.RELEASE_PUBLIC_KEY and product not in V.RELEASE_KEY_PRODUCTS:
        base["public_key"] = key_text.strip()
        base["key_fingerprint"] = digest
        base["configured"] = False
        base["code"] = "UPDATE-NO-KEY"
        base["need"] = [
            "The published runtime pin does not vouch for product azos. Put an azos release public key in public_key, or set product to aziel-runtime."
        ]
        return base
    base["public_key"] = key_text.strip()
    base["key_fingerprint"] = digest
    base["configured"] = True
    base["code"] = "UPDATE-OK"
    base["need"] = []
    return base


def _read_limited(response: Any, cap: int) -> bytes:
    header = response.headers.get("Content-Length") if getattr(response, "headers", None) else None
    if header is not None:
        try:
            declared = int(header)
        except ValueError as exc:
            raise _Bound from exc
        if declared < 0 or declared > cap:
            raise _Bound
    buf = bytearray()
    while len(buf) <= cap:
        chunk = response.read(min(65536, cap - len(buf) + 1))
        if not chunk:
            break
        buf += chunk
        if len(buf) > cap:
            raise _Bound
    return bytes(buf)


def _urllib_get(url: str, cap: int, timeout: float) -> bytes:
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            return _read_limited(response, cap)
    except _Bound:
        raise
    except Exception as exc:
        raise _Transport(str(exc)) from exc


def _pull(url: str, cap: int, timeout: float, opener: Callable[..., object] | None) -> bytes:
    if opener is not None:
        try:
            data = opener(url, timeout)
        except _Bound:
            raise
        except Exception as exc:
            raise _Transport(str(exc)) from exc
        if not isinstance(data, (bytes, bytearray)) or len(data) > cap:
            raise _Bound
        return bytes(data)
    checked = _https_url(url)
    if checked is None:
        raise _Transport("url refused")
    return _urllib_get(checked, cap, timeout)


def _parse_envelope(raw: bytes) -> dict[str, Any] | None:
    if len(raw) > ENVELOPE_MAX:
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        return None
    loaded = V.parse_manifest_text(text)
    if not isinstance(loaded, dict):
        return None
    if "manifest" in loaded:
        manifest = loaded.get("manifest")
        signature = loaded.get("signature")
        artifact_url = loaded.get("url") if isinstance(loaded.get("url"), str) else None
    else:
        manifest = loaded
        signature = None
        artifact_url = None
    if not isinstance(manifest, dict) or not isinstance(signature, str):
        return None
    return {"manifest": manifest, "signature": signature, "artifact_url": artifact_url}


def _local_candidate(directory: Path, cap: int) -> dict[str, Any] | None | str:
    """Return an offer, None when the directory is absent, or ``bound``."""
    if not directory.is_dir() or directory.is_symlink():
        return None
    envelope_path = directory / "envelope.json"
    if envelope_path.is_file() and not envelope_path.is_symlink():
        if envelope_path.stat().st_size > ENVELOPE_MAX:
            return "shape"
        parsed = _parse_envelope(envelope_path.read_bytes())
        if parsed is None:
            return "shape"
        manifest = parsed["manifest"]
        signature = parsed["signature"]
    else:
        manifest_path = directory / "manifest.json"
        sig_path = directory / "manifest.sig"
        if not manifest_path.is_file() or manifest_path.is_symlink():
            return None
        if not sig_path.is_file() or sig_path.is_symlink():
            return "shape"
        if manifest_path.stat().st_size > ENVELOPE_MAX or sig_path.stat().st_size > 512:
            return "shape"
        try:
            manifest = V.parse_manifest_text(manifest_path.read_text(encoding="utf-8"))
            signature = sig_path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            return "shape"
        if not isinstance(manifest, dict) or not signature:
            return "shape"
    if not V.shape_ok(manifest):
        return {"manifest": manifest, "signature": signature, "data": b"", "skip_read": True}
    declared = int(manifest["artifact"]["size"])
    if declared > cap:
        return {"manifest": manifest, "signature": signature, "data": b"", "bound": True}
    name = manifest["artifact"]["name"]
    artifact = directory / name
    if artifact.parent != directory or artifact.is_symlink() or not artifact.is_file():
        return {"manifest": manifest, "signature": signature, "data": b"", "bound": False}
    if artifact.stat().st_size > cap:
        return {"manifest": manifest, "signature": signature, "data": b"", "bound": True}
    data = artifact.read_bytes()
    if len(data) > cap:
        return {"manifest": manifest, "signature": signature, "data": b"", "bound": True}
    return {"manifest": manifest, "signature": signature, "data": data, "bound": False}


def _safe_member_name(name: str) -> Path | None:
    if not name or len(name) > NAME_CAP or "\\" in name or "\x00" in name:
        return None
    if name.startswith("/") or (len(name) >= 2 and name[1] == ":"):
        return None
    parts = [part for part in Path(name).parts if part not in ("", ".")]
    if not parts or any(part == ".." or part.startswith("/") for part in parts):
        return None
    if any(V.WIN_RESERVED.fullmatch(part) for part in parts):
        return None
    return Path(*parts)


def _extract(blob: bytes, dest: Path, cap: int, after_member: Callable[[int], None] | None) -> None:
    tree = dest / "tree"
    tree.mkdir(mode=0o755)
    try:
        handle = tarfile.open(fileobj=io.BytesIO(blob), mode="r:*")
    except tarfile.TarError:
        target = tree / "payload"
        _write_file(target, blob if len(blob) <= cap else b"")
        if len(blob) > cap:
            raise _Bound
        return
    total = 0
    count = 0
    with handle:
        for member in handle.getmembers():
            count += 1
            if count > MEMBER_CAP:
                raise _Unsafe("too many members")
            if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise _Unsafe("refused member type")
            rel = _safe_member_name(member.name)
            if rel is None:
                raise _Unsafe("refused member name")
            target = tree / rel
            if not _inside(tree, target):
                raise _Unsafe("escape")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True, mode=0o755)
                continue
            if member.size < 0 or member.size > cap or total + member.size > cap:
                raise _Bound
            source = handle.extractfile(member)
            if source is None:
                raise _Unsafe("missing body")
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            remaining = member.size
            chunks = bytearray()
            while remaining:
                piece = source.read(min(65536, remaining))
                if not piece:
                    raise _Unsafe("short member")
                if len(piece) > remaining:
                    raise _Bound
                chunks += piece
                remaining -= len(piece)
                total += len(piece)
                if total > cap:
                    raise _Bound
            _write_file(target, bytes(chunks))
            if after_member is not None:
                after_member(count)


def _inside(root: Path, path: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def _rm(path: Path) -> None:
    if path.is_symlink():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


class AzosUpdateHost:
    """Disk host: bounded bytes, safe extract, atomic generation swap, rollback."""

    def __init__(self, root: Path, trust: Mapping[str, Any], hooks: Mapping[str, Any] | None = None) -> None:
        self.root = Path(root)
        self.trust = trust
        self.hooks = dict(hooks or {})
        self.home = _update_home(self.root)
        self.gen = self.home / "generations"
        self.state_path = self.home / "state.json"
        self.receipt_path = self.home / "receipts.jsonl"
        self.product = str(trust.get("product") or "azos")
        self.public_key = trust.get("public_key") if isinstance(trust.get("public_key"), str) else None
        self.enabled = trust.get("enabled") is True and trust.get("trust_refused") is not True
        self.cap = int(trust.get("max_bytes") or DEFAULT_MAX)
        self.node_id = "azos-update"
        self.offline = True
        self._state_bad = False
        self._swapped = False
        self._pending_signature = ""
        self._offer: dict[str, Any] | None = None
        self._reach_cached: bool | None = None
        self._bound = False
        self._transport_failed = False
        self.recovered: str | None = None

    def now(self) -> str:
        return _now()

    def load(self) -> dict[str, Any]:
        if self._state_bad:
            return self._bad_state()
        if not self.state_path.is_file() or self.state_path.is_symlink():
            return U.initial_state(self.product, 0)
        try:
            loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            self._state_bad = True
            return self._bad_state()
        if not isinstance(loaded, dict) or loaded.get("product") != self.product:
            self._state_bad = True
            return self._bad_state()
        return json.loads(json.dumps(loaded))

    def _bad_state(self) -> dict[str, Any]:
        state = U.initial_state(self.product, 0)
        state["installed_seq"] = None
        state["floor_seq"] = None
        return state

    def _disk_floor(self) -> int | None:
        if not self.state_path.is_file() or self.state_path.is_symlink():
            return None
        try:
            loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        if isinstance(loaded, dict) and V.sint(loaded.get("floor_seq")) and loaded["floor_seq"] >= 0:
            return int(loaded["floor_seq"])
        return None

    def save(self, state: dict[str, Any]) -> None:
        if self._state_bad:
            return
        new_floor = state.get("floor_seq")
        disk_floor = self._disk_floor()
        if isinstance(disk_floor, int) and isinstance(new_floor, int) and new_floor < disk_floor:
            return
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = self.state_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(state, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.state_path)

    def write_receipt(self, row: dict[str, Any]) -> None:
        self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.receipt_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    def carrier_present(self, carrier: str) -> bool:
        """No radio and no Track 2 session exist in this process."""
        del carrier
        return False

    def peer_hello(self, carrier: str) -> dict[str, Any]:
        del carrier
        return {"refused": True, "code": "UPDATE-PEER-NO-ROUTE"}

    def peer_fetch(self, carrier: str, manifest: object) -> dict[str, Any]:
        del carrier, manifest
        return {"refused": True, "code": "UPDATE-PEER-NO-ARTIFACT"}

    def internet_reachable(self) -> bool:
        if self._reach_cached is not None:
            return self._reach_cached
        self._reach_cached = self._probe_release()
        return self._reach_cached

    def _probe_release(self) -> bool:
        try:
            offer = self._fetch_envelope()
        except _Transport:
            self._transport_failed = True
            self._offer = None
            return False
        except _Bound:
            self._bound = True
            self._offer = None
            return True
        self._offer = offer
        if (
            isinstance(offer, dict)
            and isinstance(offer.get("manifest"), dict)
            and V.sint(offer["manifest"].get("artifact", {}).get("size"))
            and offer["manifest"]["artifact"]["size"] > self.cap
        ):
            self._bound = True
        return True

    def fetch_release(self) -> dict[str, Any] | None:
        if self._offer is None and self._reach_cached is None:
            self.internet_reachable()
        offer = self._offer
        if isinstance(offer, dict) and isinstance(offer.get("signature"), str):
            self._pending_signature = offer["signature"]
        return offer

    def fetch_artifact(self, manifest: dict[str, Any]) -> bytes | None:
        if self._bound or manifest["artifact"]["size"] > self.cap:
            raise _Bound
        url = self._offer.get("artifact_url") if isinstance(self._offer, dict) else None
        if not isinstance(url, str):
            return None
        hosts = GITHUB_HOSTS if self.trust.get("established_runtime_release") is True else None
        checked = _https_url(url, hosts=hosts)
        if checked is None:
            return None
        data = _pull(checked, self.cap, 8.0, self.hooks.get("opener"))
        if len(data) > self.cap:
            raise _Bound
        return data

    def _fetch_envelope(self) -> dict[str, Any] | None:
        opener = self.hooks.get("opener")
        if self.trust.get("established_runtime_release") is True:
            listing = _pull(ESTABLISHED_RELEASE_API, ENVELOPE_MAX, 8.0, opener)
            try:
                meta = json.loads(listing.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                return {"refused": True, "code": "UPDATE-NO-RELEASE"}
            if not isinstance(meta, dict) or meta.get("prerelease") is True or meta.get("draft") is True:
                return {"refused": True, "code": "UPDATE-NO-RELEASE"}
            assets = meta.get("assets") if isinstance(meta.get("assets"), list) else []
            asset_url = None
            for asset in assets:
                if (
                    isinstance(asset, dict)
                    and asset.get("name") == RELEASE_MANIFEST_NAME
                    and isinstance(asset.get("browser_download_url"), str)
                ):
                    asset_url = _https_url(asset["browser_download_url"], hosts=GITHUB_HOSTS)
                    break
            if asset_url is None:
                return {"refused": True, "code": "UPDATE-NO-RELEASE"}
            body = _pull(asset_url, ENVELOPE_MAX, 8.0, opener)
        else:
            release = self.trust.get("release_url")
            if not isinstance(release, str):
                return {"refused": True, "code": "UPDATE-NO-RELEASE"}
            body = _pull(release, ENVELOPE_MAX, 8.0, opener)
        parsed = _parse_envelope(body)
        if parsed is None:
            return {"refused": True, "code": "UPDATE-NO-RELEASE"}
        artifact_url = parsed.get("artifact_url")
        hosts = GITHUB_HOSTS if self.trust.get("established_runtime_release") is True else None
        if isinstance(artifact_url, str):
            checked = _https_url(artifact_url, hosts=hosts)
            if checked is None:
                return {"refused": True, "code": "UPDATE-NO-RELEASE"}
            parsed["artifact_url"] = checked
        return {"manifest": parsed["manifest"], "signature": parsed["signature"], "artifact_url": parsed.get("artifact_url")}

    def stage(self, data: bytes, manifest: dict[str, Any]) -> None:
        staging = self.gen / "staging"
        _rm(staging)
        self.gen.mkdir(parents=True, exist_ok=True, mode=0o700)
        staging.mkdir(mode=0o700)
        try:
            _write_file(staging / "artifact.bin", data)
            after = self.hooks.get("after_member")
            _extract(data, staging, self.cap, after if callable(after) else None)
            before = self.hooks.get("before_ready")
            if callable(before):
                before(staging)
            (staging / "manifest.json").write_text(
                json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
            )
            (staging / "signature.txt").write_text(self._pending_signature + "\n", encoding="utf-8")
            (staging / "READY").write_text("ready\n", encoding="utf-8")
        except Exception:
            _rm(staging)
            raise

    def swap(self) -> None:
        current = self.gen / "current"
        previous = self.gen / "previous"
        staging = self.gen / "staging"
        if not (staging / "READY").is_file():
            raise _Unsafe("staging is not ready")
        if previous.exists() or previous.is_symlink():
            _rm(previous)
        if current.exists() or current.is_symlink():
            os.replace(current, previous)
        os.replace(staging, current)
        self._swapped = True

    def health_check(self) -> bool:
        return self._directory_healthy(self.gen / "current")

    def _directory_healthy(self, directory: Path) -> bool:
        ready = directory / "READY"
        blob = directory / "artifact.bin"
        manifest_path = directory / "manifest.json"
        if directory.is_symlink() or not directory.is_dir():
            return False
        if not ready.is_file() or ready.is_symlink() or not blob.is_file() or blob.is_symlink():
            return False
        if not manifest_path.is_file() or manifest_path.is_symlink():
            return False
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            data = blob.read_bytes()
        except (OSError, UnicodeError, json.JSONDecodeError):
            return False
        if not _artifact_matches(manifest, data):
            return False
        tree = directory / "tree"
        if tree.is_symlink() or not tree.is_dir():
            return False
        for path in tree.rglob("*"):
            if path.is_symlink() or not _inside(tree, path):
                return False
        return True

    def rollback(self) -> None:
        current = self.gen / "current"
        previous = self.gen / "previous"
        staging = self.gen / "staging"
        if not self._swapped:
            _rm(staging)
            return
        _rm(current)
        if previous.exists() and not previous.is_symlink():
            os.replace(previous, current)
        self._swapped = False

    def recover(self) -> None:
        """Finish or reject a generation only after bytes, size, and trust match.

        An empty ``artifact.bin`` is accepted only when the signed manifest
        declares size 0 and that hash. It never counts as a longer artifact.
        The recorded high-water floor is not lowered.
        """
        self._finish_or_drop_staging()
        current = self.gen / "current"
        if not current.is_dir() or current.is_symlink():
            if not self._restore_matching_previous():
                return
        if current.is_symlink() or not (current / "READY").is_file() or (current / "READY").is_symlink():
            self._reject_current()
            self.recovered = "current-rejected"
            return
        verdict = self._generation_verdict(current)
        if verdict is None or verdict.get("bytes_ok") is not True:
            self._reject_current()
            self.recovered = "current-rejected"
            return
        if not self.health_check():
            self._reject_current()
            self.recovered = "current-rejected"
            return
        if verdict.get("trusted") is not True:
            return
        state = self.load()
        if self._state_bad:
            return
        high = self._high_water(state)
        if high is None:
            return
        seq = verdict.get("seq")
        if not V.sint(seq) or seq <= high:
            return
        state["installed_seq"] = seq
        state["floor_seq"] = max(high, seq)
        state["manifest_hash"] = verdict.get("manifest_hash")
        state["served_manifest"] = {
            "manifest": verdict.get("manifest"),
            "signature": verdict.get("signature"),
        }
        state["last_code"] = "UPDATE-OK"
        state["product"] = self.product
        self.save(state)
        recorded = self._recorded_high()
        if recorded is None or recorded < seq:
            return
        self.recovered = "commit-finished"

    def _finish_or_drop_staging(self) -> None:
        staging = self.gen / "staging"
        current = self.gen / "current"
        if not staging.exists() and not staging.is_symlink():
            return
        ready = staging / "READY"
        if staging.is_symlink() or not ready.is_file() or ready.is_symlink() or current.exists() or current.is_symlink():
            _rm(staging)
            self.recovered = "staging-discarded"
            return
        verdict = self._generation_verdict(staging)
        high = self._recorded_high()
        if (
            verdict
            and verdict.get("bytes_ok") is True
            and verdict.get("trusted") is True
            and high is not None
            and V.sint(verdict.get("seq"))
            and verdict["seq"] > high
            and self._directory_healthy(staging)
        ):
            os.replace(staging, current)
            self.recovered = "staging-promoted"
            return
        _rm(staging)
        self.recovered = "staging-discarded"

    def _generation_verdict(self, directory: Path) -> dict[str, Any] | None:
        """Judge one generation. Empty bytes are hashed. Missing bytes are not a match."""
        if directory.is_symlink() or not directory.is_dir():
            return None
        blob = directory / "artifact.bin"
        manifest_path = directory / "manifest.json"
        sig_path = directory / "signature.txt"
        if blob.is_symlink() or manifest_path.is_symlink() or sig_path.is_symlink():
            return {"bytes_ok": False, "trusted": False, "seq": 0}
        if not manifest_path.is_file() or not sig_path.is_file():
            return None
        if not blob.is_file():
            return {"bytes_ok": False, "trusted": False, "seq": 0}
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            signature = sig_path.read_text(encoding="utf-8").strip()
            data = blob.read_bytes()
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        seq = manifest.get("version_seq") if isinstance(manifest, dict) else 0
        matched = _artifact_matches(manifest, data)
        if not matched:
            return {"bytes_ok": False, "trusted": False, "seq": seq if V.sint(seq) else 0, "manifest": manifest}
        trusted = self._signature_trusted(manifest, signature)
        digest = V.manifest_hash(manifest) if trusted and isinstance(manifest, dict) else None
        return {
            "bytes_ok": True,
            "trusted": trusted,
            "seq": seq if V.sint(seq) else 0,
            "manifest": manifest,
            "signature": signature,
            "manifest_hash": digest,
        }

    def _signature_trusted(self, manifest: object, signature: object) -> bool:
        if not self.public_key or not isinstance(manifest, dict) or not isinstance(signature, str):
            return False
        if not V.shape_ok(manifest):
            return False
        if manifest.get("product") != self.product:
            return False
        if manifest.get("channel") not in V.ACCEPTED_CHANNELS:
            return False
        if self.public_key == V.RELEASE_PUBLIC_KEY and manifest["product"] not in V.RELEASE_KEY_PRODUCTS:
            return False
        return V.sig_ok(self.public_key, manifest, signature)

    def _high_water(self, state: Mapping[str, Any] | None) -> int | None:
        if not isinstance(state, dict):
            return None
        floor = state.get("floor_seq")
        installed = state.get("installed_seq")
        if isinstance(floor, bool) or not isinstance(floor, int) or floor < 0:
            return None
        if isinstance(installed, bool) or not isinstance(installed, int) or installed < 0:
            return None
        return max(floor, installed)

    def _recorded_high(self) -> int | None:
        if not self.state_path.exists() and not self.state_path.is_symlink():
            return 0
        if self.state_path.is_symlink() or not self.state_path.is_file():
            return None
        try:
            loaded = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        return self._high_water(loaded if isinstance(loaded, dict) else None)

    def _restore_matching_previous(self) -> bool:
        previous = self.gen / "previous"
        current = self.gen / "current"
        verdict = self._generation_verdict(previous)
        high = self._recorded_high()
        if (
            not verdict
            or verdict.get("bytes_ok") is not True
            or verdict.get("trusted") is not True
            or high is None
            or not V.sint(verdict.get("seq"))
            or verdict["seq"] != high
            or high <= 0
            or not self._directory_healthy(previous)
        ):
            return False
        os.replace(previous, current)
        self.recovered = "previous-restored"
        return True

    def _reject_current(self) -> None:
        current = self.gen / "current"
        previous = self.gen / "previous"
        rejected = self.gen / "rejected"
        high = self._recorded_high()
        verdict = self._generation_verdict(previous) if previous.is_dir() and not previous.is_symlink() else None
        restore = (
            verdict is not None
            and verdict.get("bytes_ok") is True
            and verdict.get("trusted") is True
            and high is not None
            and V.sint(verdict.get("seq"))
            and verdict["seq"] == high
            and high > 0
            and self._directory_healthy(previous)
        )
        _rm(rejected)
        if current.exists() or current.is_symlink():
            os.replace(current, rejected)
        if restore:
            os.replace(previous, current)


def _refuse(host: AzosUpdateHost, code: str, source: str) -> dict[str, Any]:
    state = host.load()
    state["last_check"] = host.now()
    state["last_code"] = code
    row = U.update_receipt(
        host,
        state,
        {
            "product": state.get("product"),
            "from_seq": state.get("installed_seq"),
            "to_seq": None,
            "manifest_hash": None,
            "source": source,
            "outcome": "refused",
            "code": code,
            "at": state["last_check"],
        },
    )
    host.save(state)
    return {"ok": False, "code": code, "row": row, "live": False, "applied": False}


def _apply_candidate(
    host: AzosUpdateHost,
    candidate: Mapping[str, Any],
    source: str,
) -> dict[str, Any]:
    manifest = candidate.get("manifest")
    signature = candidate.get("signature")
    data = candidate.get("data") if isinstance(candidate.get("data"), (bytes, bytearray)) else b""
    pre = V.verify_manifest(manifest, signature, host.load(), host.public_key)
    if pre.get("ok") is True and isinstance(manifest, dict):
        declared = manifest["artifact"]["size"]
        if candidate.get("bound") is True or declared > host.cap or len(data) > host.cap:
            return _refuse(host, "UPDATE-BOUND", source)
    host._pending_signature = signature if isinstance(signature, str) else ""
    return U.apply_offer(
        host,
        {"manifest": manifest, "signature": signature},
        source,
        lambda _manifest: bytes(data),
        host.public_key,
    )


def _locked_out(root: Path) -> dict[str, Any]:
    """Another live process holds the update lock. Do not evict it or the floor."""
    trust = load_trust(root)
    host = AzosUpdateHost(
        root,
        {"product": trust.get("product") or "azos", "enabled": False, "public_key": None, "max_bytes": DEFAULT_MAX},
    )
    return _public(
        host,
        trust,
        {"ok": False, "code": "UPDATE-LOCK", "live": False, "applied": False},
        mesh=None,
        internet={"attempted": False, "code": None},
    )


def apply_candidate(
    root: Path | str,
    manifest: dict[str, Any],
    signature: str,
    data: bytes,
    source: str,
    *,
    hooks: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one in-memory offer with the operator key. Used by boot and by tests.

    ``source`` ``mesh:lan`` still reports hardware false. This process has no
    Track 2 session and does not treat the caller as a second device.
    """
    root_path = Path(root)
    lock = UpdateLock(_update_home(root_path))
    if not lock.acquire():
        try:
            return _locked_out(root_path)
        finally:
            lock.release()
    try:
        trust = load_trust(root_path)
        host = AzosUpdateHost(root_path, trust, hooks)
        host.recover()
        if source.startswith("mesh:"):
            host.offline = True
        decision = _apply_candidate(host, {"manifest": manifest, "signature": signature, "data": data}, source)
        return _public(host, trust, decision, mesh=None, internet=None)
    finally:
        lock.release()


def _public(
    host: AzosUpdateHost,
    trust: Mapping[str, Any],
    decision: Mapping[str, Any],
    *,
    mesh: Mapping[str, Any] | None,
    internet: Mapping[str, Any] | None,
) -> dict[str, Any]:
    state = {}
    try:
        if host.state_path.is_file():
            loaded = json.loads(host.state_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                state = loaded
    except (OSError, UnicodeError, json.JSONDecodeError):
        state = {}
    code = decision.get("code") if isinstance(decision.get("code"), str) else "UPDATE-STATE"
    row = decision.get("row") if isinstance(decision.get("row"), dict) else {}
    applied = code == "UPDATE-OK" and (row.get("outcome") == "applied" or decision.get("ok") is True)
    mesh_view = {
        "attempted": mesh is not None,
        "code": mesh.get("code") if isinstance(mesh, Mapping) else None,
        "carriers_present": [],
        "hardware": False,
        "radio_phy": False,
        "second_device": False,
        "satellite_relay": "HELD",
        "membership_only": True,
        "reason": None if mesh is not None else "updater is off or trust is not configured",
    }
    internet_view = dict(internet or {"attempted": False, "code": None})
    internet_view["live"] = False
    report = {
        "ok": code == "UPDATE-OK" and applied is True,
        "code": code,
        "applied": applied,
        "live": False,
        "booted": False,
        "hardware": False,
        "kernel": False,
        "installed": False,
        "os_yet": False,
        "one_click_install_live": False,
        "host_os": False,
        "remote_curl": False,
        "pip_ran": False,
        "radio_phy": False,
        "second_device": False,
        "satellite_relay": "HELD",
        "membership_only": True,
        "configured": trust.get("configured") is True,
        "enabled": host.enabled is True,
        "product": host.product,
        "key_pinned": bool(host.public_key) and trust.get("configured") is True,
        "key_fingerprint": trust.get("key_fingerprint") if trust.get("configured") is True else None,
        "need": list(trust.get("need") or []),
        "recovered": host.recovered,
        "source": row.get("source") if isinstance(row.get("source"), str) else None,
        "outcome": row.get("outcome") if isinstance(row.get("outcome"), str) else None,
        "floor_seq": state.get("floor_seq") if V.sint(state.get("floor_seq")) else None,
        "installed_seq": state.get("installed_seq") if V.sint(state.get("installed_seq")) else None,
        "manifest_hash": state.get("manifest_hash") if isinstance(state.get("manifest_hash"), str) else None,
        "mesh": mesh_view,
        "internet": internet_view,
        "channel": "stable",
        "boundary": list(BOUNDARY),
        "next": list(NEXT),
        "generation": str(host.gen / "current") if (host.gen / "current").is_dir() else None,
    }
    return report


def boot_update(root: Path | str, *, hooks: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run the signed update path for one directory. Default result is UPDATE-OFF.

    This is the userspace boot and install call. It does not boot hardware.
    Recover and apply share one cross-process lock.
    """
    root_path = Path(root)
    lock = UpdateLock(_update_home(root_path))
    if not lock.acquire():
        try:
            return _locked_out(root_path)
        finally:
            lock.release()
    try:
        try:
            return _boot_update(root_path, hooks or {})
        except Exception:
            trust = {
                "configured": False,
                "product": "azos",
                "need": list(TRUST_NEED),
                "enabled": False,
            }
            host = AzosUpdateHost(
                root_path,
                {"product": "azos", "enabled": False, "public_key": None, "max_bytes": DEFAULT_MAX},
            )
            return _public(
                host,
                trust,
                {"ok": False, "code": "UPDATE-STATE", "live": False},
                mesh=None,
                internet={"attempted": False, "code": None},
            )
    finally:
        lock.release()


def _boot_update(root: Path, hooks: Mapping[str, Any]) -> dict[str, Any]:
    trust = load_trust(root)
    host = AzosUpdateHost(root, trust, hooks)
    host.recover()
    if trust.get("trust_refused") is True:
        decision = _refuse(host, "UPDATE-TRUST-REFUSED", "offline")
        return _public(host, trust, decision, mesh=None, internet={"attempted": False, "code": None})
    if host.enabled is not True:
        decision = U.apply_offer(host, None, "offline", lambda _manifest: None, host.public_key)
        return _public(host, trust, decision, mesh=None, internet={"attempted": False, "code": None})
    if trust.get("configured") is not True or not host.public_key:
        decision = U.apply_offer(host, None, "offline", lambda _manifest: None, None)
        return _public(host, trust, decision, mesh=None, internet={"attempted": False, "code": None})

    host.offline = True
    mesh = U.on_peer_contact(host, host.public_key)
    incoming = _local_candidate(host.home / "incoming", host.cap)
    inbox = _local_candidate(host.home / "peer-inbox", host.cap)
    candidate = incoming if incoming is not None else inbox
    source = "offline" if incoming is not None else "mesh:file"
    if candidate == "shape":
        decision = U.apply_offer(host, {"manifest": None, "signature": None}, source, lambda _manifest: None, host.public_key)
        return _public(host, trust, decision, mesh=mesh, internet={"attempted": False, "code": None})
    if isinstance(candidate, dict):
        host.offline = True
        decision = _apply_candidate(host, candidate, source)
        return _public(
            host,
            trust,
            decision,
            mesh=mesh,
            internet={"attempted": False, "code": None, "reason": "a local signed artifact was the candidate"},
        )

    release_configured = bool(trust.get("release_url")) or trust.get("established_runtime_release") is True
    if not release_configured:
        decision = _refuse(host, "UPDATE-NO-RELEASE", "online")
        return _public(host, trust, decision, mesh=mesh, internet={"attempted": False, "code": "UPDATE-NO-RELEASE"})

    host.offline = False
    host.internet_reachable()
    offer = host._offer if isinstance(host._offer, dict) else None
    pre_ok = False
    if isinstance(offer, dict) and isinstance(offer.get("manifest"), dict):
        pre_ok = V.verify_manifest(offer.get("manifest"), offer.get("signature"), host.load(), host.public_key).get("ok") is True
    if host._bound and pre_ok and offer is not None and offer.get("refused") is not True:
        decision = _refuse(host, "UPDATE-BOUND", "online")
        return _public(host, trust, decision, mesh=mesh, internet={"attempted": True, "code": "UPDATE-BOUND"})
    decision = U.on_internet_reach(host, host.public_key)
    internet = {"attempted": True, "code": decision.get("code"), "live": False}
    return _public(host, trust, decision, mesh=mesh, internet=internet)


def update_proposal(actor: str):
    """Ethics proposal for ``azos update``. The name is not a privilege."""
    from azos.gate import Proposal

    return Proposal(
        action="update",
        definition="Adopt a signed artifact under .azos/update or record that trust is not configured.",
        evidence="Operator asked for the signed install and update path on this machine.",
        impact="Writes only under .azos/update. Does not replace the host OS, boot a kernel, or open a radio.",
        actor=actor,
    )


UPDATE_ACTIONS = frozenset({"update"})


def trust_view(root: Path | str) -> dict[str, Any]:
    """Read-only trust report. Does not apply and does not write."""
    trust = load_trust(root)
    return {
        "spec": U.UPDATER_SPEC,
        "configured": trust.get("configured") is True,
        "enabled": trust.get("enabled") is True and trust.get("trust_refused") is not True,
        "live": False,
        "product": trust.get("product"),
        "key_fingerprint": trust.get("key_fingerprint") if trust.get("configured") is True else None,
        "code": "UPDATE-OFF" if trust.get("enabled") is not True and trust.get("trust_refused") is not True else trust.get("code"),
        "radio_phy": False,
        "second_device": False,
        "satellite_relay": "HELD",
        "hardware": False,
        "need": list(trust.get("need") or []),
    }
