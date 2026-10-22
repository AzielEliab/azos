"""USER-SIGNIN-ARK-1.0 on-device client: parity with aziel-runtime and offline invariants."""
import json
from pathlib import Path

import pytest

pytest.importorskip("cryptography")
from azos import ark_account as ark  # noqa: E402

FX = json.loads((Path(__file__).parent / "fixtures" / "ark-account-vectors.json").read_text())


@pytest.mark.parametrize("v", FX["vectors"], ids=lambda v: v["username"])
def test_parity_vectors(v):
    a = ark.derive(v["username"], v["password"])
    assert (a.pub, a.vault_id, a.rl_subject) == (v["pub"], v["vault_id"], v["rl_subject"])


def test_deniable_wrong_password_is_other_vault():
    a = ark.derive("aziel", "correct horse battery")
    b = ark.derive("aziel", "correct horse batterz")
    assert a.vault_id != b.vault_id and a.rl_subject == b.rl_subject


def test_signature_matches_runtime_vector():
    a = ark.derive("aziel", "correct horse battery")
    body = {"spec": ark.SPEC, "vault_id": a.vault_id, "seq": 1, "prev": ark.GENESIS, "kind": "note", "ct_sha256": "832c9684f728c2278c01d63759d7d77ceb214bc87cb8a6e9e14a462cde2038dd", "ts": 1792670076587}
    assert a.sign(ark.append_message(body)) == "caaeb121443dd89018d5d802b26f04798ff01ba18fc560aff045181458700752b97ce57bbd306fcdc551310139b5fc68340cc8510afe4f673b08414bbacdf704"
    assert a.sign(ark.recall_message(a.vault_id, 1792670076587)) == "a471a363182b83967e5e96a746f686c6f7df11462aac95450d93868cd40b5d998b0d5dceb65435a4ae1a443dde09f47e30e11a78260d85e46b14411c1564f006"


def test_lattice_rules_match_runtime_vectors():
    d = "832c9684f728c2278c01d63759d7d77ceb214bc87cb8a6e9e14a462cde2038dd"
    assert ark.lattice_primary(d, None) == "a087b1ef5b2de4ebeacf839486d4e731165bdf136f1e3a647b6a3821dda2987b"
    assert ark.lattice_online_secondary("a087b1ef5b2de4ebeacf839486d4e731165bdf136f1e3a647b6a3821dda2987b", None) == "02ecec3c329b79ec3f81dcb653db16fbfcd40fe899f1f5ab25c042d3f272ccc2"
    assert ark.lattice_offline_secondary(d, "ark.5edd3cac1e7c91a0cd5ee9c8735e7ca209a245d5c092a17a6c572106b55f8dfd") == "1dce38243c8fe9d380054d9b62b1dfce167a93c81b9a8e3e0e89f8660c28b159"


def test_device_requests_carry_no_secret():
    a = ark.derive("zq7sentinel", "Pw-SENTINEL-93f1x")
    for req in (a.open_request(), a.append_request(1, ark.GENESIS, "hello", ts=1), a.recall_request(ts=1)):
        s = json.dumps(req)
        assert "zq7sentinel" not in s and "Pw-SENTINEL" not in s and "username" not in s and "password" not in s
    req = a.append_request(1, ark.GENESIS, "hello", ts=1)["payload"]
    body = {"spec": ark.SPEC, "vault_id": a.vault_id, "seq": 1, "prev": ark.GENESIS, "kind": "note", "ct_sha256": req["ct_sha256"], "ts": 1}
    assert ark.verify_sig(a.pub, req["user_sig"], ark.append_message(body))
    assert "Pw-SENTINEL" not in repr(a)


def test_offline_vault_append_only_and_private(tmp_path):
    a = ark.derive("zq7sentinel", "Pw-SENTINEL-93f1x")
    v = ark.OfflineVault(tmp_path)
    r1 = v.append(a, "first secret")
    r2 = v.append(a, "second secret")
    assert r2["prev"] == r1["row_hash"] and r1["lattice"]["offline"] is True
    assert r1["lattice"]["username"] == "ark." + a.vault_id
    assert v.recall(a) == ["first secret", "second secret"]
    assert ark.verify_rows(v.rows(a.vault_id)) is True
    disk = "".join(p.read_text() for p in tmp_path.rglob("*") if p.is_file())
    for bad in ("zq7sentinel", "Pw-SENTINEL", "first secret", "second secret"):
        assert bad not in disk
    wrong = ark.derive("zq7sentinel", "Pw-SENTINEL-93f1y")
    assert v.recall(wrong) == []  # wrong password: empty history, no error


def test_tamper_fails_closed(tmp_path):
    a = ark.derive("zq7sentinel", "Pw-SENTINEL-93f1x")
    v = ark.OfflineVault(tmp_path)
    v.append(a, "x1")
    p = next(tmp_path.rglob("*.jsonl"))
    row = json.loads(p.read_text())
    row["kind"] = "evil"
    p.write_text(json.dumps(row) + "\n")
    assert ark.verify_rows(v.rows(a.vault_id)) == "row_hash@1"
    with pytest.raises(ark.ArkError) as e:
        v.append(a, "x2")
    assert e.value.code == "ARK-FAIL-CLOSED"


@pytest.mark.parametrize("u,p", [("ab", "longenough"), ("a b", "longenough"), ("aziel", "short"), (None, "longenough")])
def test_uniform_input_refusal(u, p):
    with pytest.raises(ark.ArkError) as e:
        ark.derive(u, p)
    assert e.value.code == "ARK-INPUT"
