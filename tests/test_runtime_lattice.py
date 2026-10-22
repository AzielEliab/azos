"""Vectors computed from aziel-runtime src/dual-lattice.js @ 2d181b9."""

from azos.runtime_lattice import runtime_offline_secondary, runtime_online_secondary, runtime_primary

D = "a" * 64


def test_primary_vector():
    assert runtime_primary(D) == "342e4cf00987c1a1fa90d2fe941a77a389e4ed10b9038530ac1cc0662982ed31"


def test_offline_secondary_vector():
    assert runtime_offline_secondary(D, "aziel") == "7e1ea25d11c9c05dbb7844a69f83456fa56c7dbc67cadb913b16459e6e7a1a85"


def test_online_secondary_vector():
    assert runtime_online_secondary("b" * 64) == "54839f519abdcf74107097bc8d825e5a9667d484a9dc1f9cc2b41887cdcafc41"


def test_offline_secondary_distinct_per_user_and_stable():
    assert runtime_offline_secondary(D, "a") != runtime_offline_secondary(D, "b")
    assert runtime_offline_secondary(D, "a") == runtime_offline_secondary(D, "a")
