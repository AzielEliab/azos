"""Offline node client for AZnet.

AZnet is the sidenet (AZN-WP-0.1): hash refs, a local memorial, and
integrity refuse. AZ Browser is the browser surface for AZnet. This
module is the AZ-OS client for that sidenet. It keeps hash refs under
``.azos/node/``. It does not host payloads, open a tunnel, join the
suite mesh, or replace FragGate. AZ Browser is a separate product.
This package does not include it. The three AZ-OS layers stay as they are.

Three layers, chosen by need. Each name is an overlay mode. This
process does not install or replace an operating system.

  base        Host OS stays the host OS. AZ-OS is the overlay. Local garden.
  stacked     Same local garden. FragGate HTTPS stays the online door.
  standalone  Same local garden. No shell session. Softwares desk unchanged.

L0 is FragGate over HTTPS. A probe is ``GET /v1/health`` only. It does
not call a FragGate op. Online execution stays on that door.

Author: Aziel Eliab.
"""

from __future__ import annotations

import hashlib
import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

from azos.errors import AzosError
from azos.paths import session_dir

AUTHOR = "Aziel Eliab"
SPEC = "AZOS-NODE-1.0"
SIDENET = "aznet"
SIDENET_SPEC = "AZN-WP-0.1"
BROWSER_SURFACE = "AZ Browser"
BROWSER_SLUG = "azbrowser"
BROWSER_ROLE = "browser surface for AZnet"
CLIENT = "offline-node"
PRODUCT = "azos"

GENESIS_PREV = "0" * 64
GARDEN_CAP = 64
MEMORIAL_CAP = 64
LABEL_CAP = 160
TEXT_CAP = 65536
HEX64 = 64

L0_ORIGIN = "https://aziel-runtime.vibelock.workers.dev"
L0_HEALTH = L0_ORIGIN + "/v1/health"
L0_DOOR = L0_ORIGIN + "/v1/fraggate/call"
L0_MCP = L0_ORIGIN + "/mcp"
USER_AGENT = "Mozilla/5.0"

LAYERS = ("base", "stacked", "standalone")
DEFAULT_LAYER = "base"

# Hosted AZNet refuses these. The local client refuses them too.
_PAYLOAD_KEYS = frozenset(
    {
        "payload",
        "content",
        "body",
        "bytes",
        "file",
        "blob",
        "media",
        "data",
    }
)
_HOST_KEYS = frozenset(
    {
        "host",
        "host_payload",
        "store_payload",
        "serve",
        "serve_content",
        "serve_content_for_peer",
    }
)

NODE_ACTIONS = frozenset({"node_stamp", "node_memorial"})


def node_proposal(action: str, actor: str):
    """Five-gate proposal for one local hash write. Does not call FragGate."""
    from azos.gate import Proposal

    if action not in NODE_ACTIONS:
        raise AzosError(f"unregistered node action: {action}")
    if action == "node_memorial":
        definition = "Append one local AZnet memorial line under .azos/node."
        impact = "Append-only memorial line in .azos/node. No FragGate call. No rewrite."
    else:
        definition = "Append one local AZnet hash ref under .azos/node."
        impact = "Append-only hash ref in .azos/node. Text is not stored. No FragGate call."
    return Proposal(
        action=action,
        definition=definition,
        evidence="Operator asked the offline AZnet client to record a local hash.",
        impact=impact,
        actor=actor or "operator",
    )

LAYER_NEED: dict[str, str] = {
    "base": "Use the host operating system. AZ-OS stays an overlay, with a local AZnet hash garden.",
    "stacked": "Keep the local garden, and leave FragGate HTTPS as the online door.",
    "standalone": "Use the local AZnet hash garden with no shell session and no Softwares desk change.",
}

Transport = Callable[[str], tuple[int, bytes]]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canon(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canon(payload)).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_hex64(value: str) -> bool:
    if not isinstance(value, str) or len(value) != HEX64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def normalize_layer(layer: str | None) -> str:
    name = (layer or DEFAULT_LAYER).strip().lower()
    if name not in LAYERS:
        raise AzosError(
            f'Unknown layer "{layer}". Use base, stacked, or standalone.'
        )
    return name


def payload_host_key(fields: dict[str, Any] | None) -> str | None:
    """Return the field name that asks this client to store or serve a body."""
    src = fields if isinstance(fields, dict) else {}
    for key in _HOST_KEYS:
        if src.get(key) is True:
            return key
    for key in _PAYLOAD_KEYS:
        value = src.get(key)
        if value is None or value is False or value == "":
            continue
        return key
    return None


def pair_view(*, pair_token: str | None = None, pair_flag: str | None = None) -> dict[str, Any]:
    """Report pair fields without storing them.

    A local token string is not a hosted AZ Browser pair. Hosted garden
    ops still require pairing token and flag on the FragGate door.
    The flag value is the slug ``azbrowser``. The display name is AZ Browser.
    """
    token = "" if pair_token is None else str(pair_token).strip()
    flag = "" if pair_flag is None else str(pair_flag).strip().lower()
    token_present = len(token) >= 8
    flag_ok = flag == BROWSER_SLUG
    return {
        "peer": BROWSER_SLUG,
        "peer_name": BROWSER_SURFACE,
        "peer_role": BROWSER_ROLE,
        "token_present": token_present,
        "flag_present": bool(flag),
        "flag_ok": flag_ok,
        "local_fields_present": token_present and flag_ok,
        "hosted_paired": False,
        "local_pair_is_hosted_pair": False,
        "token_stored": False,
        "both_required_on_hosted_garden": True,
        "note": (
            "AZ Browser is the browser surface for AZnet. "
            "Local fields are not a hosted pair. Hosted AZNet garden ops "
            "still require an AZ Browser pairing token and the azbrowser flag through FragGate."
        ),
    }


def _default_transport(url: str) -> tuple[int, bytes]:
    if url != L0_HEALTH:
        raise AzosError("probe URL is fixed to FragGate health")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            return int(response.status), response.read(4096)
    except urllib.error.HTTPError as exc:
        body = exc.read(256)
        return int(exc.code), body


class OfflineNode:
    """Local AZnet hash garden. Append-only files. No payload bytes."""

    def __init__(self, root: Path | str | None = None, *, layer: str | None = None) -> None:
        self.root = Path(root) if root is not None else Path.cwd()
        self.home = session_dir(self.root) / "node"
        self.state_path = self.home / "state.json"
        self.garden_path = self.home / "garden.jsonl"
        self.memorial_path = self.home / "memorial.jsonl"
        self._layer_arg = layer

    def status(
        self,
        *,
        pair_token: str | None = None,
        pair_flag: str | None = None,
        remember: bool = False,
    ) -> dict[str, Any]:
        layer = self._resolved_layer(persist=remember and bool(self._layer_arg))
        garden = self._read_chain(self.garden_path, kind="stamp")
        memorial = self._read_chain(self.memorial_path, kind="memorial")
        record = self._honesty(layer)
        record.update(
            {
                "ok": garden["ok"] and memorial["ok"],
                "op": "status",
                "garden_count": garden["count"],
                "garden_tip": garden["tip"],
                "garden_chain_ok": garden["ok"],
                "memorial_count": memorial["count"],
                "memorial_tip": memorial["tip"],
                "memorial_chain_ok": memorial["ok"],
                "chain_ok": garden["ok"] and memorial["ok"],
                "store": str(self.home),
                "pair": pair_view(pair_token=pair_token, pair_flag=pair_flag),
                "l0": self._l0_word(layer, probed=False),
            }
        )
        if not garden["ok"] or not memorial["ok"]:
            record["code"] = "AZOS-NODE-CHAIN"
            record["chain_note"] = "A local chain failed verify. This client will not rewrite it."
        return record

    def stamp(
        self,
        *,
        text: str | None = None,
        ref: str | None = None,
        label: str = "",
        fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Append one hash ref. Text is hashed in memory and not written."""
        layer = self._resolved_layer()
        host_key = payload_host_key(fields)
        if host_key:
            return self._refuse(
                "AZOS-NODE-NO-PAYLOAD",
                f"Field {host_key} asks to store or serve a body. This client keeps hash refs.",
                layer=layer,
                op="stamp",
            )
        if text is not None and len(text) > TEXT_CAP:
            return self._refuse(
                "AZOS-NODE-TOO-LARGE",
                f"Text is longer than {TEXT_CAP} bytes. It was not hashed and not stored.",
                layer=layer,
                op="stamp",
            )
        digest = self._ref_from(text, ref)
        if isinstance(digest, dict):
            digest["layer"] = layer
            return digest
        chain = self._read_chain(self.garden_path, kind="stamp")
        if not chain["ok"]:
            return self._refuse(
                "AZOS-NODE-CHAIN",
                "Garden chain failed verify. No rewrite and no new stamp.",
                layer=layer,
                op="stamp",
            )
        if chain["count"] >= GARDEN_CAP:
            return self._refuse(
                "AZOS-NODE-CAP",
                f"Local garden holds {GARDEN_CAP} refs. Older refs stay. Nothing was dropped.",
                layer=layer,
                op="stamp",
            )
        entry = self._append(
            self.garden_path,
            kind="stamp",
            prev=chain["tip"],
            body={"label": str(label)[:LABEL_CAP], "ref": digest},
        )
        self._write_state(layer, garden_tip=entry["hash"], garden_count=chain["count"] + 1)
        out = self._honesty(layer)
        out.update(
            {
                "ok": True,
                "op": "stamp",
                "code": "AZOS-NODE-STAMP",
                "ref": digest,
                "hash": entry["hash"],
                "prev_hash": entry["prev_hash"],
                "text_stored": False,
                "hosted_called": False,
                "garden_count": chain["count"] + 1,
            }
        )
        return out

    def verify(self, *, ref: str | None = None, text: str | None = None) -> dict[str, Any]:
        layer = self._resolved_layer()
        chain = self._read_chain(self.garden_path, kind="stamp")
        record = self._honesty(layer)
        record.update(
            {
                "op": "verify",
                "garden_chain_ok": chain["ok"],
                "hosted_called": False,
            }
        )
        if text is not None and len(text) > TEXT_CAP:
            record.update(
                {
                    "ok": False,
                    "code": "AZOS-NODE-TOO-LARGE",
                    "match": False,
                    "note": "Text was not hashed.",
                }
            )
            return record
        expected = None
        if text is not None and text != "":
            expected = sha256_text(text)
        if ref:
            given = str(ref).strip().lower()
            if not is_hex64(given):
                record.update(
                    {
                        "ok": False,
                        "code": "AZOS-NODE-REF",
                        "match": False,
                        "note": "ref must be 64 hex characters.",
                    }
                )
                return record
            if expected is not None and expected != given:
                record.update(
                    {
                        "ok": True,
                        "code": "AZOS-NODE-MISMATCH",
                        "match": False,
                        "ref": given,
                        "text_hash": expected,
                        "in_garden": False,
                        "note": "Text hash and ref differ. Neither was written.",
                    }
                )
                return record
            expected = given
        if expected is None:
            record.update(
                {
                    "ok": False,
                    "code": "AZOS-NODE-EMPTY",
                    "match": False,
                    "note": "Pass a ref or text to verify.",
                }
            )
            return record
        found = any(item.get("ref") == expected for item in chain["entries"])
        record.update(
            {
                "ok": True,
                "code": "AZOS-NODE-VERIFY",
                "match": found and chain["ok"],
                "in_garden": found,
                "ref": expected,
                "text_stored": False,
            }
        )
        if not chain["ok"]:
            record["code"] = "AZOS-NODE-CHAIN"
            record["match"] = False
            record["note"] = "Garden chain failed verify, so a listed ref is not treated as valid."
        return record

    def garden(self) -> dict[str, Any]:
        layer = self._resolved_layer()
        chain = self._read_chain(self.garden_path, kind="stamp")
        record = self._honesty(layer)
        refs = [
            {
                "ref": item.get("ref"),
                "label": item.get("label") or "",
                "hash": item.get("hash"),
                "prev_hash": item.get("prev_hash"),
                "timestamp": item.get("timestamp"),
            }
            for item in chain["entries"]
        ]
        record.update(
            {
                "ok": chain["ok"],
                "op": "garden",
                "count": chain["count"],
                "tip": chain["tip"],
                "refs": refs,
                "cap": GARDEN_CAP,
                "hosted_garden": False,
            }
        )
        if not chain["ok"]:
            record["code"] = "AZOS-NODE-CHAIN"
        return record

    def memorial(self, *, summary: str, evidence: str) -> dict[str, Any]:
        layer = self._resolved_layer()
        summary_s = (summary or "").strip()
        evidence_s = (evidence or "").strip()
        if len(summary_s) < 8 or len(evidence_s) < 8:
            return self._refuse(
                "AZOS-NODE-MEMORIAL",
                "Memorial needs a summary and evidence of at least 8 characters.",
                layer=layer,
                op="memorial",
            )
        chain = self._read_chain(self.memorial_path, kind="memorial")
        if not chain["ok"]:
            return self._refuse(
                "AZOS-NODE-CHAIN",
                "Memorial chain failed verify. No rewrite and no new line.",
                layer=layer,
                op="memorial",
            )
        if chain["count"] >= MEMORIAL_CAP:
            return self._refuse(
                "AZOS-NODE-CAP",
                f"Local memorial holds {MEMORIAL_CAP} lines. Older lines stay. Nothing was dropped.",
                layer=layer,
                op="memorial",
            )
        entry = self._append(
            self.memorial_path,
            kind="memorial",
            prev=chain["tip"],
            body={"summary": summary_s[:LABEL_CAP], "evidence": evidence_s[:LABEL_CAP]},
        )
        self._write_state(layer, memorial_tip=entry["hash"], memorial_count=chain["count"] + 1)
        out = self._honesty(layer)
        out.update(
            {
                "ok": True,
                "op": "memorial",
                "code": "AZOS-NODE-MEMORIAL",
                "hash": entry["hash"],
                "prev_hash": entry["prev_hash"],
                "terminal": True,
                "hosted_called": False,
                "memorial_count": chain["count"] + 1,
            }
        )
        return out

    def memorial_list(self) -> dict[str, Any]:
        layer = self._resolved_layer()
        chain = self._read_chain(self.memorial_path, kind="memorial")
        record = self._honesty(layer)
        lines = [
            {
                "summary": item.get("summary") or "",
                "evidence": item.get("evidence") or "",
                "hash": item.get("hash"),
                "prev_hash": item.get("prev_hash"),
                "timestamp": item.get("timestamp"),
            }
            for item in chain["entries"]
        ]
        record.update(
            {
                "ok": chain["ok"],
                "op": "memorial_list",
                "count": chain["count"],
                "tip": chain["tip"],
                "lines": lines,
                "cap": MEMORIAL_CAP,
                "terminal": True,
            }
        )
        if not chain["ok"]:
            record["code"] = "AZOS-NODE-CHAIN"
        return record

    def bind_once(self) -> dict[str, Any]:
        """Listen on 127.0.0.1, answer one GET, then close.

        This does not bind 0.0.0.0 and it does not enable the suite mesh.
        ``public_bind`` stays false. A loopback answer is not a live mesh
        node and it is not a host kernel.
        """
        token = b"azos-node-bound"
        layer = self._resolved_layer()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path != "/health":
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(token)))
                self.end_headers()
                self.wfile.write(token)

            def log_message(self, fmt: str, *args: object) -> None:
                return

        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        except OSError as exc:
            refused = self._honesty(layer)
            refused.update(
                {
                    "ok": False,
                    "bound": False,
                    "answered": False,
                    "public_bind": False,
                    "host": None,
                    "code": "MESH-NODE-NOT-LIVE",
                    "error": type(exc).__name__,
                }
            )
            return refused
        host, port = httpd.server_address[:2]
        if host != "127.0.0.1":
            httpd.server_close()
            refused = self._honesty(layer)
            refused.update(
                {
                    "ok": False,
                    "bound": False,
                    "answered": False,
                    "public_bind": False,
                    "host": host,
                    "code": "MESH-NODE-NOT-LIVE",
                }
            )
            return refused
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{port}/health"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
            with urllib.request.urlopen(request, timeout=4) as response:
                status = int(response.status)
                body = response.read(64)
        except Exception as exc:  # noqa: BLE001 — a failed bind is not a live node
            status, body = 0, b""
            error: str | None = type(exc).__name__
        else:
            error = None
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join(timeout=2)
        answered = status == 200 and body == token
        record = self._honesty(layer)
        record.update(
            {
                "ok": False,
                "bound": answered,
                "answered": answered,
                "live": False,
                "mesh_node_live": False,
                "kernel": False,
                "public_bind": False,
                "mesh_enable": False,
                "host": "127.0.0.1",
                "port": port,
                "suite_mesh": False,
                "code": "MESH-NODE-NOT-LIVE",
                "error": error,
            }
        )
        return record

    def probe(self, transport: Transport | None = None) -> dict[str, Any]:
        """GET FragGate health. Does not call an op and does not stamp."""
        layer = self._resolved_layer()
        fetch = transport or _default_transport
        record = self._honesty(layer)
        record.update(
            {
                "op": "probe",
                "l0_executed": False,
                "op_called": None,
                "hosted_called": False,
                "url": L0_HEALTH,
                "door": L0_DOOR,
            }
        )
        try:
            status, _body = fetch(L0_HEALTH)
        except Exception as exc:  # noqa: BLE001 — probe must report the failure, not hide it
            record.update(
                {
                    "ok": True,
                    "reachable": False,
                    "l0": "unreachable",
                    "http_status": None,
                    "error": type(exc).__name__,
                    "note": "L0 health did not answer. The local garden was not changed. No FragGate op was called.",
                }
            )
            return record
        answered = isinstance(status, int) and 200 <= status < 500
        record.update(
            {
                "ok": True,
                "reachable": 200 <= int(status) < 300,
                "l0": "reachable" if 200 <= int(status) < 300 else "answered",
                "http_status": int(status),
                "answered": answered,
                "note": (
                    "HTTP status is reachability of GET /v1/health. "
                    "This client did not call a FragGate op."
                ),
            }
        )
        return record

    def _resolved_layer(self, *, persist: bool = False) -> str:
        if self._layer_arg:
            layer = normalize_layer(self._layer_arg)
            if persist:
                self._write_state(layer)
            return layer
        state = self._read_state()
        stored = state.get("layer")
        if isinstance(stored, str) and stored in LAYERS:
            return stored
        return DEFAULT_LAYER

    def _honesty(self, layer: str) -> dict[str, Any]:
        return {
            "product": PRODUCT,
            "client": CLIENT,
            "spec": SPEC,
            "author": AUTHOR,
            "sidenet": SIDENET,
            "sidenet_is_aznet": True,
            "sidenet_spec": SIDENET_SPEC,
            "browser_surface": BROWSER_SURFACE,
            "browser_slug": BROWSER_SLUG,
            "browser_role": BROWSER_ROLE,
            "browser_for": SIDENET,
            "browser_in_this_package": False,
            "browser_is_layer": False,
            "layers_additive": True,
            "products_merged": False,
            "layer": layer,
            "layers": list(LAYERS),
            "need": LAYER_NEED[layer],
            "os_claim": "Overlay mode name. This process does not install or replace an operating system.",
            "host_os": "unchanged",
            "shell_session_required": False,
            "hosted_engine": False,
            "ran_in": "local-process",
            "l0_door": L0_DOOR,
            "l0_health": L0_HEALTH,
            "l0_mcp": L0_MCP,
            "l0_replaced": False,
            "l0_executed": False,
            "payload_host": False,
            "tunnel": False,
            "vpn": False,
            "mesh_enable": False,
            "public_bind": False,
            "softwares_desk": "frozen",
            "softwares_tab": False,
            "prefab_desk_changed": False,
            "kernel": False,
            "network_default": False,
        }

    def _l0_word(self, layer: str, *, probed: bool) -> str:
        if probed:
            return "probed"
        if layer == "stacked":
            return "unprobed"
        return "not-required"

    def _ref_from(self, text: str | None, ref: str | None) -> str | dict[str, Any]:
        given = str(ref).strip().lower() if ref else ""
        if given and not is_hex64(given):
            return self._refuse(
                "AZOS-NODE-REF",
                "ref must be 64 hex characters.",
                layer=self._resolved_layer(),
                op="stamp",
            )
        hashed = None
        if text is not None and text != "":
            hashed = sha256_text(text)
        if hashed and given and hashed != given:
            return self._refuse(
                "AZOS-NODE-MISMATCH",
                "Text hash and ref differ. Nothing was stored.",
                layer=self._resolved_layer(),
                op="stamp",
            )
        if hashed:
            return hashed
        if given:
            return given
        return self._refuse(
            "AZOS-NODE-EMPTY",
            "Stamp needs --text or --ref. Nothing was stored.",
            layer=self._resolved_layer(),
            op="stamp",
        )

    def _refuse(self, code: str, note: str, *, layer: str, op: str) -> dict[str, Any]:
        out = self._honesty(layer)
        out.update(
            {
                "ok": False,
                "op": op,
                "code": code,
                "note": note,
                "text_stored": False,
                "hosted_called": False,
            }
        )
        return out

    def _append(self, path: Path, *, kind: str, prev: str, body: dict[str, Any]) -> dict[str, Any]:
        material: dict[str, Any] = {
            "kind": kind,
            "timestamp": _utcnow(),
            "prev_hash": prev,
        }
        material.update(body)
        material["hash"] = _digest({k: v for k, v in material.items() if k != "hash"})
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")
            handle.flush()
        return material

    def _read_chain(self, path: Path, *, kind: str) -> dict[str, Any]:
        if not path.is_file():
            return {"ok": True, "count": 0, "tip": GENESIS_PREV, "entries": []}
        entries: list[dict[str, Any]] = []
        prev = GENESIS_PREV
        try:
            raw_lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return {"ok": False, "count": 0, "tip": GENESIS_PREV, "entries": []}
        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError:
                return {"ok": False, "count": len(entries), "tip": prev, "entries": entries}
            if not isinstance(item, dict):
                return {"ok": False, "count": len(entries), "tip": prev, "entries": entries}
            if item.get("kind") != kind:
                return {"ok": False, "count": len(entries), "tip": prev, "entries": entries}
            if str(item.get("prev_hash") or "") != prev:
                return {"ok": False, "count": len(entries), "tip": prev, "entries": entries}
            body = {k: v for k, v in item.items() if k != "hash"}
            if _digest(body) != item.get("hash"):
                return {"ok": False, "count": len(entries), "tip": prev, "entries": entries}
            entries.append(item)
            prev = str(item["hash"])
        return {"ok": True, "count": len(entries), "tip": prev, "entries": entries}

    def _read_state(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return {}
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_state(
        self,
        layer: str,
        *,
        garden_tip: str | None = None,
        garden_count: int | None = None,
        memorial_tip: str | None = None,
        memorial_count: int | None = None,
    ) -> None:
        prior = self._read_state()
        doc = {
            "layer": layer,
            "sidenet": SIDENET,
            "client": CLIENT,
            "spec": SPEC,
            "author": AUTHOR,
            "garden_tip": garden_tip if garden_tip is not None else prior.get("garden_tip", GENESIS_PREV),
            "garden_count": garden_count if garden_count is not None else prior.get("garden_count", 0),
            "memorial_tip": memorial_tip
            if memorial_tip is not None
            else prior.get("memorial_tip", GENESIS_PREV),
            "memorial_count": memorial_count
            if memorial_count is not None
            else prior.get("memorial_count", 0),
            "updated": _utcnow(),
        }
        self.home.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.state_path)
