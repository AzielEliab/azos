"""Sealed UDP mesh frames: open, tamper, and a third party."""

from __future__ import annotations

import subprocess
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

from azos.carriers import encode_mesh, exchange_mesh, parse_mesh
from azos.mesh_seal import (
    ENVELOPE_VERSION,
    HEADER_LEN,
    LEGACY_MAGIC,
    MAGIC,
    NETWORK_ID,
    open_frame,
    seal_frame,
)


def _box() -> tuple[bytes, bytes]:
    private = X25519PrivateKey.generate()
    secret = private.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    public = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return secret, public


def _legacy(payload: bytes) -> bytes:
    import zlib

    raw = bytearray(74 + len(payload))
    raw[0:7] = LEGACY_MAGIC
    raw[7] = 1
    raw[8:24] = b"az-node-a" + bytes(7)
    raw[24:40] = b"az-node-b" + bytes(7)
    raw[40:72] = b"host" + bytes(28)
    raw[72] = (len(payload) >> 8) & 0xFF
    raw[73] = len(payload) & 0xFF
    raw[74:] = payload
    body = bytes(raw)
    return body + zlib.crc32(body).to_bytes(4, "big")


def test_seal_opens_for_the_pinned_peer_only() -> None:
    alice_sk, _alice_pk = _box()
    bob_sk, bob_pk = _box()
    payload = b"mesh-payload"
    frame = seal_frame("az-node-a", "az-node-b", "abc", payload, peer_public=bob_pk)
    assert frame.startswith(MAGIC)
    assert not frame.startswith(LEGACY_MAGIC)
    assert payload not in frame
    opened = open_frame(frame, static_private=bob_sk)
    assert opened["ok"] is True
    assert opened["code"] == "MESH-SEAL-OK"
    assert opened["payload"] == payload
    assert opened["src"] == "az-node-a"
    assert opened["dst"] == "az-node-b"
    assert opened["host"] == "abc"
    assert opened["peer_public_key"] == bob_pk
    assert len(opened["peer_public_key"]) == 32
    assert opened["packet_live"] is False
    assert opened["public_icann"] is False
    assert opened["bgp"] is False
    assert opened["cap7_is_path"] is False
    assert opened["satellite_relay"] == "HELD"
    assert opened["envelope"] == ENVELOPE_VERSION
    same = encode_mesh("az-node-a", "az-node-b", "abc", payload, peer_public=bob_pk)
    assert parse_mesh(same, static_private=bob_sk)["payload"] == payload
    assert parse_mesh(same, static_private=alice_sk) is None


def test_tamper_and_unsealed_frames_are_refused() -> None:
    bob_sk, bob_pk = _box()
    frame = bytearray(seal_frame("az-node-a", "az-node-b", "abc", b"secret", peer_public=bob_pk))
    frame[-1] ^= 0x01
    tampered = open_frame(bytes(frame), static_private=bob_sk)
    assert tampered["ok"] is False
    assert tampered["code"] == "MESH-TAMPER"
    assert tampered["payload"] is None
    rewritten = bytearray(seal_frame("az-node-a", "az-node-b", "abc", b"secret", peer_public=bob_pk))
    rewritten[HEADER_LEN - 20] ^= 0x01
    pinned = open_frame(bytes(rewritten), static_private=bob_sk)
    assert pinned["ok"] is False
    assert pinned["payload"] is None
    legacy = open_frame(_legacy(b"secret"), static_private=bob_sk)
    assert legacy["ok"] is False
    assert legacy["code"] == "MESH-UNSEALED"
    assert parse_mesh(_legacy(b"secret"), static_private=bob_sk) is None
    assert open_frame(b"not-a-frame", static_private=bob_sk)["code"] == "MESH-UNSEALED"


def test_third_party_cannot_open() -> None:
    _alice_sk, _alice_pk = _box()
    bob_sk, bob_pk = _box()
    eve_sk, eve_pk = _box()
    frame = seal_frame("az-node-a", "az-node-b", "abc", b"secret", peer_public=bob_pk)
    eve = open_frame(frame, static_private=eve_sk)
    assert eve["ok"] is False
    assert eve["code"] == "MESH-WRONG-KEY"
    assert eve["payload"] is None
    stolen = bytearray(frame)
    stolen[104:136] = eve_pk
    stolen_open = open_frame(bytes(stolen), static_private=eve_sk)
    assert stolen_open["ok"] is False
    assert stolen_open["code"] == "MESH-TAMPER"
    assert open_frame(frame, static_private=bob_sk)["ok"] is True
    try:
        seal_frame("a", "b", "c", b"x", peer_public=bob_pk[:16])
    except Exception as exc:
        assert getattr(exc, "code", "") == "MESH-SEAL-PIN"
    else:
        raise AssertionError("a truncated peer key was accepted")


def test_envelope_v2_schedule_opens_in_node(tmp_path: Path) -> None:
    bob_sk, bob_pk = _box()
    payload = b"envelope-v2-payload"
    nonce = bytes(range(12))
    message_id = bytes(range(16))
    ephemeral = bytes(range(32, 64))
    frame = seal_frame(
        "az-node-a",
        "az-node-b",
        "host-id",
        payload,
        peer_public=bob_pk,
        ephemeral_private=ephemeral,
        nonce=nonce,
        message_id=message_id,
    )
    script = tmp_path / "open-envelope.mjs"
    script.write_text(
        """
import { webcrypto } from "node:crypto";
const crypto = webcrypto;
const frame = Buffer.from(process.argv[2], "hex");
const secret = Buffer.from(process.argv[3], "hex");
const HEADER = 166;
function b64url(buf) {
  return Buffer.from(buf).toString("base64url");
}
const header = {
  dst: b64url(frame.subarray(24, 40)),
  eph_public_key: b64url(frame.subarray(72, 104)),
  host: b64url(frame.subarray(40, 72)),
  message_id: Buffer.from(frame.subarray(148, 164)).toString("hex"),
  network_id: "azos-mesh",
  nonce: b64url(frame.subarray(136, 148)),
  peer_public_key: b64url(frame.subarray(104, 136)),
  src: b64url(frame.subarray(8, 24)),
  version: "AZP-NS-1.0",
};
const keys = Object.keys(header).sort();
const aad = Buffer.from("{" + keys.map((key) => JSON.stringify(key) + ":" + JSON.stringify(header[key])).join(",") + "}");
const info = Buffer.from(`${header.version}|${header.network_id}|${header.message_id}|${header.nonce}`);
const prefix = Uint8Array.from([0x30, 0x2e, 0x02, 0x01, 0x00, 0x30, 0x05, 0x06, 0x03, 0x2b, 0x65, 0x6e, 0x04, 0x22, 0x04, 0x20]);
const pkcs8 = new Uint8Array(prefix.length + secret.length);
pkcs8.set(prefix, 0);
pkcs8.set(secret, prefix.length);
const sk = await crypto.subtle.importKey("pkcs8", pkcs8, { name: "X25519" }, false, ["deriveBits"]);
const eph = await crypto.subtle.importKey("raw", frame.subarray(72, 104), { name: "X25519" }, false, []);
const shared = await crypto.subtle.deriveBits({ name: "X25519", public: eph }, sk, 256);
const hkdf = await crypto.subtle.importKey("raw", shared, "HKDF", false, ["deriveBits"]);
const aes = await crypto.subtle.deriveBits(
  { name: "HKDF", hash: "SHA-256", salt: Buffer.from("AZP-NS-1.0"), info },
  hkdf,
  256,
);
const key = await crypto.subtle.importKey("raw", aes, "AES-GCM", false, ["decrypt"]);
try {
  const plain = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: frame.subarray(136, 148), additionalData: aad },
    key,
    frame.subarray(HEADER),
  );
  process.stdout.write(Buffer.from(plain).toString("utf8"));
} catch (err) {
  process.stdout.write("FAIL");
}
""".lstrip()
    )
    opened = subprocess.run(
        ["node", str(script), frame.hex(), bob_sk.hex()],
        check=False,
        capture_output=True,
        text=True,
    )
    assert opened.returncode == 0, opened.stderr
    assert opened.stdout == payload.decode("utf-8")
    assert NETWORK_ID == "azos-mesh"
    flipped = bytearray(frame)
    flipped[8] ^= 0x01
    refused = subprocess.run(
        ["node", str(script), bytes(flipped).hex(), bob_sk.hex()],
        check=False,
        capture_output=True,
        text=True,
    )
    assert refused.stdout == "FAIL"
    eve_sk, _eve_pk = _box()
    outsider = subprocess.run(
        ["node", str(script), frame.hex(), eve_sk.hex()],
        check=False,
        capture_output=True,
        text=True,
    )
    assert outsider.stdout == "FAIL"
    assert HEADER_LEN == 166


def test_same_machine_udp_stays_sealed_and_not_a_second_device() -> None:
    report = exchange_mesh("127.0.0.1")
    if report.get("code") == "MESH-HOST-ABSENT":
        return
    assert report["bytes_match"] is True
    assert report["frame_magic"] == "AZMESH2"
    assert report["packet_live"] is False
    assert report["second_device"] is False
    assert report["public_icann"] is False
    assert report["bgp"] is False
    assert report["code"] == "SAME-MACHINE-REFUSED"
