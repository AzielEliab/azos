"""AZOS-NEWS-COPY-1.0 CLI side: sync checks every row; serve works offline; standalone only when verified."""

from __future__ import annotations

import json

from azos.news_copy import GENESIS, _h, _js_number, canonicalize, check_row, serve, sync


def test_js_number_forms():
    cases = {1e-7: "1e-7", 0.00005: "0.00005", 1e21: "1e+21", 123.0: "123", 25.2854: "25.2854", -0.5: "-0.5", 1.5e300: "1.5e+300", 0.1: "0.1", 100: "100"}
    for value, want in cases.items():
        assert _js_number(value) == want, value
    assert canonicalize({"b": 1, "a": [True, None, "é\n"]}) == '{"a":[true,null,"é\\n"],"b":1}'


def _ledger(n=12):
    rows, tip = [], {"primary": GENESIS, "secondary": GENESIS}
    for i in range(n):
        offline = i == n - 1
        kind = ["news", "pin", "pin", "pull_receipt", "sky"][i % 5] if not offline else "view_receipt"
        doc = {"item_id": f"n-{i}", "title": f"Fire “{i}”", "outlet": {"name": "X"}, "score": 0.25 + i, "tiny": 0.00005, "event": "e", "pin_type": "news-report", "geo": {"lat": 6.45, "lon": 3.39}}
        dh = _h(doc)
        primary = _h({"document": dh, "prev": tip["primary"]})
        user = "vh-" + "a" * 32
        secondary = _h({"primary": dh, "username": user}) if offline else _h({"offline": False, "prev": tip["secondary"], "primary": primary})
        lat = {"document_hash": dh, "primary": primary, "primary_prev": tip["primary"], "secondary": secondary, "secondary_prev": tip["secondary"], "offline": offline, "username": user if offline else None}
        rows.append({"seq": i + 1, "kind": kind, "at": "2026-10-09T06:00:00Z", "doc": doc, "lattice": lat})
        tip = {"primary": primary, "secondary": secondary}
    return rows, tip


def _fetcher(rows, tip, from_genesis=True):
    def fetch(url, limit=0, timeout=0):
        after = int(url.split("after=")[1].split("&")[0])
        page = rows[after : after + 5]
        return 200, json.dumps({"ok": True, "tip_seq": len(rows), "tips": tip, "from_genesis": from_genesis, "rows": page}).encode()
    return fetch


def test_sync_then_serve_offline(tmp_path):
    rows, tip = _ledger()
    assert serve("feed", tmp_path)["standalone"] is False
    out = sync(tmp_path, fetch=_fetcher(rows, tip))
    assert out["ok"] and out["tip_seq"] == len(rows) and out["tips_match_tracker"] is True
    # Offline: no fetch at all.
    got = serve("status", tmp_path)
    assert got["standalone"] is True and got["live"] is False and got["copy_verify"]["ok"] is True
    assert got["items"] and got["pins"] and got["sky"]
    # Again: nothing new.
    assert sync(tmp_path, fetch=_fetcher(rows, tip))["rows_added"] == 0


def test_tampered_copy_is_not_standalone(tmp_path):
    rows, tip = _ledger()
    sync(tmp_path, fetch=_fetcher(rows, tip))
    p = tmp_path / ".azos" / "aznews-copy" / "rows.jsonl"
    lines = p.read_text("utf-8").splitlines()
    first = json.loads(lines[0])
    first["doc"]["title"] = "changed"
    lines[0] = json.dumps(first, ensure_ascii=False)
    p.write_text("\n".join(lines) + "\n", "utf-8")
    got = serve("feed", tmp_path)
    assert got["standalone"] is False and "document hash" in got["copy_verify"]["reason"]


def test_sync_refuses_bad_rows(tmp_path):
    rows, tip = _ledger()
    bad = json.loads(json.dumps(rows))
    bad[3]["lattice"]["primary_prev"] = "f" * 64
    out = sync(tmp_path, fetch=_fetcher(bad, tip))
    assert out["ok"] is False and out["code"] == "NEWS-COPY-SYNC-HASH" and out["at_seq"] == 4
    assert sync(tmp_path / "x", fetch=_fetcher(rows, tip, from_genesis=False))["code"] == "NEWS-COPY-SYNC-NOT-GENESIS"
    assert check_row(rows[0], {"primary": GENESIS, "secondary": GENESIS}) is None
