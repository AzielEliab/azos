"""SIDENET-P4 offline node. No network. SLOT stays SLOT."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from azos.cli import main
from azos.sidenet import (
    GENESIS_PREV,
    L0_ORIGINS,
    OfflineNode,
    SidenetRefuse,
    assert_l0_url,
)

TOKEN = "ab" * 32


class Scripted:
    def __init__(self, handler) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.handler = handler

    def exchange(self, method: str, url: str, body: dict | None = None) -> dict:
        self.calls.append((method, url, body))
        return self.handler(method, url, body)


def _items(menu: dict) -> dict:
    return {item["id"]: item for item in menu["items"]}


def test_menu_is_honest_without_a_probe(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    menu = node.menu()
    assert menu["layer"] == "stacked-os"
    assert menu["icann_tld_az"] is False
    assert menu["radio_phy"] is False
    assert menu["softwares_cards"] == []
    assert menu["neighbor_vote_to_fix"] is False
    assert menu["rewrite_key"] is False
    assert menu["lie_to_survive"] is False
    assert menu["public_hostname_resurrection"] is False
    items = _items(menu)
    assert items["local-receipts"]["status"] == "LIVE"
    assert items["l0-fraggate-https"]["status"] == "UNPROBED"
    assert items["softwares-desk"]["status"] == "FROZEN"
    assert items["softwares-desk"]["cards"] == []
    assert items["plane-b"]["status"] == "SLOT"
    assert items["plane-c"]["status"] == "SLOT"
    assert items["live-node-api"]["status"] == "SLOT"
    assert items["doi"]["status"] == "SLOT"
    assert items["doi"]["doi"] is None
    assert items["radio-phy"]["status"] == "ABSENT"
    assert items["qnm-node"]["status"] == "CITE"
    assert items["qnm-node"]["paired"] is False
    assert items["cap7-factory-cite"]["status"] == "LIVE"
    assert items["cap7-factory-cite"]["internet_reachable"] is False
    assert items["cap7-factory-cite"]["icann_tld_az"] is False
    assert items["cap7-factory-cite"]["is_live_door"] is False
    assert items["phoenix"]["public_hostname_resurrection"] is False


def test_seal_chains_and_reload_keeps_the_tip(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    first = node.seal(token_hash=TOKEN)
    second = node.seal(token_hash=TOKEN)
    assert first["prev"] == GENESIS_PREV
    assert second["prev"] == first["hash"]
    assert "body" not in first
    again = OfflineNode(tmp_path)
    assert again.tip == second["hash"]
    assert again.status()["receipts"] == 2
    assert again.status()["posture"] == "offline"


def test_phoenix_waits_without_changing_the_tip(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    sealed = node.seal(token_hash=TOKEN)
    waiting = node.phoenix(token_hash=TOKEN)
    assert waiting["phoenix_wait"] is True
    assert waiting["tip"] == sealed["hash"]
    assert waiting["receipts"] == 1
    with pytest.raises(SidenetRefuse) as refused:
        node.seal(token_hash=TOKEN)
    assert refused.value.code == "SIDENET-PHOENIX-WAIT"
    resealed = node.reseal(token_hash=TOKEN)
    assert resealed["action"] == "reseal"
    assert resealed["prev"] == sealed["hash"]
    assert node.status()["phoenix_wait"] is False


def test_reseal_without_wait_is_refused(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    node.seal(token_hash=TOKEN)
    with pytest.raises(SidenetRefuse) as refused:
        node.reseal(token_hash=TOKEN)
    assert refused.value.code == "SIDENET-NO-RESEAL"


def test_reheal_refuses_neighbor_vote(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    sealed = node.seal(token_hash=TOKEN)
    with pytest.raises(SidenetRefuse) as refused:
        node.reheal(vote=True, neighbor_tip="cd" * 32)
    assert refused.value.code == "SIDENET-NO-VOTE"
    assert node.tip == sealed["hash"]
    own = node.reheal(token_hash=TOKEN)
    assert own["changed"] is False
    assert own["cure"] == "own-tip"


def test_equivocation_isolates_and_does_not_adopt(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    sealed = node.seal(token_hash=TOKEN)
    foreign = "cd" * 32
    observed = node.observe_foreign(GENESIS_PREV, foreign)
    assert observed["code"] == "SIDENET-EQUIVOCATION"
    assert observed["adopted"] is False
    text = node.receipts_path.read_text(encoding="utf-8")
    assert foreign not in text
    assert node.status()["posture"] == "isolated"
    assert node.status()["phoenix_wait"] is True
    assert sealed["hash"] in text


def test_foreign_extension_is_refused(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    sealed = node.seal(token_hash=TOKEN)
    with pytest.raises(SidenetRefuse) as refused:
        node.observe_foreign(sealed["hash"], "ef" * 32)
    assert refused.value.code == "SIDENET-NO-FOREIGN-TIP"
    assert node.tip == sealed["hash"]


def test_tamper_refuses_splice(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    node.seal(token_hash=TOKEN)
    with node.receipts_path.open("a", encoding="utf-8") as handle:
        handle.write("{not-json}\n")
    again = OfflineNode(tmp_path)
    assert again.status()["tampered"] is True
    with pytest.raises(SidenetRefuse) as refused:
        again.seal(token_hash=TOKEN)
    assert refused.value.code == "SIDENET-TAMPER"


def test_corrupt_state_is_not_rewritten(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    raw = b"{"
    node.state_path.write_bytes(raw)
    again = OfflineNode(tmp_path)
    assert again.state_path.read_bytes() == raw
    with pytest.raises(SidenetRefuse) as refused:
        again.seal(token_hash=TOKEN)
    assert refused.value.code == "SIDENET-TAMPER"
    assert again.state_path.read_bytes() == raw


def test_rewrite_and_hostname_resurrection_refused(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    with pytest.raises(SidenetRefuse) as rewrite:
        node.rewrite()
    assert rewrite.value.code == "SIDENET-NO-REWRITE"
    with pytest.raises(SidenetRefuse) as restore:
        node.restore_public_hostname()
    assert restore.value.code == "SIDENET-NO-RESURRECTION"


def test_l0_urls_stay_on_published_fronts() -> None:
    assert assert_l0_url(L0_ORIGINS[0] + "/v1/health")
    with pytest.raises(SidenetRefuse):
        assert_l0_url("http://aziel-runtime.vibelock.workers.dev/v1/health")
    with pytest.raises(SidenetRefuse):
        assert_l0_url("https://evil.example/v1/health")
    with pytest.raises(SidenetRefuse):
        assert_l0_url(L0_ORIGINS[0] + "/v1/software")
    with pytest.raises(SidenetRefuse):
        assert_l0_url("https://azgrid.az/v1/health")


def test_rejoin_success_freezes_the_desk(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    node.seal(token_hash=TOKEN)

    def handler(method: str, url: str, body: dict | None) -> dict:
        if url.endswith("/v1/health"):
            return {"status": 200, "json": {"ok": True}, "error": None}
        if url.endswith("/v1/mesh/join"):
            assert body is not None
            assert body["kind"] == "instance"
            assert body["product"] == "azos"
            assert "body" not in body
            return {"status": 200, "json": {"ok": True, "node_id": body["node_id"]}, "error": None}
        assert url.endswith("/v1/mesh/heartbeat")
        assert body is not None
        assert set(body) == {"node_id", "presence", "tip_hash", "prev"}
        return {"status": 200, "json": {"ok": True, "node_id": body["node_id"]}, "error": None}

    scripted = Scripted(handler)
    node.transport = scripted
    result = node.rejoin(token_hash=TOKEN)
    assert result["ok"] is True
    assert result["joined"] is True
    assert result["tip"] == node.tip
    assert result["softwares_cards"] == []
    assert result["softwares_desk"] == "frozen"
    actions = [json.loads(line)["action"] for line in node.receipts_path.read_text().splitlines()]
    assert actions == ["seal"]
    assert _items(node.menu())["l0-fraggate-https"]["status"] == "LIVE"
    assert _items(node.menu())["softwares-desk"]["status"] == "FROZEN"
    assert _items(node.menu())["plane-b"]["status"] == "SLOT"
    urls = [url for _method, url, _body in scripted.calls]
    assert all(url.startswith(L0_ORIGINS[0]) for url in urls)
    assert not any("/v1/software" in url for url in urls)
    assert len(urls) == 3


def test_rejoin_unreachable_keeps_the_tip(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    sealed = node.seal(token_hash=TOKEN)

    def handler(method: str, url: str, body: dict | None) -> dict:
        return {"status": 0, "json": None, "error": "offline"}

    node.transport = Scripted(handler)
    result = node.rejoin(token_hash=TOKEN)
    assert result["ok"] is False
    assert result["joined"] is False
    assert result["reachable"] is False
    assert node.tip == sealed["hash"]
    actions = [json.loads(line)["action"] for line in node.receipts_path.read_text().splitlines()]
    assert actions == ["seal"]
    assert _items(node.menu())["l0-fraggate-https"]["status"] == "UNREACHABLE"
    assert _items(node.menu())["plane-b"]["status"] == "SLOT"


def test_rejoin_mesh_off_is_not_a_join(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    tip = node.seal(token_hash=TOKEN)["hash"]

    def handler(method: str, url: str, body: dict | None) -> dict:
        if url.endswith("/v1/health"):
            return {"status": 200, "json": {"ok": True}, "error": None}
        return {"status": 200, "json": {"ok": False, "code": "MESH-OFF"}, "error": None}

    node.transport = Scripted(handler)
    result = node.rejoin(token_hash=TOKEN)
    assert result["reachable"] is True
    assert result["joined"] is False
    assert result["code"] == "MESH-OFF"
    assert node.tip == tip
    assert _items(node.menu())["l0-fraggate-https"]["status"] == "LIVE"
    assert _items(node.menu())["softwares-desk"]["cards"] == []


def test_phoenix_does_not_call_l0(tmp_path: Path) -> None:
    node = OfflineNode(tmp_path)
    node.seal(token_hash=TOKEN)

    def handler(method: str, url: str, body: dict | None) -> dict:
        raise AssertionError("phoenix must not call L0")

    node.transport = Scripted(handler)
    node.phoenix(token_hash=TOKEN)
    with pytest.raises(SidenetRefuse) as refused:
        node.rejoin(token_hash=TOKEN)
    assert refused.value.code == "SIDENET-PHOENIX-WAIT"


def test_cli_menu_and_seal(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["node", "menu", "--json"]) == 0
    menu = json.loads(capsys.readouterr().out)
    assert menu["items"]
    assert main(["node", "seal", "--json"]) == 0
    sealed = json.loads(capsys.readouterr().out)
    assert sealed["action"] == "seal"
    assert main(["node"]) == 0
    text = capsys.readouterr().out
    assert "SIDENET-P4" in text
    assert "frozen" in text


def test_cli_halt_refuses_seal(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    assert main(["halt"]) == 0
    capsys.readouterr()
    assert main(["node", "seal"]) == 1
    err = capsys.readouterr().err
    assert "halted" in err.lower()
