"""ARK-ACCOUNT-1.0 on-device client (USER-SIGNIN-ARK-1.0, aziel-runtime #330).

One (username, password) -> one vault. A wrong password is a different, empty
vault (ARK deniability). Nothing secret is stored: the device keeps only
vault_id, the public key and ciphertext rows. A lost password leaves the
history unreadable forever (no recovery, by design).

Keys are derived on this device; only the public key, Ed25519 signatures and
AES-256-GCM ciphertext ever reach the runtime FragGate (device mode). The key
schedule is byte-identical to aziel-runtime src/account/ark-kdf.js.

Needs the `cryptography` package (pip install cryptography); it is not a declared dependency. Without it
every call refuses ARK-UNAVAILABLE (fail closed). Default OFF on the runtime.
Author: Aziel Eliab. SPDX-License-Identifier: Apache-2.0
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SPEC = "ARK-ACCOUNT-1.0"
ITERS = 100_000  # Cloudflare Workers PBKDF2 maximum, so hosted and device keys match
GENESIS = "0" * 64
USERNAME_RE = re.compile(r"^[a-z0-9._-]{3,32}$")
KIND_RE = re.compile(r"^[a-z0-9_.-]{1,40}$")


class ArkError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _crypto():
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    except Exception as exc:  # pragma: no cover - exercised only without the extra
        raise ArkError("ARK-UNAVAILABLE") from exc
    return hashes, Ed25519PrivateKey, Ed25519PublicKey, AESGCM, HKDF, Encoding, PublicFormat


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: str | bytes) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


def normalize_username(raw: Any) -> str:
    if not isinstance(raw, str):
        raise ArkError("ARK-INPUT")
    d = "".join(c for c in unicodedata.normalize("NFKD", raw) if not unicodedata.category(c).startswith("M"))
    u = unicodedata.normalize("NFKC", d).lower()
    if not USERNAME_RE.fullmatch(u):
        raise ArkError("ARK-INPUT")
    return u


def normalize_password(raw: Any) -> bytes:
    if not isinstance(raw, str):
        raise ArkError("ARK-INPUT")
    pw = unicodedata.normalize("NFKC", raw).encode()
    if not 8 <= len(pw) <= 1024:
        raise ArkError("ARK-INPUT")
    return pw


def vault_id_of(pub_hex: str) -> str:
    if not isinstance(pub_hex, str) or not re.fullmatch(r"[0-9a-f]{64}", pub_hex):
        raise ArkError("ARK-INPUT")
    return sha256_hex("ARK-ACCOUNT:v1:vault|" + pub_hex)


def aad(vault_id: str, seq: int) -> bytes:
    return f"ARK:V1|{vault_id}|{seq}".encode()


# Dual lattice rules, identical to aziel-runtime src/dual-lattice.js.
def lattice_primary(document_hash: str, primary_prev: str | None) -> str:
    return sha256_hex(canonical({"document": document_hash, "prev": primary_prev or GENESIS}))


def lattice_online_secondary(primary: str, secondary_prev: str | None) -> str:
    return sha256_hex(canonical({"offline": False, "prev": secondary_prev or GENESIS, "primary": primary}))


def lattice_offline_secondary(document_hash: str, username: str) -> str:
    return sha256_hex(canonical({"primary": document_hash, "username": str(username)}))


def lattice_handle(vault_id: str) -> str:
    """The only 'username' a lattice row ever carries: a hash, never the name."""
    return "ark." + vault_id


def append_message(body: dict) -> bytes:
    keys = ("spec", "vault_id", "seq", "prev", "kind", "ct_sha256", "ts")
    return canonical({k: body[k] for k in keys}).encode()


def recall_message(vault_id: str, ts: int) -> bytes:
    return f"ARK-ACCOUNT:v1:recall|{vault_id}|{ts}".encode()


def verify_sig(pub_hex: str, sig_hex: str, msg: bytes) -> bool:
    _, _, Pub, *_ = _crypto()
    try:
        Pub.from_public_bytes(bytes.fromhex(pub_hex)).verify(bytes.fromhex(sig_hex), msg)
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class ArkAccount:
    pub: str
    vault_id: str
    rl_subject: str
    _sk: Any = field(repr=False)
    _ek: bytes = field(repr=False)

    def __repr__(self) -> str:
        return f"ArkAccount(vault_id={self.vault_id})"

    def sign(self, msg: bytes) -> str:
        return self._sk.sign(msg).hex()

    def seal(self, seq: int, plaintext: str) -> str:
        AESGCM = _crypto()[3]
        iv = os.urandom(12)
        return base64.b64encode(iv + AESGCM(self._ek).encrypt(iv, plaintext.encode(), aad(self.vault_id, seq))).decode()

    def open(self, seq: int, b64: str) -> str:
        AESGCM = _crypto()[3]
        raw = base64.b64decode(b64)
        try:
            return AESGCM(self._ek).decrypt(raw[:12], raw[12:], aad(self.vault_id, seq)).decode()
        except Exception as exc:
            raise ArkError("ARK-DECRYPT") from exc

    # Device-mode FragGate payloads (POST /v1/fraggate/call {slug:"ark", op, payload}).
    def open_request(self) -> dict:
        return {"slug": "ark", "op": "account_open", "payload": {"vault_pub": self.pub}}

    def append_request(self, seq: int, prev: str, data: str, kind: str = "note", ts: int | None = None) -> dict:
        if not KIND_RE.fullmatch(kind):
            raise ArkError("ARK-INPUT")
        ts = int(time.time() * 1000) if ts is None else ts
        ct = self.seal(seq, data)
        body = {"spec": SPEC, "vault_id": self.vault_id, "seq": seq, "prev": prev, "kind": kind, "ct_sha256": sha256_hex(ct), "ts": ts}
        payload = {"vault_pub": self.pub, "seq": seq, "prev": prev, "kind": kind, "ct_b64": ct, "ct_sha256": body["ct_sha256"], "ts": ts, "user_sig": self.sign(append_message(body))}
        return {"slug": "ark", "op": "account_append", "payload": payload}

    def recall_request(self, ts: int | None = None, limit: int = 20) -> dict:
        ts = int(time.time() * 1000) if ts is None else ts
        return {"slug": "ark", "op": "account_recall", "payload": {"vault_pub": self.pub, "ts": ts, "limit": limit, "user_sig": self.sign(recall_message(self.vault_id, ts))}}


def derive(username: str, password: str, iterations: int = ITERS) -> ArkAccount:
    hashes, Priv, _, _, HKDF, Encoding, PublicFormat = _crypto()
    u = normalize_username(username)
    pw = normalize_password(password)
    salt = hashlib.sha256(("ARK-ACCOUNT:v1:salt|" + u).encode()).digest()
    master = hashlib.pbkdf2_hmac("sha256", pw, salt, iterations, 32)

    def sub(info: str) -> bytes:
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=salt, info=info.encode()).derive(master)

    sk = Priv.from_private_bytes(sub("ARK:SIGN"))
    ek = sub("ARK:ENC")
    pub = sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    return ArkAccount(pub, vault_id_of(pub), sha256_hex("ARK-ACCOUNT:v1:rl|" + u), sk, ek)


class OfflineVault:
    """Append-only offline rows on this device (secondary chain).

    Each row is sealed with row_hash and carries the dual lattice with the
    OFFLINE secondary rule, keyed by lattice_handle(vault_id) - never the
    username. Rows stay local until the 3-chain tie-break sync ships (it waits
    on the audited tie-break formula). Files hold only ciphertext and hashes.
    """

    def __init__(self, root: Path | str):
        self.root = Path(root)

    def _path(self, vault_id: str) -> Path:
        return self.root / "ark-accounts" / f"{vault_id}.jsonl"

    def rows(self, vault_id: str) -> list[dict]:
        p = self._path(vault_id)
        if not p.exists():
            return []  # a wrong password and a new vault look the same
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    def append(self, acct: ArkAccount, data: str, kind: str = "note", ts: int | None = None) -> dict:
        if not KIND_RE.fullmatch(kind) or not isinstance(data, str) or not data:
            raise ArkError("ARK-INPUT")
        rows = self.rows(acct.vault_id)
        if verify_rows(rows) is not True:
            raise ArkError("ARK-FAIL-CLOSED")
        prev = rows[-1]["row_hash"] if rows else GENESIS
        prev_primary = rows[-1]["lattice"]["primary"] if rows else GENESIS
        seq = len(rows) + 1
        ts = int(time.time() * 1000) if ts is None else ts
        ct = acct.seal(seq, data)
        ct_sha = sha256_hex(ct)
        body = {"spec": SPEC, "vault_id": acct.vault_id, "seq": seq, "prev": prev, "kind": kind, "ct_sha256": ct_sha, "ts": ts}
        handle = lattice_handle(acct.vault_id)
        row = {
            **body,
            "ct_b64": ct,
            "user_pub": acct.pub,
            "user_sig": acct.sign(append_message(body)),
            "signed_by": "user",
            "lattice": {
                "document_hash": ct_sha,
                "primary": lattice_primary(ct_sha, prev_primary),
                "offline": True,
                "username": handle,
                "secondary": lattice_offline_secondary(ct_sha, handle),
            },
            "synced": False,
        }
        row["row_hash"] = sha256_hex(canonical(row))
        p = self._path(acct.vault_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:  # append-only
            fh.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def recall(self, acct: ArkAccount) -> list[str]:
        rows = self.rows(acct.vault_id)
        if verify_rows(rows) is not True:
            raise ArkError("ARK-FAIL-CLOSED")
        return [acct.open(r["seq"], r["ct_b64"]) for r in rows]


def verify_rows(rows: list[dict]) -> bool | str:
    """Read-only check of one vault's offline rows. True, or the first failing reason."""
    prev, pp = GENESIS, GENESIS
    for i, r in enumerate(rows, start=1):
        if r.get("seq") != i or r.get("prev") != prev:
            return f"link@{i}"
        rest = {k: v for k, v in r.items() if k != "row_hash"}
        if sha256_hex(canonical(rest)) != r.get("row_hash"):
            return f"row_hash@{i}"
        lat = r["lattice"]
        if lat["primary"] != lattice_primary(r["ct_sha256"], pp):
            return f"primary@{i}"
        if lat["username"] != lattice_handle(r["vault_id"]) or lat["secondary"] != lattice_offline_secondary(r["ct_sha256"], lat["username"]):
            return f"secondary@{i}"
        if vault_id_of(r["user_pub"]) != r["vault_id"] or not verify_sig(r["user_pub"], r["user_sig"], append_message(r)):
            return f"user_sig@{i}"
        prev, pp = r["row_hash"], lat["primary"]
    return True
