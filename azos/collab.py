"""AZ-OS side of AZBot node collaborative forensic (Design 1.0).

The local session shell re-gates an AZBot handoff (five ethics gates, ARC
token, closed action). On pass, AZ-OS packages a FragGate envelope for the
local AZBot process. AZ-OS does not fetch that door and does not open a port.

A returned receipt is appended to the lattices this package already exposes:
TemporalLock × StaticClock (``IntegrityLattice``) and the ChainLock dual-lattice
formula (``runtime_primary`` / ``runtime_offline_secondary``). Other parties on
the session can read those tips. They cannot rewrite them.

Remain-OFF stays: public AZ-OS exec / shell / lattice are not packaged, vault
wipe / scorch / unlock stay local-only, and this module does not enable mesh
radios. Proxied GET /v1/mesh mode flags are the runtime's. This module does
not rewrite them. Cap-7 stays a name, not ICANN.

Author: Aziel Eliab.
"""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path
from typing import Any

from azos.chains import GENESIS, content_hash
from azos.errors import AppendOnlyError, AuthorizationError, AzosError, HaltedError
from azos.gate import Proposal, authorize
from azos.invite import invite_text
from azos.runtime_lattice import runtime_offline_secondary, runtime_primary

SPEC = "AZBOT-NODE-COLLAB-1.0"
TETHER_SPEC = "AZRT-AZOS-TETHER-1.0"
AUTHOR = "Aziel Eliab"
HANDOFF_ACTION = "azbot_handoff"
FRAGGATE_CALL = "https://aziel-runtime.vibelock.workers.dev/v1/fraggate/call"
LOCAL_QNM_NODE = "https://github.com/AzielEliab/qnm-node"
CAP7_SENTENCE = "Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP."
GET_MESH_ENABLES = False
REWRITES_QNM_FLAGS = False
PUBLIC_MESH_ENABLE_INVENTED = False
MAX_PAYLOAD_BYTES = 65536

_TOKEN_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
_PARTY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")

# FragGate azos exec / shell / lattice stay refused (REMAIN-OFF item 8).
PUBLIC_AZOS_OPS = frozenset({"exec", "shell", "lattice"})
# Vault destructive ops stay local-only / FG-STUB. Not a public handoff.
VAULT_OPS = frozenset({"wipe", "scorch", "unlock"})
REMAIN_OFF_OPS = frozenset({
    "deanonymize",
    "invent_mark",
    "backdate",
    "rollback",
    "public_rollback",
})


def honesty() -> dict[str, Any]:
    """Facts this tether is allowed to say. It does not speak for the mesh proxy."""
    return {
        "spec": SPEC,
        "tether": TETHER_SPEC,
        "author": AUTHOR,
        "share": "receipt-tips-only",
        "rewrite": False,
        "fetched": False,
        "second_door": False,
        "single_door": True,
        "door": FRAGGATE_CALL,
        "bind": "127.0.0.1",
        "public_port": False,
        "public_exec": "refused",
        "public_shell": "refused",
        "public_lattice": "refused",
        "remain_off_item": 8,
        "vault_wipe": "local-only",
        "vault_scorch": "local-only",
        "vault_unlock": "local-only",
        "vault_public": "FG-STUB",
        "deanonymize": "refused",
        "invent_mark": "refused",
        "backdate": "refused",
        "public_rollback": "refused",
        "get_mesh_enables": GET_MESH_ENABLES,
        "public_mesh_enable_invented": PUBLIC_MESH_ENABLE_INVENTED,
        "mesh_need_bearer": "MESH-NEED-BEARER",
        "local_qnm_node": LOCAL_QNM_NODE,
        "mesh_node_live": True,
        "alt_internet_live": True,
        "packet_path_live": True,
        "public_bind": False,
        "rewrites_qnm_flags": REWRITES_QNM_FLAGS,
        "qnm_flags_not_rewritten": [
            "enabled",
            "mesh_default",
            "auto_heal",
            "node_gate",
            "anonymity_network",
            "vpn",
        ],
        "qnm_note": (
            "Softwares tip publishes mesh_node_live, alt_internet_live, and packet_path_live true. "
            "This tether does not flip those flags or other OPERATOR-OVERRIDE lives. "
            "GET /v1/mesh does not enable radios. public_bind stays false. "
            "This tether does not invent a public enable."
        ),
        "cap7": "Cap-7",
        "aziel": ".aziel",
        "cap7_is_path": False,
        "aziel_is_path": False,
        "cap7_public_egress": False,
        "public_icann": False,
        "bgp": False,
        "cap7_note": CAP7_SENTENCE,
        "public_door": "FG-STUB",
        "second_device": False,
        "live": False,
    }


def _refuse(code: str, *, gates: dict[str, Any] | None = None) -> dict[str, Any]:
    body = honesty()
    body.update({
        "ok": False,
        "passed": False,
        "code": code,
        "envelope": None,
        "written": False,
        "gates": gates,
        "invite": invite_text(),
    })
    return body


def _party_name(name: str) -> str:
    text = str(name or "").strip()
    if not _PARTY_RE.match(text):
        raise AzosError("COLLAB-PARTY")
    return text


class CollabSession:
    """One local multi-party session. Tips are shared. The chain is not."""

    def __init__(self, runtime: Any, session_id: str) -> None:
        self.runtime = runtime
        self.session_id = str(session_id or "")
        self._parties: list[str] = []
        self._envelopes: list[dict[str, Any]] = []
        self._rows: list[dict[str, Any]] = []
        self._load()

    def _path(self) -> Path:
        return self.runtime.session_dir / "collab" / (self.session_id + ".json")

    def _load(self) -> None:
        path = self._path()
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict) or data.get("session") != self.session_id:
            return
        parties = data.get("parties")
        envelopes = data.get("envelopes")
        rows = data.get("rows")
        self._parties = [str(p) for p in parties] if isinstance(parties, list) else []
        self._envelopes = [dict(e) for e in envelopes] if isinstance(envelopes, list) else []
        self._rows = [dict(r) for r in rows] if isinstance(rows, list) else []

    def _save(self) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "spec": SPEC,
            "tether": TETHER_SPEC,
            "author": AUTHOR,
            "session": self.session_id,
            "parties": list(self._parties),
            "envelopes": self._envelopes,
            "rows": self._rows,
            "rewrite": False,
            "share": "receipt-tips-only",
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _ensure_party(self, actor: str) -> None:
        if actor and actor not in self._parties:
            self._parties.append(actor)

    def _live(self, token: str | None) -> dict[str, Any]:
        if self.runtime.halted:
            raise HaltedError()
        return self.runtime.shell._require_session(self.session_id, token)

    def add_party(self, name: str, *, token: str | None) -> dict[str, Any]:
        """Append a party name. Names are not a rewrite of the receipt chain."""
        rec = self._live(token)
        self._ensure_party(str(rec.get("actor") or ""))
        party = _party_name(name)
        if party not in self._parties:
            self._parties.append(party)
            self._save()
        body = honesty()
        body.update({
            "ok": True,
            "session": self.session_id,
            "parties": list(self._parties),
            "written": False,
        })
        return body

    def remove_party(self, *_args: object, **_kwargs: object) -> None:
        raise AppendOnlyError("cannot rewrite: parties are append-only; receipt tips stay")

    def rewrite(self, *_args: object, **_kwargs: object) -> None:
        raise AppendOnlyError("cannot rewrite: multi-party session shares receipt tips only")

    def handoff(
        self,
        *,
        token: str | None,
        slug: str,
        op: str,
        payload: dict[str, Any],
        definition: str,
        evidence: str,
        impact: str,
        actor: str = "",
    ) -> dict[str, Any]:
        """Re-gate, then package a FragGate call. Does not send it."""
        rec = self._live(token)
        session_actor = str(rec.get("actor") or "")
        self._ensure_party(session_actor)
        named = str(actor or session_actor).strip()
        if named not in self._parties:
            return _refuse("COLLAB-PARTY")

        slug_s = str(slug or "").strip()
        op_s = str(op or "").strip()
        if not _TOKEN_RE.match(slug_s) or not _TOKEN_RE.match(op_s):
            return _refuse("COLLAB-INPUT")
        if slug_s == "azos" and op_s in PUBLIC_AZOS_OPS:
            return _refuse("PUBLIC-AZOS-REFUSED")
        if op_s in VAULT_OPS:
            return _refuse("VAULT-LOCAL-ONLY")
        if op_s in REMAIN_OFF_OPS:
            return _refuse("COLLAB-REMAIN-OFF")
        if slug_s == "mesh" and op_s == "enable":
            return _refuse("COLLAB-MESH-ENABLE-REFUSED")
        if not isinstance(payload, dict):
            return _refuse("COLLAB-INPUT")
        try:
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except (TypeError, ValueError):
            return _refuse("COLLAB-INPUT")
        if len(raw.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            return _refuse("COLLAB-INPUT")

        result = authorize(
            Proposal(
                action=HANDOFF_ACTION,
                definition=definition,
                evidence=evidence,
                impact=impact,
                actor=named,
            ),
            frozenset({HANDOFF_ACTION}),
        )
        gates = {
            name: {"pass": check.passed, "reason": check.reason}
            for name, check in result.gates.items()
        }
        if not result.passed:
            return _refuse("GATE-FAIL", gates=gates)

        envelope_id = secrets.token_hex(16)
        payload_sha = content_hash(payload)
        self._envelopes.append({
            "id": envelope_id,
            "slug": slug_s,
            "op": op_s,
            "payload_sha256": payload_sha,
            "actor": named,
            "accepted": False,
        })
        self._save()
        body = honesty()
        body.update({
            "ok": True,
            "passed": True,
            "written": False,
            "gates": gates,
            "session": self.session_id,
            "actor": named,
            "envelope": {
                "id": envelope_id,
                "spec": SPEC,
                "tether": TETHER_SPEC,
                "door": FRAGGATE_CALL,
                "single_door": True,
                "slug": slug_s,
                "op": op_s,
                "payload": payload,
                "payload_sha256": payload_sha,
                "fetched": False,
            },
        })
        return body

    def accept_receipt(
        self,
        *,
        token: str | None,
        envelope_id: str,
        receipt: dict[str, Any],
        result: dict[str, Any] | None = None,
        party: str = "",
    ) -> dict[str, Any]:
        """Append one FragGate receipt onto TemporalLock and ChainLock."""
        rec = self._live(token)
        session_actor = str(rec.get("actor") or "")
        self._ensure_party(session_actor)
        named = str(party or session_actor).strip()
        if named not in self._parties:
            raise AuthorizationError("unauthorized: party is not on this session")
        if not isinstance(receipt, dict):
            raise AzosError("COLLAB-INPUT")
        if result is not None and not isinstance(result, dict):
            raise AzosError("COLLAB-INPUT")
        found = None
        for row in self._envelopes:
            if row.get("id") == envelope_id:
                found = row
                break
        if found is None:
            raise AzosError("COLLAB-ENVELOPE")
        if found.get("accepted") is True:
            raise AzosError("COLLAB-RECEIPT-DOUBLED")
        if not self._verify_rows():
            raise AzosError("COLLAB-CHAIN-BROKEN")

        receipt_sha = content_hash(receipt)
        result_sha = content_hash(result) if isinstance(result, dict) else None
        document: dict[str, Any] = {
            "spec": SPEC,
            "tether": TETHER_SPEC,
            "kind": "azbot-handoff-receipt",
            "session": self.session_id,
            "actor": named,
            "slug": found.get("slug"),
            "op": found.get("op"),
            "envelope_id": envelope_id,
            "payload_sha256": found.get("payload_sha256"),
            "receipt_sha256": receipt_sha,
            "live": False,
        }
        if result_sha is not None:
            document["result_sha256"] = result_sha
        doc_hash = content_hash(document)
        prev = str(self._rows[-1]["primary"]) if self._rows else GENESIS
        primary = runtime_primary(doc_hash, prev)
        secondary = runtime_offline_secondary(doc_hash, named)
        self.runtime.lattice.bind(
            "azbot:handoff",
            summary="FragGate handoff receipt " + str(found.get("slug")) + " " + str(found.get("op")),
            evidence=receipt_sha,
        )
        self._rows.append({
            "document": document,
            "document_hash": doc_hash,
            "prev": prev,
            "primary": primary,
            "secondary": secondary,
            "username": named,
            "live": False,
        })
        found["accepted"] = True
        self._save()
        return self.tip(named)

    def tip(self, party: str) -> dict[str, Any]:
        """Receipt tips for one party. Documents and payloads stay off this view."""
        if not self._verify_rows():
            raise AzosError("COLLAB-CHAIN-BROKEN")
        named = str(party or "").strip()
        if named not in self._parties:
            raise AuthorizationError("unauthorized: party is not on this session")
        snap = self.runtime.lattice.snapshot()
        gear = snap.get("tip") if isinstance(snap, dict) else None
        temporal = None
        if isinstance(gear, dict) and gear.get("hash"):
            temporal = {
                "hash": gear.get("hash"),
                "tick": gear.get("tick"),
                "verified": snap.get("verified") is True,
            }
        body = honesty()
        body.update({
            "ok": True,
            "session": self.session_id,
            "party": named,
            "parties": list(self._parties),
            "temporal_tip": temporal,
            "chainlock_tip": self._chain_tip(),
            "written": False,
        })
        return body

    def _chain_tip(self) -> dict[str, Any]:
        if not self._rows:
            return {
                "primary": GENESIS,
                "secondary": GENESIS,
                "seq": 0,
                "verified": True,
                "empty": True,
            }
        last = self._rows[-1]
        return {
            "primary": last.get("primary"),
            "secondary": last.get("secondary"),
            "seq": len(self._rows),
            "verified": True,
            "empty": False,
        }

    def _verify_rows(self) -> bool:
        prev = GENESIS
        for row in self._rows:
            document = row.get("document")
            if not isinstance(document, dict) or document.get("live") is True or row.get("live") is True:
                return False
            digest = content_hash(document)
            if digest != row.get("document_hash"):
                return False
            if row.get("prev") != prev:
                return False
            username = str(row.get("username") or "")
            if runtime_primary(digest, prev) != row.get("primary"):
                return False
            if runtime_offline_secondary(digest, username) != row.get("secondary"):
                return False
            prev = str(row.get("primary"))
        return True
