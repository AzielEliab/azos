"""SIDENET-P4 — AZ-OS offline node client (stacked OS).

Holds receipts and the presence tip on disk under ``.azos/node/``.
When the operator asks, and only then, it rejoins L0 (aziel-runtime
FragGate over HTTPS). The Softwares desk is not copied here.

This is not a kernel, not a Softwares card, and not qnm-node.
Phoenix is local wait / re-seal. REHEAL does not take a neighbor vote.
Radio PHY is absent. No ICANN name is claimed.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from azos.errors import AzosError
from azos.paths import SESSION_DIRNAME

SPEC = "SIDENET-P4"
LAYER = "stacked-os"
AUTHOR = "Aziel Eliab"
PRODUCT = "azos"
KIND = "instance"
GENESIS_PREV = "0" * 64
USER_AGENT = "Mozilla/5.0"

# Published BAN-SURVIVAL fronts. Same FragGate door. Not four blast radii.
L0_ORIGINS: tuple[str, ...] = (
    "https://aziel-runtime.vibelock.workers.dev",
    "https://www.azielcorpuslibrary.net/runtime",
    "https://www.azieleliab.com/runtime",
    "https://godlock.uk/runtime",
)
L0_PATHS = frozenset({"/v1/health", "/v1/mesh/join", "/v1/mesh/heartbeat"})

QNM_NODE = "https://github.com/AzielEliab/qnm-node"
SELF_PROTECTION = hashlib.sha256(b"azos-sidenet-self-protection").hexdigest()

_PRESENCE = frozenset({"live", "locked", "isolated"})
_HEX64 = set("0123456789abcdef")
_NODE_ID_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789._-")
_FORBIDDEN_KEYS = frozenset(
    {"body", "diff", "file", "bytes", "video", "mp4", "publish", "payload"}
)
_DEFINITIVE = frozenset(
    {
        "MESH-OFF",
        "MESH-NO-BYTES",
        "MESH-NO-NEIGHBOR-HEAL",
        "MESH-EQUIVOCATION",
        "MESH-NO-REWRITE",
        "MESH-NO-LIE",
        "MESH-BAD-INPUT",
        "MESH-UNKNOWN-NODE",
    }
)


class SidenetRefuse(AzosError):
    """A sidenet law refused the call. The code is the reason."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canon(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canon(payload)).hexdigest()


def _is_hex64(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    return all(ch in _HEX64 for ch in value)


def _valid_node_id(value: object) -> bool:
    if not isinstance(value, str) or not (8 <= len(value) <= 80):
        return False
    return all(ch in _NODE_ID_CHARS for ch in value)


def assert_l0_url(url: str) -> str:
    """Refuse any origin that is not a published L0 front, and any extra path."""
    if not isinstance(url, str) or not url.startswith("https://"):
        raise SidenetRefuse("SIDENET-NO-HYDRA", "L0 URL must be https on a named front")
    matched: str | None = None
    path = ""
    for origin in L0_ORIGINS:
        if url == origin:
            matched = origin
            path = "/"
            break
        prefix = origin + "/"
        if url.startswith(prefix):
            matched = origin
            path = "/" + url[len(prefix) :]
            break
    if matched is None:
        raise SidenetRefuse("SIDENET-NO-HYDRA", "unnamed origin refused")
    if path not in L0_PATHS:
        raise SidenetRefuse("SIDENET-NO-HYDRA", "path is not an L0 health, join, or heartbeat")
    return url


def _reject_forbidden(body: dict[str, Any] | None) -> None:
    if not body:
        return
    found = _FORBIDDEN_KEYS.intersection(body)
    if found:
        names = ", ".join(sorted(found))
        raise SidenetRefuse("SIDENET-NO-BYTES", f"tick refuses {names}")


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect is a different host until proven otherwise. Do not follow it."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        raise SidenetRefuse("SIDENET-NO-HYDRA", "L0 redirect refused")


class UrllibTransport:
    """HTTPS to a published L0 front. No redirect. No other host."""

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout
        self._opener = urllib.request.build_opener(_RefuseRedirect)

    def exchange(self, method: str, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        assert_l0_url(url)
        _reject_forbidden(body)
        data = None
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
        if body is not None:
            data = _canon(body)
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read()
                status = int(getattr(response, "status", 200))
        except SidenetRefuse as exc:
            return {"status": 0, "json": None, "error": exc.code}
        except urllib.error.HTTPError as exc:
            raw = exc.read() if exc.fp is not None else b""
            status = int(exc.code)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {"status": 0, "json": None, "error": str(exc)}
        parsed: dict[str, Any] | None
        try:
            loaded = json.loads(raw.decode("utf-8")) if raw else None
            parsed = loaded if isinstance(loaded, dict) else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None
        return {"status": status, "json": parsed, "error": None}


class OfflineNode:
    """Local receipt chain and presence tip. L0 is optional and probed."""

    def __init__(self, root: Path | str | None = None, *, transport: Any | None = None) -> None:
        base = Path(root) if root is not None else Path.cwd()
        self.root = base
        self.dir = base / SESSION_DIRNAME / "node"
        self.receipts_path = self.dir / "receipts.jsonl"
        self.state_path = self.dir / "state.json"
        self.l0_path = self.dir / "l0.json"
        self.transport = transport
        self._receipts: list[dict[str, Any]] = []
        self._tampered = False
        self._state_untrusted = False
        self._verified_prefix = 0
        self.state = self._load_state()
        self.l0 = self._load_l0()
        self._load_receipts()
        self._align_state_to_chain()

    def status(self) -> dict[str, Any]:
        tip = self.tip
        return {
            "spec": SPEC,
            "layer": LAYER,
            "author": AUTHOR,
            "product": PRODUCT,
            "kind": KIND,
            "node_id": self.state["node_id"],
            "posture": self.state["posture"],
            "presence": self.state["presence"],
            "tip": tip,
            "prev": self.state["prev"],
            "seq": self.state["seq"],
            "receipts": len(self._receipts),
            "tip_present": tip is not None,
            "phoenix_wait": bool(self.state["phoenix_wait"]),
            "tampered": self._tampered,
            "verified_prefix": self._verified_prefix,
            "l0": self._l0_public(),
            "softwares_desk": "frozen",
            "softwares_cards": [],
            "qnm_node": {
                "paired": False,
                "required": False,
                "cite": QNM_NODE,
            },
            "radio_phy": False,
            "icann_tld_az": False,
            "rewrite_key": False,
            "lie_to_survive": False,
            "neighbor_vote_to_fix": False,
            "public_hostname_resurrection": False,
            "session": str(self.dir),
        }

    def menu(self) -> dict[str, Any]:
        """Multi-survival menu. SLOT stays SLOT. Unprobed L0 is not LIVE."""
        l0_status = self._l0_status_word()
        items = [
            {
                "id": "local-receipts",
                "status": "LIVE",
                "note": "Append-only receipts in .azos/node/. This process holds them.",
            },
            {
                "id": "local-presence-tip",
                "status": "LIVE",
                "tip_present": self.tip is not None,
                "note": "Presence tip is the local chain tip. Empty until the first seal.",
            },
            {
                "id": "l0-fraggate-https",
                "status": l0_status,
                "note": "aziel-runtime FragGate over HTTPS. LIVE only after a health probe succeeds.",
            },
            {
                "id": "softwares-desk",
                "status": "FROZEN",
                "cards": [],
                "invented": False,
                "note": "Softwares desk stays on L0. This client does not copy or invent cards.",
            },
            {
                "id": "phoenix",
                "status": "LIVE",
                "mode": "local-wait-reseal",
                "waiting": bool(self.state["phoenix_wait"]),
                "neighbor_phoenix": False,
                "public_hostname_resurrection": False,
                "note": "Local wait, then re-seal from this node's own tip. No controller hunt.",
            },
            {
                "id": "reheal",
                "status": "LIVE",
                "neighbor_vote": "refused",
                "vote_to_fix": False,
                "note": "Isolation is the cure. Own last good tip, or phoenix-wait. No vote-to-fix.",
            },
            {
                "id": "plane-a-named-fronts",
                "status": "LIVE",
                "independent": False,
                "blast_radius": "cf-github",
                "origins": list(L0_ORIGINS),
                "note": "Published named fronts. Same FragGate door. Not four independent shelves.",
            },
            {
                "id": "plane-b",
                "status": "SLOT",
                "hash_verify_pass_is_not_live": True,
                "doi": None,
                "note": "Codeberg + archive.org hash-verify PASS is still SLOT. Zenodo is not LIVE.",
            },
            {
                "id": "plane-c",
                "status": "SLOT",
                "attested": False,
                "note": "USB airgap SLOT until CNS-OPERATOR-ATTEST.",
            },
            {
                "id": "live-node-api",
                "status": "SLOT",
                "code": "BAN-NODE-API-NOT-ATTESTED",
                "exec": False,
                "note": "Roster nodes do not publish exec URLs. Open proxy is refused.",
            },
            {
                "id": "cap7-factory-cite",
                "status": "LIVE",
                "is_live_door": False,
                "internet_reachable": False,
                "reached_by_this_node": False,
                "icann_tld_az": False,
                "radio_phy": False,
                "note": "Published factory cite is LIVE. Standard internet does not reach Cap-7. Not an ICANN .az ccTLD. This client does not ping MirageGrid.",
            },
            {
                "id": "radio-phy",
                "status": "ABSENT",
                "fake": False,
                "note": "No Wi-Fi, Bluetooth, RF, or photon PHY on this client. qnm-node probes hardware. Absent is not LIVE.",
            },
            {
                "id": "qnm-node",
                "status": "CITE",
                "paired": False,
                "required": False,
                "cite": QNM_NODE,
                "note": "Full node process is qnm-node. Not vendored. Not required to hold a local tip.",
            },
            {
                "id": "spore",
                "status": "LIVE",
                "metabolism": "pause" if self.state["phoenix_wait"] else "on",
                "invented_heartbeats": False,
                "note": "Failsafe law. Phoenix-wait pauses new seals. It does not pretend the node is dead or LIVE on a radio.",
            },
            {
                "id": "doi",
                "status": "SLOT",
                "doi": None,
                "note": "No Zenodo DOI is claimed.",
            },
        ]
        return {
            "spec": SPEC,
            "layer": LAYER,
            "layer_note": "Stacked on the AZ-OS overlay. Not a base kernel. Not a Softwares card.",
            "author": AUTHOR,
            "identity": AUTHOR,
            "no_lie": True,
            "rewrite_key": False,
            "lie_to_survive": False,
            "icann_tld_az": False,
            "radio_phy": False,
            "softwares_cards_invented": False,
            "softwares_cards": [],
            "neighbor_vote_to_fix": False,
            "phoenix_local_only": True,
            "public_hostname_resurrection": False,
            "fraggate_is_the_door": True,
            "second_door": False,
            "items": items,
        }

    @property
    def tip(self) -> str | None:
        if not self._receipts:
            return None
        return str(self._receipts[-1]["hash"])

    def seal(self, *, token_hash: str) -> dict[str, Any]:
        """Append one local receipt and move the presence tip. No mesh body."""
        self._require_token(token_hash)
        self._require_chain()
        if self.state["phoenix_wait"]:
            raise SidenetRefuse("SIDENET-PHOENIX-WAIT", "phoenix is waiting; reseal locally, do not seal new work")
        return self._append(action="seal", token_hash=token_hash, authority="arc", presence="live")

    def phoenix(self, *, token_hash: str) -> dict[str, Any]:
        """Local wait. The tip stays. No network. No public hostname restore."""
        self._require_token(token_hash)
        if self._tampered:
            self.state["posture"] = "isolated"
            self.state["presence"] = "isolated"
            self.state["phoenix_wait"] = True
            self._save_state()
            return self.status()
        self.state["phoenix_wait"] = True
        self.state["posture"] = "phoenix-wait"
        self.state["phoenix_at"] = _utcnow()
        self.state["last_good_tip"] = self.tip
        self._save_state()
        return self.status()

    def reseal(self, *, token_hash: str) -> dict[str, Any]:
        """Re-seal from this node's own tip after phoenix-wait or isolation."""
        self._require_token(token_hash)
        self._require_chain()
        if not self.state["phoenix_wait"] and self.state["posture"] != "isolated":
            raise SidenetRefuse("SIDENET-NO-RESEAL", "re-seal follows local wait or isolation")
        receipt = self._append(
            action="reseal",
            token_hash=token_hash,
            authority="arc",
            presence="live",
        )
        self.state["phoenix_wait"] = False
        self.state["posture"] = "offline"
        self.state["presence"] = "live"
        self.state["last_good_tip"] = receipt["hash"]
        self._save_state()
        return receipt

    def reheal(
        self,
        *,
        token_hash: str | None = None,
        vote: bool = False,
        neighbor_tip: str | None = None,
        neighbor_prev: str | None = None,
    ) -> dict[str, Any]:
        """Own tip, or keep waiting. A neighbor vote is refused."""
        if vote or neighbor_tip or neighbor_prev:
            raise SidenetRefuse(
                "SIDENET-NO-VOTE",
                "neighbor vote-to-fix refused; isolation is the cure",
            )
        self._require_token(token_hash or "")
        if self._tampered:
            raise SidenetRefuse("SIDENET-TAMPER", "tamper isolates; this client will not splice the chain")
        return {
            "ok": True,
            "code": "SIDENET-OWN-TIP",
            "cure": "phoenix-wait" if self.state["phoenix_wait"] or self.state["posture"] == "isolated" else "own-tip",
            "tip": self.tip,
            "changed": False,
            "neighbor_vote_to_fix": False,
        }

    def observe_foreign(self, prev: str, tip_hash: str) -> dict[str, Any]:
        """A foreign tip is not adopted. Same prev and a different tip isolates."""
        if not _is_hex64(prev) or not _is_hex64(tip_hash):
            raise SidenetRefuse("SIDENET-BAD-INPUT", "prev and tip must be 64 hex characters")
        current = self.tip
        if current is None:
            raise SidenetRefuse("SIDENET-NO-FOREIGN-TIP", "no local tip yet; a foreign tip is not genesis")
        if tip_hash == current:
            return {"ok": True, "code": "SIDENET-SAME-TIP", "changed": False, "tip": current}
        our_prev = str(self._receipts[-1]["prev"])
        if prev == our_prev:
            self.state["posture"] = "isolated"
            self.state["presence"] = "isolated"
            self.state["phoenix_wait"] = True
            self._save_state()
            if not self._tampered:
                self._append(
                    action="isolate",
                    token_hash=SELF_PROTECTION,
                    authority="self-protection",
                    presence="isolated",
                )
            return {
                "ok": False,
                "code": "SIDENET-EQUIVOCATION",
                "changed": False,
                "adopted": False,
                "tip": self.tip,
                "posture": "isolated",
            }
        raise SidenetRefuse("SIDENET-NO-FOREIGN-TIP", "foreign tip refused; neighbors do not heal this node")

    def rejoin(self, *, token_hash: str) -> dict[str, Any]:
        """Probe L0 and rejoin when HTTPS answers. Failure leaves the local tip."""
        self._require_token(token_hash)
        if self.state["phoenix_wait"]:
            raise SidenetRefuse("SIDENET-PHOENIX-WAIT", "phoenix waits locally; it does not hunt L0")
        self._require_chain()
        if self.tip is None:
            self.seal(token_hash=token_hash)
        transport = self.transport if self.transport is not None else UrllibTransport()
        last_error = "no published front answered"
        reached_origin: str | None = None
        definitive: str | None = None
        presence = self.state["presence"] if self.state["presence"] in _PRESENCE else "isolated"
        for origin in L0_ORIGINS:
            health_url = assert_l0_url(origin + "/v1/health")
            health = self._exchange(transport, "GET", health_url, None)
            if not _http_ok(health):
                last_error = _exchange_error(health) or last_error
                continue
            reached_origin = origin
            join_body = {
                "product": PRODUCT,
                "node_id": self.state["node_id"],
                "label": "AZ-OS sidenet",
                "presence": presence,
                "kind": KIND,
            }
            _reject_forbidden(join_body)
            joined = self._exchange(transport, "POST", assert_l0_url(origin + "/v1/mesh/join"), join_body)
            code = _mesh_code(_as_mesh_doc(joined))
            if code in _DEFINITIVE:
                definitive = code
                last_error = code
                break
            if not _mesh_accepted(joined):
                last_error = _exchange_error(joined) or last_error
                if int(joined.get("status") or 0) in {403, 429, 502, 503, 504, 0}:
                    continue
                break
            remote_id = (_as_mesh_doc(joined) or {}).get("node_id")
            if remote_id is not None and remote_id != self.state["node_id"]:
                definitive = "SIDENET-ID-MISMATCH"
                last_error = "SIDENET-ID-MISMATCH"
                break
            beat = {
                "node_id": self.state["node_id"],
                "presence": presence,
                "tip_hash": self.tip,
                "prev": self.state["prev"],
            }
            _reject_forbidden(beat)
            heart = self._exchange(
                transport,
                "POST",
                assert_l0_url(origin + "/v1/mesh/heartbeat"),
                beat,
            )
            heart_code = _mesh_code(_as_mesh_doc(heart))
            if heart_code in _DEFINITIVE or not _mesh_accepted(heart):
                self._write_l0(
                    probed=True,
                    reachable=True,
                    origin=origin,
                    joined=False,
                    error=heart_code or _exchange_error(heart) or "heartbeat refused",
                )
                self.state["posture"] = "degraded"
                self._save_state()
                return {
                    "ok": False,
                    "code": heart_code or "SIDENET-HEARTBEAT",
                    "reachable": True,
                    "joined": False,
                    "origin": origin,
                    "tip": self.tip,
                    "softwares_desk": "frozen",
                }
            self._write_l0(probed=True, reachable=True, origin=origin, joined=True, error=None)
            self.state["posture"] = "joined"
            self.state["presence"] = presence
            self._save_state()
            return {
                "ok": True,
                "code": "SIDENET-JOINED",
                "reachable": True,
                "joined": True,
                "origin": origin,
                "tip": self.tip,
                "softwares_desk": "frozen",
                "softwares_cards": [],
            }
        reachable = reached_origin is not None
        self._write_l0(
            probed=True,
            reachable=reachable,
            origin=reached_origin,
            joined=False,
            error=definitive or last_error,
        )
        if self.state["posture"] == "joined":
            self.state["posture"] = "offline"
            self._save_state()
        return {
            "ok": False,
            "code": definitive or "SIDENET-L0-UNREACHABLE",
            "reachable": reachable,
            "joined": False,
            "origin": reached_origin,
            "tip": self.tip,
            "error": definitive or last_error,
            "softwares_desk": "frozen",
        }

    def restore_public_hostname(self) -> None:
        raise SidenetRefuse(
            "SIDENET-NO-RESURRECTION",
            "phoenix does not restore a public hostname",
        )

    def rewrite(self, *_args: object, **_kwargs: object) -> None:
        raise SidenetRefuse("SIDENET-NO-REWRITE", "no rewrite key")

    def _append(
        self,
        *,
        action: str,
        token_hash: str,
        authority: str,
        presence: str,
    ) -> dict[str, Any]:
        prev = self.tip if self.tip is not None else GENESIS_PREV
        seq = int(self.state["seq"]) + 1
        material = {
            "seq": seq,
            "timestamp": _utcnow(),
            "action": action,
            "node_id": self.state["node_id"],
            "presence": presence,
            "prev": prev,
            "token_hash": token_hash,
            "authority": authority,
        }
        receipt = dict(material)
        receipt["hash"] = _digest(material)
        self.dir.mkdir(parents=True, exist_ok=True)
        line = json.dumps(receipt, sort_keys=True, separators=(",", ":"))
        with self.receipts_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
            handle.flush()
        self._receipts.append(receipt)
        self._verified_prefix = len(self._receipts)
        self.state["seq"] = seq
        self.state["prev"] = prev
        self.state["presence"] = presence
        if action != "isolate":
            self.state["last_good_tip"] = receipt["hash"]
        self._save_state()
        return receipt

    def _require_token(self, token_hash: str) -> None:
        if not _is_hex64(token_hash):
            raise SidenetRefuse("SIDENET-NO-TOKEN", "a 64-hex token hash is required")

    def _require_chain(self) -> None:
        if self._tampered or self._state_untrusted:
            raise SidenetRefuse("SIDENET-TAMPER", "tamper isolates; this client will not splice the chain")

    def _align_state_to_chain(self) -> None:
        if self._tampered or self._state_untrusted or not self._receipts:
            return
        last = self._receipts[-1]
        self.state["seq"] = int(last["seq"])
        self.state["prev"] = str(last["prev"])
        self._save_state()

    def _load_receipts(self) -> None:
        if not self.receipts_path.is_file():
            return
        prev_expected = GENESIS_PREV
        verified = 0
        try:
            lines = self.receipts_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            self._tampered = True
            self.state["posture"] = "isolated"
            self.state["presence"] = "isolated"
            return
        for line in lines:
            text = line.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                self._tampered = True
                break
            if not isinstance(data, dict) or not _is_hex64(data.get("hash")):
                self._tampered = True
                break
            material = {
                "seq": data.get("seq"),
                "timestamp": data.get("timestamp"),
                "action": data.get("action"),
                "node_id": data.get("node_id"),
                "presence": data.get("presence"),
                "prev": data.get("prev"),
                "token_hash": data.get("token_hash"),
                "authority": data.get("authority"),
            }
            if _digest(material) != data["hash"] or data.get("prev") != prev_expected:
                self._tampered = True
                break
            self._receipts.append(data)
            prev_expected = str(data["hash"])
            verified += 1
        self._verified_prefix = verified
        if self._tampered:
            self.state["posture"] = "isolated"
            self.state["presence"] = "isolated"
            self.state["phoenix_wait"] = True

    def _blank_state(self) -> dict[str, Any]:
        return {
            "spec": SPEC,
            "layer": LAYER,
            "author": AUTHOR,
            "node_id": "azos." + secrets.token_hex(8),
            "posture": "offline",
            "presence": "live",
            "prev": GENESIS_PREV,
            "seq": 0,
            "phoenix_wait": False,
            "phoenix_at": None,
            "last_good_tip": None,
            "product": PRODUCT,
            "kind": KIND,
        }

    def _untrusted_state(self) -> dict[str, Any]:
        """Keep the corrupt file. Identity is a digest of those bytes, not a new node."""
        self._state_untrusted = True
        try:
            raw = self.state_path.read_bytes()
        except OSError:
            raw = b""
        digest = hashlib.sha256(raw).hexdigest()[:16]
        state = self._blank_state()
        state["node_id"] = "azos.bad." + digest
        state["posture"] = "isolated"
        state["presence"] = "isolated"
        state["phoenix_wait"] = True
        return state

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            state = self._blank_state()
            self._save_state_file(state)
            return state
        try:
            text = self.state_path.read_text(encoding="utf-8")
            loaded = json.loads(text)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return self._untrusted_state()
        if not isinstance(loaded, dict) or not _valid_node_id(loaded.get("node_id")):
            return self._untrusted_state()
        state = self._blank_state()
        state["node_id"] = loaded["node_id"]
        presence = loaded.get("presence")
        state["presence"] = presence if presence in _PRESENCE else "isolated"
        posture = loaded.get("posture")
        state["posture"] = posture if isinstance(posture, str) and posture else "offline"
        prev = loaded.get("prev")
        state["prev"] = prev if _is_hex64(prev) else GENESIS_PREV
        try:
            state["seq"] = int(loaded.get("seq") or 0)
        except (TypeError, ValueError):
            state["seq"] = 0
        state["phoenix_wait"] = bool(loaded.get("phoenix_wait"))
        state["phoenix_at"] = loaded.get("phoenix_at")
        last = loaded.get("last_good_tip")
        state["last_good_tip"] = last if _is_hex64(last) else None
        return state

    def _load_l0(self) -> dict[str, Any]:
        blank = {
            "probed": False,
            "reachable": False,
            "origin": None,
            "joined": False,
            "error": None,
            "softwares_desk": "frozen",
        }
        if not self.l0_path.is_file():
            return blank
        try:
            loaded = json.loads(self.l0_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return blank
        if not isinstance(loaded, dict):
            return blank
        origin = loaded.get("origin")
        if origin is not None and origin not in L0_ORIGINS:
            origin = None
        return {
            "probed": bool(loaded.get("probed")),
            "reachable": bool(loaded.get("reachable")),
            "origin": origin,
            "joined": bool(loaded.get("joined")),
            "error": loaded.get("error") if isinstance(loaded.get("error"), str) else None,
            "softwares_desk": "frozen",
        }

    def _save_state(self) -> None:
        if self._state_untrusted:
            return
        self._save_state_file(self.state)

    def _save_state_file(self, state: dict[str, Any]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        target = self.state_path
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(target)

    def _write_l0(
        self,
        *,
        probed: bool,
        reachable: bool,
        origin: str | None,
        joined: bool,
        error: str | None,
    ) -> None:
        self.l0 = {
            "probed": probed,
            "reachable": reachable,
            "origin": origin,
            "joined": joined,
            "error": error,
            "softwares_desk": "frozen",
        }
        self.dir.mkdir(parents=True, exist_ok=True)
        temporary = self.l0_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.l0, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(self.l0_path)

    def _l0_public(self) -> dict[str, Any]:
        return {
            "status": self._l0_status_word(),
            "probed": bool(self.l0.get("probed")),
            "reachable": bool(self.l0.get("reachable")),
            "joined": bool(self.l0.get("joined")),
            "origin": self.l0.get("origin"),
            "error": self.l0.get("error"),
            "softwares_desk": "frozen",
        }

    def _l0_status_word(self) -> str:
        if not self.l0.get("probed"):
            return "UNPROBED"
        if self.l0.get("reachable"):
            return "LIVE"
        return "UNREACHABLE"

    @staticmethod
    def _exchange(transport: Any, method: str, url: str, body: dict[str, Any] | None) -> dict[str, Any]:
        assert_l0_url(url)
        _reject_forbidden(body)
        try:
            result = transport.exchange(method, url, body)
        except SidenetRefuse:
            raise
        except Exception as exc:  # noqa: BLE001 — transport faults are offline, not a join
            return {"status": 0, "json": None, "error": str(exc)}
        if not isinstance(result, dict):
            return {"status": 0, "json": None, "error": "transport returned no record"}
        return result


def _as_mesh_doc(result: dict[str, Any]) -> dict[str, Any] | None:
    doc = result.get("json")
    if not isinstance(doc, dict):
        return None
    inner = doc.get("result")
    if isinstance(inner, dict) and any(key in inner for key in ("ok", "node_id", "code", "error")):
        merged = dict(inner)
        for key in ("ok", "code", "error", "node_id"):
            if key not in merged and key in doc:
                merged[key] = doc[key]
        return merged
    return doc


def _http_ok(result: dict[str, Any]) -> bool:
    if int(result.get("status") or 0) != 200:
        return False
    doc = _as_mesh_doc(result)
    return isinstance(doc, dict) and doc.get("ok") is not False and not _mesh_code(doc)


def _mesh_code(doc: object) -> str | None:
    if not isinstance(doc, dict):
        return None
    for key in ("code", "error"):
        value = doc.get(key)
        if isinstance(value, str) and value.startswith("MESH-") and value != "MESH-OK":
            return value
        if isinstance(value, str) and value.startswith("SIDENET-"):
            return value
    return None


def _mesh_accepted(result: dict[str, Any]) -> bool:
    if int(result.get("status") or 0) != 200:
        return False
    doc = _as_mesh_doc(result)
    if not isinstance(doc, dict) or doc.get("ok") is False:
        return False
    if _mesh_code(doc):
        return False
    return doc.get("ok") is True or "node_id" in doc


def _exchange_error(result: dict[str, Any]) -> str | None:
    code = _mesh_code(_as_mesh_doc(result))
    if code:
        return code
    error = result.get("error")
    if isinstance(error, str) and error:
        return error
    status = int(result.get("status") or 0)
    if status == 0:
        return "network unavailable"
    return f"HTTP {status}"


def menu_lines(menu: dict[str, Any]) -> str:
    """Plain menu for the terminal."""
    lines = [
        f"{menu.get('spec')}  {menu.get('layer')}",
        f"Author: {menu.get('author')}",
        str(menu.get("layer_note") or ""),
        "",
    ]
    for item in menu.get("items") or []:
        if not isinstance(item, dict):
            continue
        lines.append(f"{item.get('id')}: {item.get('status')}")
    lines.append("")
    lines.append("Next: azos node    or    azos node rejoin")
    return "\n".join(lines) + "\n"


def status_lines(status: dict[str, Any]) -> str:
    tip = status.get("tip") or "(none yet)"
    l0 = status.get("l0") if isinstance(status.get("l0"), dict) else {}
    waiting = "waiting" if status.get("phoenix_wait") else "not waiting"
    return (
        "AZ-OS offline node (SIDENET-P4)\n"
        "Layer: stacked OS\n"
        "Author: Aziel Eliab\n"
        "\n"
        f"Node: {status.get('node_id')}\n"
        f"Posture: {status.get('posture')}\n"
        f"Receipts: {status.get('receipts')}\n"
        f"Presence tip: {tip}\n"
        f"L0 FragGate/HTTPS: {str(l0.get('status', 'UNPROBED')).lower()}\n"
        "Softwares desk: frozen\n"
        f"Phoenix: {waiting}\n"
        "\n"
        "Next: azos node menu    or    azos node seal\n"
    )
