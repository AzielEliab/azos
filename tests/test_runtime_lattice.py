"""Vectors computed from aziel-runtime src/dual-lattice.js.

Primary and offline/online secondary: @ 2d181b9.
Tie-break: LATTICE-TIEBREAK-1.0, aziel-runtime #327 (prev=0, primary=b*64,
secondary=offline(a*64, aziel), username aziel) -> 168b99ad…9c27.
"""

import hashlib
import json

from azos.chains import GENESIS, canon
from azos.runtime_lattice import (
    runtime_offline_secondary,
    runtime_online_secondary,
    runtime_primary,
    runtime_receipt_lattice,
    runtime_tiebreak,
    runtime_tiebreak_index_key,
    runtime_tiebreak_tip,
)

D = "a" * 64
TIEBREAK_GOLDEN = "168b99add5f1735d8efd44012c41c449e752d7d6ddd0d470d40c975b45da9c27"


def test_primary_vector():
    assert runtime_primary(D) == "342e4cf00987c1a1fa90d2fe941a77a389e4ed10b9038530ac1cc0662982ed31"


def test_offline_secondary_vector():
    assert runtime_offline_secondary(D, "aziel") == "7e1ea25d11c9c05dbb7844a69f83456fa56c7dbc67cadb913b16459e6e7a1a85"


def test_online_secondary_vector():
    assert runtime_online_secondary("b" * 64) == "54839f519abdcf74107097bc8d825e5a9667d484a9dc1f9cc2b41887cdcafc41"


def test_offline_secondary_distinct_per_user_and_stable():
    assert runtime_offline_secondary(D, "a") != runtime_offline_secondary(D, "b")
    assert runtime_offline_secondary(D, "a") == runtime_offline_secondary(D, "a")


def test_tiebreak_vector_and_key_order():
    off = runtime_offline_secondary(D, "aziel")
    assert off == "7e1ea25d11c9c05dbb7844a69f83456fa56c7dbc67cadb913b16459e6e7a1a85"
    got = runtime_tiebreak(primary="b" * 64, secondary=off, username="aziel", prev=GENESIS)
    assert got == TIEBREAK_GOLDEN
    raw = canon(
        {"chain": "tiebreak", "prev": GENESIS, "primary": "b" * 64, "secondary": off, "username": "aziel"}
    )
    assert got == hashlib.sha256(raw).hexdigest()
    ordered = canon({"username": "u", "secondary": "s", "primary": "p", "prev": GENESIS, "chain": "tiebreak"})
    assert ordered == (
        b'{"chain":"tiebreak","prev":"' + GENESIS.encode() + b'","primary":"p","secondary":"s","username":"u"}'
    )


def test_tiebreak_chains_from_previous_hash():
    off = runtime_offline_secondary(D, "aziel")
    first = runtime_tiebreak(primary="b" * 64, secondary=off, username="aziel")
    assert first == TIEBREAK_GOLDEN
    second = runtime_tiebreak(primary="c" * 64, secondary=off, username="aziel", prev=first)
    assert second != first
    assert runtime_tiebreak_index_key("aziel", D) == "aziel\0" + D
    rows = [
        {"lattice": {"primary": "p", "secondary": off}},
        {"lattice": {"tiebreak": {"status": "synced", "hash": first}}},
        {"lattice": {"tiebreak": {"status": "pending", "hash": None}}},
    ]
    assert runtime_tiebreak_tip(rows) == first


def test_receipt_without_tiebreak_keeps_its_bytes():
    primary, secondary = "a" * 64, "b" * 64
    bare = runtime_receipt_lattice(primary, secondary, {"primary": primary, "secondary": secondary})
    assert list(bare) == ["primary", "secondary"]
    assert json.dumps(bare, separators=(",", ":")) == (
        '{"primary":"' + primary + '","secondary":"' + secondary + '"}'
    )
    assert canon(bare) == canon({"secondary": secondary, "primary": primary})
    tb = {
        "status": "synced",
        "hash": TIEBREAK_GOLDEN,
        "prev": GENESIS,
        "offline_secondary": runtime_offline_secondary(D, "aziel"),
    }
    shown = runtime_receipt_lattice(primary, secondary, {"primary": primary, "secondary": secondary, "tiebreak": tb})
    assert shown["tiebreak"] == tb
    assert "tiebreak" not in bare
    assert json.dumps(bare, separators=(",", ":")) == (
        '{"primary":"' + primary + '","secondary":"' + secondary + '"}'
    )
