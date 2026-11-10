"""Signed install/update adoption. Offline success, and the closed failures.

The release key in these tests is generated here and thrown away. It is not
an AZ-OS pin and not the runtime pin. No network release is fetched.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import stat
import tarfile
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from azos import update_engine as U
from azos import update_verify as V
from azos.boot import boot_overlay
from azos.cli import main
from azos.install import adopt_signed, one_click
from azos.sidenet import OfflineNode
from azos.update_apply import apply_candidate, boot_update
from azos.update_verify import RELEASE_KEY_FINGERPRINT, RELEASE_PUBLIC_KEY

GIT = "0123456789abcdef0123456789abcdef01234567"
RELEASE = "https://updates.example/envelope.json"
ARTIFACT_URL = "https://updates.example/azos-payload.tar"


def _keys():
    private = Ed25519PrivateKey.generate()
    raw = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return private, public


def _sign(private, manifest: dict) -> str:
    signature = private.sign(V.canon(manifest).encode())
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def _tar(files: dict[str, bytes], *, mode: int = 0o644) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            info.mode = mode
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _manifest(blob: bytes, *, seq: int, product: str = "azos", channel: str = "stable", name: str = "azos-payload.tar") -> dict:
    return {
        "artifact": {"name": name, "sha256": hashlib.sha256(blob).hexdigest(), "size": len(blob)},
        "channel": channel,
        "git_sha": GIT,
        "issued_at": "2026-11-10T00:00:00Z",
        "prev_manifest_hash": None,
        "product": product,
        "spec": "AZ-UPDATE-MANIFEST-1.0",
        "version": f"0.{seq}.0",
        "version_seq": seq,
    }


def _trust(root: Path, public: str, **extra) -> None:
    body = {
        "spec": "AZOS-UPDATE-TRUST-1.0",
        "product": extra.pop("product", "azos"),
        "public_key": public,
        "auto_update": extra.pop("auto_update", True),
    }
    body.update(extra)
    path = root / ".azos" / "update" / "trust.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body), encoding="utf-8")


def _drop(root: Path, manifest: dict, signature: str, blob: bytes, folder: str = "incoming") -> None:
    directory = root / ".azos" / "update" / folder
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "manifest.sig").write_text(signature + "\n", encoding="utf-8")
    (directory / manifest["artifact"]["name"]).write_bytes(blob)


def _hello(root: Path) -> Path:
    return root / ".azos" / "update" / "generations" / "current" / "tree" / "hello.txt"


def _receipt_codes(root: Path) -> list[str]:
    path = root / ".azos" / "update" / "receipts.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line)["code"] for line in path.read_text(encoding="utf-8").splitlines() if line]


def _floor(root: Path):
    path = root / ".azos" / "update" / "state.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8")).get("floor_seq")


def test_pinned_runtime_key_matches_its_published_fingerprint() -> None:
    assert V.canon({"b": 1, "a": "x"}) == '{"a":"x","b":1}'
    assert V.fingerprint(RELEASE_PUBLIC_KEY) == RELEASE_KEY_FINGERPRINT
    assert len(V.b64u(RELEASE_PUBLIC_KEY)) == 32
    assert V.parse_manifest_text('{"version_seq": 1.0}') is None


def test_missing_trust_is_explicit_and_off(tmp_path: Path) -> None:
    result = boot_update(tmp_path)
    text = json.dumps(result)
    assert result["code"] == "UPDATE-OFF"
    assert result["configured"] is False
    assert result["applied"] is False
    assert result["live"] is False
    assert result["booted"] is False
    assert result["os_yet"] is False
    need = "\n".join(result["need"])
    assert "trust.json" in need and "public_key" in need
    assert any(RELEASE_KEY_FINGERPRINT in item for item in result["need"])
    assert RELEASE_PUBLIC_KEY not in text
    assert "PRIVATE" not in text
    assert result["satellite_relay"] == "HELD"
    assert result["mesh"]["carriers_present"] == []
    assert "image/init does not run this module" in result["boundary"][0]


def test_private_key_field_is_refused_and_not_echoed(tmp_path: Path) -> None:
    secret = "super-secret-value"
    path = tmp_path / ".azos" / "update" / "trust.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "spec": "AZOS-UPDATE-TRUST-1.0",
                "product": "azos",
                "auto_update": True,
                "public_key": "not-used",
                "private_key": secret,
            }
        ),
        encoding="utf-8",
    )
    result = boot_update(tmp_path)
    assert result["code"] == "UPDATE-TRUST-REFUSED"
    assert result["applied"] is False
    assert secret not in json.dumps(result)


def test_runtime_pin_does_not_vouch_for_azos(tmp_path: Path) -> None:
    _trust(tmp_path, RELEASE_PUBLIC_KEY, auto_update=True)
    result = boot_update(tmp_path)
    assert result["code"] == "UPDATE-NO-KEY"
    assert result["applied"] is False
    assert result["configured"] is False
    assert RELEASE_PUBLIC_KEY not in json.dumps(result)
    assert any("does not vouch for product azos" in item for item in result["need"])


def test_offline_signed_adoption_activates_and_boot_stays_unbooted(tmp_path: Path) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"adopted\n"}, mode=0o4755)
    manifest = _manifest(blob, seq=2)
    _trust(tmp_path, public)
    _drop(tmp_path, manifest, _sign(private, manifest), blob)
    booted = boot_overlay(tmp_path)
    assert booted["code"] == "BOOT-ABSENT"
    assert booted["booted"] is False
    assert booted["receipt"] is True
    update = booted["update"]
    assert update["code"] == "UPDATE-OK"
    assert update["applied"] is True
    assert update["live"] is False
    assert update["os_yet"] is False
    assert update["installed"] is False
    assert update["one_click_install_live"] is False
    assert update["source"] == "offline"
    assert update["floor_seq"] == 2
    assert _hello(tmp_path).read_bytes() == b"adopted\n"
    mode = stat.S_IMODE(_hello(tmp_path).stat().st_mode)
    assert mode & 0o7000 == 0
    receipt = json.loads((tmp_path / ".azos" / "boot" / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["booted"] is False
    assert receipt["update_applied"] is True
    assert receipt["update_live"] is False
    assert receipt["update_code"] == "UPDATE-OK"
    click = one_click(tmp_path / "one-click")
    assert click["code"] == "ONE-CLICK-NOT-LIVE"
    assert click["remote_curl"] is False
    assert not (tmp_path / "one-click" / ".azos" / "update" / "generations" / "current").exists()


def test_switch_off_does_not_adopt_a_valid_artifact(tmp_path: Path) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"adopted\n"})
    manifest = _manifest(blob, seq=1)
    _trust(tmp_path, public, auto_update=False)
    _drop(tmp_path, manifest, _sign(private, manifest), blob)
    result = adopt_signed(tmp_path)
    assert result["code"] == "UPDATE-OFF"
    assert result["applied"] is False
    assert result["key_fingerprint"] == V.fingerprint(public)
    assert public not in json.dumps(result)
    assert not _hello(tmp_path).exists()


def test_tamper_downgrade_and_bad_signature_leave_the_tree(tmp_path: Path) -> None:
    private, public = _keys()
    first = _tar({"hello.txt": b"first\n"})
    manifest = _manifest(first, seq=1)
    _trust(tmp_path, public)
    _drop(tmp_path, manifest, _sign(private, manifest), first)
    assert boot_update(tmp_path)["code"] == "UPDATE-OK"
    assert _hello(tmp_path).read_bytes() == b"first\n"

    again = boot_update(tmp_path)
    assert again["code"] == "UPDATE-DOWNGRADE"
    assert again["applied"] is False
    assert _floor(tmp_path) == 1
    assert _hello(tmp_path).read_bytes() == b"first\n"

    second = _tar({"hello.txt": b"second\n"})
    bad = _manifest(second, seq=2)
    flipped = bytearray(second)
    flipped[20] ^= 0xFF
    _drop(tmp_path, bad, _sign(private, bad), bytes(flipped))
    tampered = boot_update(tmp_path)
    assert tampered["code"] == "UPDATE-HASH"
    assert tampered["applied"] is False
    assert _floor(tmp_path) == 1
    assert _hello(tmp_path).read_bytes() == b"first\n"

    _drop(tmp_path, bad, "not-a-signature", second)
    refused = boot_update(tmp_path)
    assert refused["code"] == "UPDATE-SIG"
    assert _hello(tmp_path).read_bytes() == b"first\n"
    assert _floor(tmp_path) == 1


def test_channel_and_traversal_and_symlink_do_not_activate(tmp_path: Path) -> None:
    private, public = _keys()
    _trust(tmp_path, public)
    blob = _tar({"hello.txt": b"nope\n"})
    manifest = _manifest(blob, seq=1, channel="rc")
    _drop(tmp_path, manifest, _sign(private, manifest), blob)
    assert boot_update(tmp_path)["code"] == "UPDATE-CHANNEL-REFUSED"
    assert not _hello(tmp_path).exists()

    outside = tmp_path / "outside.txt"
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        info = tarfile.TarInfo(name="../outside.txt")
        payload = b"escaped\n"
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
        link = tarfile.TarInfo(name="link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/tmp"
        archive.addfile(link)
    escaped = buffer.getvalue()
    manifest = _manifest(escaped, seq=2)
    _drop(tmp_path, manifest, _sign(private, manifest), escaped)
    result = boot_update(tmp_path)
    assert result["code"] == "UPDATE-HEALTH"
    assert result["outcome"] == "rolled_back"
    assert result["applied"] is False
    assert not outside.exists()
    assert not _hello(tmp_path).exists()
    assert _floor(tmp_path) == 0


def test_interrupt_and_unready_staging_do_not_replace_current(tmp_path: Path) -> None:
    private, public = _keys()
    first = _tar({"hello.txt": b"kept\n"})
    manifest = _manifest(first, seq=1)
    _trust(tmp_path, public)
    _drop(tmp_path, manifest, _sign(private, manifest), first)
    assert boot_update(tmp_path)["applied"] is True

    second = _tar({"hello.txt": b"new\n"})
    nxt = _manifest(second, seq=2)
    _drop(tmp_path, nxt, _sign(private, nxt), second)

    def before_ready(staging: Path) -> None:
        raise RuntimeError("interrupt")

    stopped = boot_update(tmp_path, hooks={"before_ready": before_ready})
    assert stopped["code"] == "UPDATE-HEALTH"
    assert stopped["outcome"] == "rolled_back"
    assert stopped["applied"] is False
    assert _floor(tmp_path) == 1
    assert _hello(tmp_path).read_bytes() == b"kept\n"
    assert not (tmp_path / ".azos" / "update" / "generations" / "staging").exists()

    partial = tmp_path / ".azos" / "update" / "generations" / "staging"
    partial.mkdir()
    (partial / "partial.txt").write_text("torn\n", encoding="utf-8")
    incoming = tmp_path / ".azos" / "update" / "incoming"
    for child in incoming.iterdir():
        child.unlink()
    recovered = boot_update(tmp_path)
    assert recovered["recovered"] == "staging-discarded"
    assert not partial.exists()
    assert _hello(tmp_path).read_bytes() == b"kept\n"
    assert recovered["code"] == "UPDATE-NO-RELEASE"
    assert recovered["internet"]["attempted"] is False


def test_crash_after_swap_finishes_the_commit_without_lowering_the_floor(tmp_path: Path) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"kept\n"})
    manifest = _manifest(blob, seq=4)
    _trust(tmp_path, public)
    _drop(tmp_path, manifest, _sign(private, manifest), blob)
    assert boot_update(tmp_path)["floor_seq"] == 4
    for child in (tmp_path / ".azos" / "update" / "incoming").iterdir():
        child.unlink()
    state_path = tmp_path / ".azos" / "update" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["installed_seq"] = 0
    state["floor_seq"] = 0
    state["manifest_hash"] = None
    state["last_code"] = None
    state_path.write_text(json.dumps(state), encoding="utf-8")
    result = boot_update(tmp_path)
    assert result["recovered"] == "commit-finished"
    assert result["floor_seq"] == 4
    assert result["code"] == "UPDATE-NO-RELEASE"
    assert _hello(tmp_path).read_bytes() == b"kept\n"

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["floor_seq"] == 4
    blob_path = tmp_path / ".azos" / "update" / "generations" / "current" / "artifact.bin"
    flipped = bytearray(blob_path.read_bytes())
    flipped[0] ^= 0x01
    blob_path.write_bytes(bytes(flipped))
    rejected = boot_update(tmp_path)
    assert rejected["applied"] is False
    assert rejected["recovered"] == "current-rejected"
    assert _floor(tmp_path) == 4
    assert not _hello(tmp_path).exists()


def test_corrupt_state_is_not_reset_to_a_zero_floor(tmp_path: Path) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"nope\n"})
    manifest = _manifest(blob, seq=1)
    _trust(tmp_path, public)
    _drop(tmp_path, manifest, _sign(private, manifest), blob)
    state = tmp_path / ".azos" / "update" / "state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text("{", encoding="utf-8")
    result = boot_update(tmp_path)
    assert result["code"] == "UPDATE-STATE"
    assert result["applied"] is False
    assert state.read_text(encoding="utf-8") == "{"
    assert not _hello(tmp_path).exists()


def test_paused_state_does_not_apply(tmp_path: Path) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"nope\n"})
    manifest = _manifest(blob, seq=1)
    _trust(tmp_path, public)
    _drop(tmp_path, manifest, _sign(private, manifest), blob)
    state = tmp_path / ".azos" / "update" / "state.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    state.write_text(
        json.dumps(U.initial_state("azos", 0) | {"paused": True}),
        encoding="utf-8",
    )
    result = boot_update(tmp_path)
    assert result["code"] == "UPDATE-PAUSED"
    assert result["applied"] is False
    assert not _hello(tmp_path).exists()


def test_oversized_manifest_is_bounded_before_the_artifact_is_read(tmp_path: Path) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"small\n"})
    manifest = _manifest(blob, seq=1)
    manifest["artifact"]["size"] = 10_000_000
    manifest["artifact"]["sha256"] = "ab" * 32
    _trust(tmp_path, public, max_bytes=1024)
    directory = tmp_path / ".azos" / "update" / "incoming"
    directory.mkdir(parents=True)
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (directory / "manifest.sig").write_text(_sign(private, manifest) + "\n", encoding="utf-8")
    marker = directory / manifest["artifact"]["name"]
    marker.write_bytes(b"do-not-need-bytes")
    result = boot_update(tmp_path)
    assert result["code"] == "UPDATE-BOUND"
    assert result["applied"] is False
    assert not _hello(tmp_path).exists()
    assert marker.read_bytes() == b"do-not-need-bytes"


def test_mesh_file_inbox_uses_the_same_signature_gate(tmp_path: Path) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"from-inbox\n"})
    manifest = _manifest(blob, seq=3)
    _trust(tmp_path, public)
    _drop(tmp_path, manifest, _sign(private, manifest), blob, folder="peer-inbox")
    result = boot_update(tmp_path)
    assert result["code"] == "UPDATE-OK"
    assert result["source"] == "mesh:file"
    assert result["applied"] is True
    assert result["hardware"] is False
    assert result["radio_phy"] is False
    assert result["second_device"] is False
    assert result["satellite_relay"] == "HELD"
    assert result["mesh"]["code"] == "UPDATE-CARRIER-ABSENT"
    assert result["mesh"]["carriers_present"] == []
    assert result["live"] is False
    assert _hello(tmp_path).read_bytes() == b"from-inbox\n"
    assert "UPDATE-CARRIER-ABSENT" in _receipt_codes(tmp_path)

    bad = dict(manifest)
    bad["version_seq"] = 4
    bad["version"] = "0.4.0"
    refused = apply_candidate(tmp_path, bad, "zzzz", blob, "mesh:lan")
    assert refused["code"] == "UPDATE-SIG"
    assert refused["applied"] is False
    assert refused["hardware"] is False
    assert refused["second_device"] is False
    assert _floor(tmp_path) == 3
    assert _hello(tmp_path).read_bytes() == b"from-inbox\n"


def test_mesh_engine_refuses_tamper_and_accepts_the_same_bytes_as_online(tmp_path: Path) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"mesh\n"})
    manifest = _manifest(blob, seq=1)
    signature = _sign(private, manifest)

    class Stub:
        def __init__(self, fetched: bytes) -> None:
            self.enabled = True
            self.node_id = "stub"
            self.offline = True
            self.state = U.initial_state("azos", 0)
            self.fetched = fetched
            self.staged = None

        def now(self) -> str:
            return "2026-11-10T00:00:00Z"

        def load(self) -> dict:
            return json.loads(json.dumps(self.state))

        def save(self, state: dict) -> None:
            self.state = json.loads(json.dumps(state))

        def write_receipt(self, row: dict) -> None:
            self.row = row

        def carrier_present(self, carrier: str) -> bool:
            return carrier == "lan"

        def peer_hello(self, carrier: str) -> dict:
            del carrier
            return {"product": "azos", "version_seq": 1, "manifest": manifest, "signature": signature}

        def peer_fetch(self, carrier: str, offered: dict) -> bytes:
            del carrier, offered
            return self.fetched

        def stage(self, data: bytes, offered: dict) -> None:
            del offered
            self.staged = bytes(data)

        def swap(self) -> None:
            return None

        def health_check(self) -> bool:
            return True

        def rollback(self) -> None:
            self.staged = None

    bad = Stub(b"\x00" + blob[1:])
    refused = U.on_peer_contact(bad, public)
    assert refused["code"] == "UPDATE-HASH"
    assert refused["ok"] is False
    assert bad.staged is None
    assert bad.state["floor_seq"] == 0
    assert refused["hardware"] is False

    good = Stub(blob)
    adopted = U.on_peer_contact(good, public)
    assert adopted["code"] == "UPDATE-OK"
    assert adopted["hardware"] is False
    assert adopted["radio_phy"] is False
    assert good.staged == blob
    assert good.state["floor_seq"] == 1

    _trust(tmp_path, public)
    calls: list[str] = []

    def opener(url: str, timeout: float) -> bytes:
        del timeout
        calls.append(url)
        if url == RELEASE:
            body = {"manifest": manifest, "signature": signature, "url": ARTIFACT_URL}
            return json.dumps(body).encode("utf-8")
        if url == ARTIFACT_URL:
            flipped = bytearray(blob)
            flipped[20] ^= 0xFF
            return bytes(flipped)
        raise AssertionError(url)

    _trust(tmp_path, public, release_url=RELEASE)
    online = boot_update(tmp_path, hooks={"opener": opener})
    assert online["code"] == "UPDATE-HASH"
    assert online["internet"]["attempted"] is True
    assert online["applied"] is False
    assert calls == [RELEASE, ARTIFACT_URL]
    assert not _hello(tmp_path).exists()


def test_internet_adoption_is_bounded_and_optional(tmp_path: Path, monkeypatch) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"online\n"})
    manifest = _manifest(blob, seq=5)
    signature = _sign(private, manifest)
    calls: list[str] = []

    def opener(url: str, timeout: float) -> bytes:
        del timeout
        calls.append(url)
        if url == RELEASE:
            return json.dumps({"manifest": manifest, "signature": signature, "url": ARTIFACT_URL}).encode("utf-8")
        if url == ARTIFACT_URL:
            return blob
        raise AssertionError(url)

    _trust(tmp_path, public, release_url=RELEASE)
    adopted = boot_update(tmp_path, hooks={"opener": opener})
    assert adopted["code"] == "UPDATE-OK"
    assert adopted["source"] == "online"
    assert adopted["applied"] is True
    assert adopted["live"] is False
    assert _hello(tmp_path).read_bytes() == b"online\n"
    assert calls == [RELEASE, ARTIFACT_URL]

    huge = dict(manifest)
    huge["version_seq"] = 6
    huge["version"] = "0.6.0"
    huge["artifact"] = dict(manifest["artifact"])
    huge["artifact"]["size"] = 9_000_000
    huge_calls: list[str] = []

    def huge_opener(url: str, timeout: float) -> bytes:
        del timeout
        huge_calls.append(url)
        if url == RELEASE:
            return json.dumps({"manifest": huge, "signature": _sign(private, huge), "url": ARTIFACT_URL}).encode()
        raise AssertionError("artifact was downloaded")

    _trust(tmp_path, public, release_url=RELEASE, max_bytes=2048)
    for child in (tmp_path / ".azos" / "update" / "incoming").glob("*"):
        if child.exists():
            child.unlink()
    bounded = boot_update(tmp_path, hooks={"opener": huge_opener})
    assert bounded["code"] == "UPDATE-BOUND"
    assert bounded["applied"] is False
    assert huge_calls == [RELEASE]
    assert _floor(tmp_path) == 5
    assert _hello(tmp_path).read_bytes() == b"online\n"

    def boom(url: str, timeout: float) -> bytes:
        del url, timeout
        raise AssertionError("http release must not be fetched")

    monkeypatch.setattr("azos.update_apply._urllib_get", boom)
    _trust(tmp_path, public, release_url="http://updates.example/envelope.json")
    offline = boot_update(tmp_path)
    assert offline["code"] == "UPDATE-NO-RELEASE"
    assert offline["internet"]["attempted"] is False


def test_established_runtime_release_without_an_asset_is_not_invented(tmp_path: Path) -> None:
    calls: list[str] = []

    def opener(url: str, timeout: float) -> bytes:
        del timeout
        calls.append(url)
        return json.dumps({"prerelease": False, "draft": False, "assets": []}).encode("utf-8")

    path = tmp_path / ".azos" / "update" / "trust.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "spec": "AZOS-UPDATE-TRUST-1.0",
                "product": "aziel-runtime",
                "auto_update": True,
                "established_runtime_release": True,
            }
        ),
        encoding="utf-8",
    )
    result = boot_update(tmp_path, hooks={"opener": opener})
    assert result["code"] == "UPDATE-NO-RELEASE"
    assert result["applied"] is False
    assert result["live"] is False
    assert result["product"] == "aziel-runtime"
    assert result["key_fingerprint"] == RELEASE_KEY_FINGERPRINT
    assert RELEASE_PUBLIC_KEY not in json.dumps(result)
    assert calls == ["https://api.github.com/repos/AzielEliab/aziel-runtime/releases/latest"]
    from azos.update_apply import _NoRedirect, _Transport

    try:
        _NoRedirect().redirect_request(None, None, 302, "moved", {}, "https://elsewhere.example/")
    except _Transport:
        refused = True
    else:
        refused = False
    assert refused is True


def test_sidenet_update_is_the_boot_path_and_not_a_radio(tmp_path: Path, monkeypatch, capsys) -> None:
    node = OfflineNode(tmp_path)
    menu = {item["id"]: item for item in node.menu()["items"]}
    assert menu["auto-update"]["live"] is False
    assert menu["auto-update"]["status"] == "OFF"
    assert menu["auto-update"]["satellite_relay"] == "HELD"
    assert menu["auto-update"]["radio_phy"] is False
    assert node.status()["auto_update"]["live"] is False
    record = node.signed_update(token_hash="ab" * 32)
    assert record["code"] == "UPDATE-OFF"
    assert record["sidenet"] == "SIDENET-P4"
    assert record["live"] is False
    assert record["second_device"] is False

    monkeypatch.chdir(tmp_path)
    assert main(["node", "update", "--json"]) == 0
    body = json.loads(capsys.readouterr().out)
    assert body["code"] == "UPDATE-OFF"
    assert body["satellite_relay"] == "HELD"
    assert main(["update", "--json"]) == 0
    cli = json.loads(capsys.readouterr().out)
    assert cli["code"] == "UPDATE-OFF"
    assert cli["booted"] is False
    assert any("trust.json" in item for item in cli["need"])
    assert main(["halt"]) == 0
    capsys.readouterr()
    assert main(["update", "--json"]) == 1
    assert "halted" in capsys.readouterr().err.lower()


def _rewind(root: Path, floor: int, installed: int) -> None:
    path = root / ".azos" / "update" / "state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["installed_seq"] = installed
    state["floor_seq"] = floor
    state["manifest_hash"] = None
    state["last_code"] = None
    path.write_text(json.dumps(state), encoding="utf-8")
    incoming = root / ".azos" / "update" / "incoming"
    if incoming.is_dir():
        for child in incoming.iterdir():
            child.unlink()


def _active(root: Path) -> bytes | None:
    path = root / ".azos" / "update" / "generations" / "current" / "artifact.bin"
    if not path.is_file() or path.is_symlink():
        return None
    return path.read_bytes()


def _case(root: Path, private, payload: bytes, seq: int) -> None:
    manifest = _manifest(payload, seq=seq, name=f"payload-{seq}.bin")
    _drop(root, manifest, _sign(private, manifest), payload)
    adopted = boot_update(root)
    assert adopted["code"] == "UPDATE-OK"
    assert adopted["floor_seq"] == seq
    assert _active(root) == payload


def test_recover_hashes_empty_truncated_missing_and_real_zero(tmp_path: Path) -> None:
    """Empty bytes are a match only when the manifest declares size 0."""
    private, public = _keys()
    _trust(tmp_path, public)
    _case(tmp_path, private, b"", 1)
    zero = tmp_path / ".azos" / "update" / "generations" / "current" / "artifact.bin"
    zero.write_bytes(b"\x00")
    _rewind(tmp_path, 0, 0)
    poisoned = boot_update(tmp_path)
    assert poisoned["recovered"] == "current-rejected"
    assert poisoned["installed_seq"] in (None, 0)
    assert _floor(tmp_path) in (None, 0)
    assert _active(tmp_path) != b"\x00"

    seq = 1
    for length in (1, 4, 32):
        payload = bytes(range(length))
        seq += 1
        _case(tmp_path, private, payload, seq)
        artifact = tmp_path / ".azos" / "update" / "generations" / "current" / "artifact.bin"
        artifact.write_bytes(b"")
        _rewind(tmp_path, 0, 0)
        emptied = boot_update(tmp_path)
        assert emptied["recovered"] != "commit-finished"
        assert emptied["code"] != "UPDATE-OK"
        assert emptied.get("installed_seq") in (None, 0)
        assert _floor(tmp_path) in (None, 0)
        assert _active(tmp_path) != b""
        seq += 1
        _case(tmp_path, private, payload, seq)
        artifact = tmp_path / ".azos" / "update" / "generations" / "current" / "artifact.bin"
        artifact.write_bytes(payload[:-1])
        _rewind(tmp_path, seq, seq)
        truncated = boot_update(tmp_path)
        assert truncated["applied"] is False
        assert _floor(tmp_path) == seq
        assert _active(tmp_path) != payload[:-1]
        seq += 1
        miss_seq = seq
        _case(tmp_path, private, payload, miss_seq)
        missing_path = tmp_path / ".azos" / "update" / "generations" / "current" / "artifact.bin"
        missing_path.unlink()
        _rewind(tmp_path, miss_seq, miss_seq)
        missing = boot_update(tmp_path)
        assert missing["recovered"] == "current-rejected"
        assert missing["applied"] is False
        assert _floor(tmp_path) == miss_seq
        assert _active(tmp_path) is None or _active(tmp_path) == payload


def test_trust_anchor_refuses_group_write_symlink_and_other_owner(tmp_path: Path, monkeypatch) -> None:
    private, public = _keys()
    blob = _tar({"hello.txt": b"secret-path\n"})
    manifest = _manifest(blob, seq=1)
    _trust(tmp_path, public)
    path = tmp_path / ".azos" / "update" / "trust.json"
    path.chmod(0o666)
    _drop(tmp_path, manifest, _sign(private, manifest), blob)
    refused = boot_update(tmp_path)
    assert refused["code"] == "UPDATE-TRUST-REFUSED"
    assert refused["configured"] is False
    assert refused["applied"] is False
    assert public not in json.dumps(refused)
    assert not _hello(tmp_path).exists()
    path.chmod(0o600)
    directory = path.parent
    directory.chmod(0o777)
    open_dir = boot_update(tmp_path)
    assert open_dir["code"] == "UPDATE-TRUST-REFUSED"
    assert open_dir["applied"] is False
    directory.chmod(0o700)
    linked = tmp_path / "elsewhere-trust.json"
    linked.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.unlink()
    path.symlink_to(linked)
    assert boot_update(tmp_path)["code"] == "UPDATE-TRUST-REFUSED"
    path.unlink()
    path.write_text(linked.read_text(encoding="utf-8"), encoding="utf-8")
    path.chmod(0o600)

    real_uid = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: real_uid + 1)
    owned = boot_update(tmp_path)
    assert owned["code"] == "UPDATE-TRUST-REFUSED"
    assert owned["applied"] is False
    assert owned["configured"] is False


def _hold_lock(root: str, ready: str, seconds: float) -> None:
    import time
    from pathlib import Path

    from azos.update_apply import UpdateLock

    lock = UpdateLock(Path(root) / ".azos" / "update")
    assert lock.acquire()
    Path(ready).write_text("held", encoding="utf-8")
    try:
        time.sleep(seconds)
    finally:
        lock.release()


def _hold_until_killed(root: str, ready: str) -> None:
    import time
    from pathlib import Path

    from azos.update_apply import UpdateLock

    lock = UpdateLock(Path(root) / ".azos" / "update")
    assert lock.acquire()
    Path(ready).write_text("held", encoding="utf-8")
    time.sleep(30)


def _apply_job(root: str, manifest: dict, signature: str, blob: bytes, sink) -> None:
    from azos.update_apply import apply_candidate

    result = apply_candidate(root, manifest, signature, blob, "offline")
    sink.put((result.get("code"), result.get("floor_seq"), result.get("installed_seq")))


def test_concurrent_updates_keep_the_highest_verified_floor(tmp_path: Path) -> None:
    import multiprocessing
    import os
    import time

    private, public = _keys()
    _trust(tmp_path, public)
    low = b"low-seq"
    high = b"high-seq-bytes"
    low_manifest = _manifest(low, seq=2, name="low.bin")
    high_manifest = _manifest(high, seq=6, name="high.bin")
    low_sig = _sign(private, low_manifest)
    high_sig = _sign(private, high_manifest)
    ctx = multiprocessing.get_context("spawn")
    sink = ctx.Queue()
    first = ctx.Process(target=_apply_job, args=(str(tmp_path), low_manifest, low_sig, low, sink))
    second = ctx.Process(target=_apply_job, args=(str(tmp_path), high_manifest, high_sig, high, sink))
    first.start()
    second.start()
    first.join(10)
    second.join(10)
    assert first.exitcode == 0 and second.exitcode == 0
    codes = [sink.get(timeout=5), sink.get(timeout=5)]
    assert _floor(tmp_path) == 6
    assert _active(tmp_path) == high
    assert any(code == "UPDATE-OK" for code, _floor_seq, _installed in codes)
    assert all(item[1] is None or item[1] <= 6 for item in codes)
    same = b"same-bytes"
    same_manifest = _manifest(same, seq=8, name="same.bin")
    same_sig = _sign(private, same_manifest)
    again = ctx.Queue()
    left = ctx.Process(target=_apply_job, args=(str(tmp_path), same_manifest, same_sig, same, again))
    right = ctx.Process(target=_apply_job, args=(str(tmp_path), same_manifest, same_sig, same, again))
    left.start()
    right.start()
    left.join(10)
    right.join(10)
    assert left.exitcode == 0 and right.exitcode == 0
    pair = [again.get(timeout=5)[0], again.get(timeout=5)[0]]
    assert "UPDATE-OK" in pair
    assert pair.count("UPDATE-OK") == 1
    assert "UPDATE-DOWNGRADE" in pair
    assert _floor(tmp_path) == 8
    assert _active(tmp_path) == same
    ready = tmp_path / "lock-ready"
    holder = ctx.Process(target=_hold_lock, args=(str(tmp_path), str(ready), 5))
    holder.start()
    for _ in range(50):
        if ready.is_file():
            break
        time.sleep(0.05)
    blocked = boot_update(tmp_path)
    assert blocked["code"] == "UPDATE-LOCK"
    assert blocked["applied"] is False
    assert _floor(tmp_path) == 8
    assert _active(tmp_path) == same
    holder.join(10)
    crashed = ctx.Process(target=_hold_until_killed, args=(str(tmp_path), str(ready)))
    ready.unlink()
    crashed.start()
    for _ in range(50):
        if ready.is_file():
            break
        time.sleep(0.05)
    os.kill(crashed.pid, 9)
    crashed.join(10)
    resumed = boot_update(tmp_path)
    assert resumed["code"] != "UPDATE-LOCK"
    assert _floor(tmp_path) == 8
    assert _active(tmp_path) == same


def test_init_does_not_call_the_userspace_updater() -> None:
    init = (Path(__file__).resolve().parents[1] / "image" / "init").read_text(encoding="utf-8")
    assert "update_apply" not in init
    assert "AUTO_UPDATE" not in init
    assert 'guardian: absent' in init or "guardian: absent" in init
