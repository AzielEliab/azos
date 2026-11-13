"""Default pytest run stays on this machine.

The session fence records every non-loopback resolve or connect and fails
the run if that list is not empty. AZOS_LIVE_NETWORK=1 turns the fence off.
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

_ATTEMPTS: list[tuple[str, str]] = []
_LIVE = os.environ.get("AZOS_LIVE_NETWORK") == "1"
_LOOPBACK = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "::"}


def _host_text(host: object) -> str:
    if isinstance(host, bytes):
        return host.decode("utf-8", "replace")
    return "" if host is None else str(host)


def _loopback(host: object) -> bool:
    text = _host_text(host).strip("[]")
    if text in _LOOPBACK or text == "":
        return True
    try:
        import ipaddress

        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False


@pytest.fixture(scope="session", autouse=True)
def network_fence():
    """Fail the run when a test resolves or connects past loopback."""
    if _LIVE:
        yield []
        return
    _ATTEMPTS.clear()
    original_info = socket.getaddrinfo
    original_create = socket.create_connection
    original_connect = socket.socket.connect

    def getaddrinfo(host, port, *args, **kwargs):  # noqa: ANN001
        if not _loopback(host):
            _ATTEMPTS.append(("getaddrinfo", _host_text(host)))
            raise OSError(f"external network blocked: {_host_text(host)}")
        return original_info(host, port, *args, **kwargs)

    def create_connection(address, *args, **kwargs):  # noqa: ANN001
        host = address[0] if isinstance(address, tuple) and address else None
        if host is not None and not _loopback(host):
            _ATTEMPTS.append(("connect", _host_text(host)))
            raise OSError(f"external network blocked: {_host_text(host)}")
        return original_create(address, *args, **kwargs)

    def connect(self, address):  # noqa: ANN001
        host = address[0] if isinstance(address, tuple) and address else None
        if host is not None and not _loopback(host):
            _ATTEMPTS.append(("connect", _host_text(host)))
            raise OSError(f"external network blocked: {_host_text(host)}")
        return original_connect(self, address)

    socket.getaddrinfo = getaddrinfo
    socket.create_connection = create_connection
    socket.socket.connect = connect
    try:
        yield _ATTEMPTS
    finally:
        socket.getaddrinfo = original_info
        socket.create_connection = original_create
        socket.socket.connect = original_connect
    assert _ATTEMPTS == [], f"external network attempts: {_ATTEMPTS}"


from azos.gate import Proposal
from azos.runtime import Runtime


@pytest.fixture
def runtime(tmp_path: Path) -> Runtime:
    return Runtime(root=tmp_path)


def passing_proposal(action: str = "echo") -> Proposal:
    return Proposal(
        action=action,
        definition="Print a bounded status string from a registered builtin.",
        evidence="Action is on the closed SAFE_ACTIONS list in azos.exec.",
        impact="In-process result only. No host disk, no other machines.",
        actor="tester",
    )
