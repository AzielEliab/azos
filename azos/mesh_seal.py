"""Sealed UDP mesh frame (AZMESH2).

The cleartext AZMESH1 frame was a header plus a CRC. This frame replaces
that checksum with the shared seal:

- ephemeral X25519 against the recipient's static key
- HKDF-SHA-256, salt ``AZP-NS-1.0`` (aziel-runtime envelope-v2)
- info ``version|network_id|message_id|nonce`` (envelope-v2)
- AES-256-GCM with the canonical header as associated data (envelope-v2)

The recipient pin is the full 32-byte X25519 public key, the width
qnm-node uses for a static box key. A truncated hint is refused.
An AZMESH1 frame, a bad tag, or a substituted pin does not open.

Cap-7 is not ICANN. This module does not bind a public registrar,
does not open a paid satellite, and does not mark a packet live.

Author: Aziel Eliab.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from typing import Any

MAGIC = b"AZMESH2"
LEGACY_MAGIC = b"AZMESH1"
FRAME_VERSION = 2
ENVELOPE_VERSION = "AZP-NS-1.0"
NETWORK_ID = "azos-mesh"
KEY_LEN = 32
NONCE_LEN = 12
MESSAGE_ID_LEN = 16
SRC_LEN = 16
DST_LEN = 16
HOST_LEN = 32
TAG_LEN = 16
HEADER_LEN = (
    len(MAGIC)
    + 1
    + SRC_LEN
    + DST_LEN
    + HOST_LEN
    + KEY_LEN
    + KEY_LEN
    + NONCE_LEN
    + MESSAGE_ID_LEN
    + 2
)
MAX_PAYLOAD = 1200

_OFF_VERSION = len(MAGIC)
_OFF_SRC = _OFF_VERSION + 1
_OFF_DST = _OFF_SRC + SRC_LEN
_OFF_HOST = _OFF_DST + DST_LEN
_OFF_EPH = _OFF_HOST + HOST_LEN
_OFF_PEER = _OFF_EPH + KEY_LEN
_OFF_NONCE = _OFF_PEER + KEY_LEN
_OFF_MID = _OFF_NONCE + NONCE_LEN
_OFF_LEN = _OFF_MID + MESSAGE_ID_LEN


class MeshSealError(Exception):
    """Caller passed a key or a payload this seal will not write."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _crypto():
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF

    return hashes, serialization, X25519PrivateKey, X25519PublicKey, AESGCM, HKDF


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _canon(header: dict[str, str]) -> bytes:
    return json.dumps(header, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _pad(text: str, size: int) -> bytes:
    raw = text.encode("utf-8")[:size]
    return raw + bytes(size - len(raw))


def _text(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def _require_key(raw: bytes, code: str) -> bytes:
    if not isinstance(raw, (bytes, bytearray)) or len(raw) != KEY_LEN:
        raise MeshSealError(code)
    return bytes(raw)


def public_from_private(static_private: bytes) -> bytes:
    """Raw 32-byte X25519 public key. Refuses any other length."""
    _require_key(static_private, "MESH-SEAL-KEY")
    try:
        _, serialization, X25519PrivateKey, _, _, _ = _crypto()
    except Exception as exc:  # noqa: BLE001
        raise MeshSealError("MESH-SEAL-UNAVAILABLE") from exc
    private = X25519PrivateKey.from_private_bytes(bytes(static_private))
    return private.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )


def _header_fields(
    *,
    src: bytes,
    dst: bytes,
    host: bytes,
    eph_public: bytes,
    peer_public: bytes,
    nonce: bytes,
    message_id: bytes,
) -> dict[str, str]:
    return {
        "dst": b64url(dst),
        "eph_public_key": b64url(eph_public),
        "host": b64url(host),
        "message_id": message_id.hex(),
        "network_id": NETWORK_ID,
        "nonce": b64url(nonce),
        "peer_public_key": b64url(peer_public),
        "src": b64url(src),
        "version": ENVELOPE_VERSION,
    }


def _info(header: dict[str, str]) -> bytes:
    return f"{header['version']}|{header['network_id']}|{header['message_id']}|{header['nonce']}".encode("utf-8")


def _derive(shared: bytes, header: dict[str, str]) -> bytes:
    hashes, _, _, _, _, HKDF = _crypto()
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=ENVELOPE_VERSION.encode("utf-8"),
        info=_info(header),
    ).derive(shared)


def _refuse(code: str) -> dict[str, Any]:
    return {
        "ok": False,
        "code": code,
        "payload": None,
        "packet_live": False,
        "mock": False,
        "public_icann": False,
        "bgp": False,
        "cap7_is_path": False,
        "satellite_relay": "HELD",
    }


def seal_frame(
    src: str,
    dst: str,
    host: str,
    payload: bytes,
    *,
    peer_public: bytes,
    ephemeral_private: bytes | None = None,
    nonce: bytes | None = None,
    message_id: bytes | None = None,
) -> bytes:
    """Seal ``payload`` to the full peer public key. The header is the AEAD associated data."""
    if not isinstance(payload, (bytes, bytearray)):
        raise MeshSealError("MESH-SEAL-PAYLOAD")
    if len(payload) > MAX_PAYLOAD:
        raise MeshSealError("MESH-SEAL-PAYLOAD")
    peer = _require_key(peer_public, "MESH-SEAL-PIN")
    try:
        _, serialization, X25519PrivateKey, X25519PublicKey, AESGCM, _ = _crypto()
    except MeshSealError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise MeshSealError("MESH-SEAL-UNAVAILABLE") from exc
    if ephemeral_private is None:
        ephemeral = X25519PrivateKey.generate()
    else:
        ephemeral = X25519PrivateKey.from_private_bytes(_require_key(ephemeral_private, "MESH-SEAL-KEY"))
    if nonce is None:
        nonce_b = os.urandom(NONCE_LEN)
    else:
        if not isinstance(nonce, (bytes, bytearray)) or len(nonce) != NONCE_LEN:
            raise MeshSealError("MESH-SEAL-NONCE")
        nonce_b = bytes(nonce)
    if message_id is None:
        mid = os.urandom(MESSAGE_ID_LEN)
    else:
        if not isinstance(message_id, (bytes, bytearray)) or len(message_id) != MESSAGE_ID_LEN:
            raise MeshSealError("MESH-SEAL-MESSAGE")
        mid = bytes(message_id)
    eph_public = ephemeral.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    src_b = _pad(src, SRC_LEN)
    dst_b = _pad(dst, DST_LEN)
    host_b = _pad(host, HOST_LEN)
    header = _header_fields(
        src=src_b,
        dst=dst_b,
        host=host_b,
        eph_public=eph_public,
        peer_public=peer,
        nonce=nonce_b,
        message_id=mid,
    )
    try:
        shared = ephemeral.exchange(X25519PublicKey.from_public_bytes(peer))
        key = _derive(shared, header)
        ciphertext = AESGCM(key).encrypt(nonce_b, bytes(payload), _canon(header))
    except MeshSealError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise MeshSealError("MESH-SEAL-REFUSED") from exc
    if len(ciphertext) != len(payload) + TAG_LEN:
        raise MeshSealError("MESH-SEAL-REFUSED")
    raw = bytearray(HEADER_LEN + len(ciphertext))
    raw[0:len(MAGIC)] = MAGIC
    raw[_OFF_VERSION] = FRAME_VERSION
    raw[_OFF_SRC:_OFF_DST] = src_b
    raw[_OFF_DST:_OFF_HOST] = dst_b
    raw[_OFF_HOST:_OFF_EPH] = host_b
    raw[_OFF_EPH:_OFF_PEER] = eph_public
    raw[_OFF_PEER:_OFF_NONCE] = peer
    raw[_OFF_NONCE:_OFF_MID] = nonce_b
    raw[_OFF_MID:_OFF_LEN] = mid
    raw[_OFF_LEN] = (len(ciphertext) >> 8) & 0xFF
    raw[_OFF_LEN + 1] = len(ciphertext) & 0xFF
    raw[HEADER_LEN:] = ciphertext
    return bytes(raw)


def open_frame(frame: bytes, *, static_private: bytes) -> dict[str, Any]:
    """Open one frame. Unsealed, tampered, and third-party frames stay closed."""
    if not isinstance(frame, (bytes, bytearray)):
        return _refuse("MESH-UNSEALED")
    blob = bytes(frame)
    if len(blob) < len(LEGACY_MAGIC):
        return _refuse("MESH-UNSEALED")
    if blob[:len(LEGACY_MAGIC)] == LEGACY_MAGIC or blob[:len(MAGIC)] != MAGIC:
        return _refuse("MESH-UNSEALED")
    if len(blob) < HEADER_LEN or blob[_OFF_VERSION] != FRAME_VERSION:
        return _refuse("MESH-UNSEALED")
    try:
        local_public = public_from_private(static_private)
    except MeshSealError:
        return _refuse("MESH-WRONG-KEY")
    peer = blob[_OFF_PEER:_OFF_NONCE]
    if len(peer) != KEY_LEN or peer != local_public:
        return _refuse("MESH-WRONG-KEY")
    ct_len = (blob[_OFF_LEN] << 8) | blob[_OFF_LEN + 1]
    if ct_len < TAG_LEN or HEADER_LEN + ct_len != len(blob):
        return _refuse("MESH-TAMPER")
    src_b = blob[_OFF_SRC:_OFF_DST]
    dst_b = blob[_OFF_DST:_OFF_HOST]
    host_b = blob[_OFF_HOST:_OFF_EPH]
    eph_public = blob[_OFF_EPH:_OFF_PEER]
    nonce_b = blob[_OFF_NONCE:_OFF_MID]
    mid = blob[_OFF_MID:_OFF_LEN]
    header = _header_fields(
        src=src_b,
        dst=dst_b,
        host=host_b,
        eph_public=eph_public,
        peer_public=peer,
        nonce=nonce_b,
        message_id=mid,
    )
    try:
        _, _, X25519PrivateKey, X25519PublicKey, AESGCM, _ = _crypto()
        private = X25519PrivateKey.from_private_bytes(bytes(static_private))
        shared = private.exchange(X25519PublicKey.from_public_bytes(eph_public))
        key = _derive(shared, header)
        payload = AESGCM(key).decrypt(nonce_b, blob[HEADER_LEN:], _canon(header))
    except Exception:  # noqa: BLE001
        return _refuse("MESH-TAMPER")
    return {
        "ok": True,
        "code": "MESH-SEAL-OK",
        "src": _text(src_b),
        "dst": _text(dst_b),
        "host": _text(host_b),
        "payload": payload,
        "peer_public_key": peer,
        "message_id": mid.hex(),
        "packet_live": False,
        "mock": False,
        "public_icann": False,
        "bgp": False,
        "cap7_is_path": False,
        "satellite_relay": "HELD",
        "frame_magic": "AZMESH2",
        "envelope": ENVELOPE_VERSION,
    }


def header_sha256(frame: bytes) -> str:
    """Hash of the clear header. Tests use it to show the payload is not sitting in front."""
    if not isinstance(frame, (bytes, bytearray)) or len(frame) < HEADER_LEN:
        return ""
    return hashlib.sha256(bytes(frame[:HEADER_LEN])).hexdigest()
