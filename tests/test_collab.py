"""AZBOT-NODE-COLLAB-1.0: local AZBot handoff on the AZ-OS session shell.

Receipt tips are shared. The chain is not rewritten. Public exec, vault
destructive ops, and mesh enable stay refused. Author: Aziel Eliab.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

from azos.collab import (
    CAP7_SENTENCE,
    GET_MESH_ENABLES,
    HANDOFF_ACTION,
    PUBLIC_MESH_ENABLE_INVENTED,
    REWRITES_QNM_FLAGS,
    SPEC,
    TETHER_SPEC,
    CollabSession,
    honesty,
)
from azos.errors import AppendOnlyError, AuthorizationError, AzosError
from azos.ethics import SHELL_VERBS
from azos.runtime import Runtime
from azos.runtime_lattice import runtime_offline_secondary, runtime_primary
from tests.conftest import passing_proposal

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "download-tracker"


def _open(tmp_path: Path):
    runtime = Runtime(root=tmp_path, start_lumen=False)
    token = runtime.request(passing_proposal()).token
    opened = runtime.open_session(token=token, actor="tester")
    return runtime, token, str(opened["session"])


def _handoff(session: CollabSession, token: str, **overrides):
    body = {
        "token": token,
        "slug": "azai",
        "op": "guide",
        "payload": {"q": "cite the door"},
        "definition": "Package a local AZBot handoff through FragGate.",
        "evidence": "A live ethics-gated session and an ARC token are present.",
        "impact": "In-process envelope only. No host shell and no mesh radio.",
        "actor": "tester",
    }
    body.update(overrides)
    return session.handoff(**body)


def test_constants_do_not_rewrite_qnm_or_enable_mesh() -> None:
    assert SPEC == "AZBOT-NODE-COLLAB-1.0"
    assert GET_MESH_ENABLES is False
    assert REWRITES_QNM_FLAGS is False
    assert PUBLIC_MESH_ENABLE_INVENTED is False
    facts = honesty()
    assert facts["get_mesh_enables"] is False
    assert facts["public_mesh_enable_invented"] is False
    assert facts["rewrites_qnm_flags"] is False
    assert facts["mesh_node_live"] is True
    assert facts["alt_internet_live"] is True
    assert facts["packet_path_live"] is True
    assert facts["public_bind"] is False
    assert "auto_heal" not in facts
    assert "node_gate" not in facts
    assert "anonymity_network" not in facts
    assert facts["qnm_flags_not_rewritten"] == [
        "enabled",
        "mesh_default",
        "auto_heal",
        "node_gate",
        "anonymity_network",
        "vpn",
    ]
    assert facts["cap7_is_path"] is False
    assert facts["public_icann"] is False
    assert facts["bgp"] is False
    assert facts["cap7_note"] == CAP7_SENTENCE
    assert facts["public_exec"] == "refused"
    assert facts["public_shell"] == "refused"
    assert facts["public_lattice"] == "refused"
    assert facts["vault_wipe"] == "local-only"
    assert facts["vault_public"] == "FG-STUB"
    assert facts["public_door"] == "FG-STUB"
    assert HANDOFF_ACTION not in SHELL_VERBS


def test_collab_source_does_not_fetch_or_spawn() -> None:
    path = ROOT / "azos" / "collab.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    banned = {"subprocess", "socket", "urllib", "http", "requests"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] not in banned
        elif isinstance(node, ast.ImportFrom) and node.module:
            assert node.module.split(".")[0] not in banned
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "compile"}


def test_gate_and_remain_off_package_nothing(tmp_path: Path) -> None:
    runtime, token, session_id = _open(tmp_path)
    session = CollabSession(runtime, session_id)
    before = runtime.lattice.snapshot()["gear_ticks"]
    failed = _handoff(session, token, definition="short")
    assert failed["ok"] is False
    assert failed["code"] == "GATE-FAIL"
    assert failed["envelope"] is None
    assert failed["fetched"] is False
    for slug, op, code in (
        ("azos", "exec", "PUBLIC-AZOS-REFUSED"),
        ("azos", "shell", "PUBLIC-AZOS-REFUSED"),
        ("azos", "lattice", "PUBLIC-AZOS-REFUSED"),
        ("ark", "wipe", "VAULT-LOCAL-ONLY"),
        ("ark", "scorch", "VAULT-LOCAL-ONLY"),
        ("ark", "unlock", "VAULT-LOCAL-ONLY"),
        ("azai", "deanonymize", "COLLAB-REMAIN-OFF"),
        ("azai", "invent_mark", "COLLAB-REMAIN-OFF"),
        ("azai", "backdate", "COLLAB-REMAIN-OFF"),
        ("azai", "rollback", "COLLAB-REMAIN-OFF"),
        ("mesh", "enable", "COLLAB-MESH-ENABLE-REFUSED"),
    ):
        refused = _handoff(session, token, slug=slug, op=op)
        assert refused["ok"] is False
        assert refused["code"] == code
        assert refused["envelope"] is None
        assert refused["written"] is False
    assert runtime.lattice.snapshot()["gear_ticks"] == before


def test_receipt_tips_are_shared_and_not_rewritten(tmp_path: Path) -> None:
    runtime, token, session_id = _open(tmp_path)
    session = CollabSession(runtime, session_id)
    packed = _handoff(session, token)
    assert packed["ok"] is True
    assert packed["passed"] is True
    assert packed["envelope"]["fetched"] is False
    assert packed["envelope"]["door"].endswith("/v1/fraggate/call")
    assert packed["envelope"]["slug"] == "azai"
    assert packed["envelope"]["op"] == "guide"
    assert packed["single_door"] is True
    envelope_id = packed["envelope"]["id"]
    tip = session.accept_receipt(
        token=token,
        envelope_id=envelope_id,
        receipt={"ok": True, "code": "GUIDE"},
        result={"text": "cited"},
        party="tester",
    )
    assert tip["ok"] is True
    assert tip["share"] == "receipt-tips-only"
    assert tip["rewrite"] is False
    assert tip["chainlock_tip"]["seq"] == 1
    assert tip["chainlock_tip"]["empty"] is False
    assert tip["temporal_tip"]["verified"] is True
    assert "document" not in tip
    assert "payload" not in tip
    row = session._rows[-1]
    assert row["primary"] == runtime_primary(row["document_hash"], row["prev"])
    assert row["secondary"] == runtime_offline_secondary(row["document_hash"], "tester")
    session.add_party("human-b", token=token)
    other = session.tip("human-b")
    assert other["chainlock_tip"] == tip["chainlock_tip"]
    assert other["temporal_tip"] == tip["temporal_tip"]
    try:
        session.tip("human-c")
        raise AssertionError("stranger read the tip")
    except AuthorizationError:
        pass
    try:
        session.rewrite()
        raise AssertionError("rewrite succeeded")
    except AppendOnlyError:
        pass
    try:
        session.remove_party("human-b")
        raise AssertionError("party removal succeeded")
    except AppendOnlyError:
        pass
    try:
        session.accept_receipt(
            token=token,
            envelope_id=envelope_id,
            receipt={"ok": True, "code": "GUIDE"},
            party="tester",
        )
        raise AssertionError("double receipt stored")
    except AzosError as exc:
        assert str(exc) == "COLLAB-RECEIPT-DOUBLED"
    assert session.tip("tester")["chainlock_tip"]["seq"] == 1
    assert tip["tether"] == TETHER_SPEC
    assert tip["spec"] == SPEC


def test_worker_collab_script() -> None:
    completed = subprocess.run(
        ["node", str(WORKER / "scripts" / "verify-collab.mjs")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert "ok azos collab" in completed.stdout
