"""Carrier path on the existing internet door.

Order is LAN, then Wi-Fi, then Bluetooth, then RF, then photon.
A flag stays false unless a packet leaves this machine and the reply
comes back from a different machine id. A same-machine frame, a guest
log line, a mock, and the names Cap-7 and .aziel do not make it live.

Author: Aziel Eliab.
"""

from __future__ import annotations

import copy
import hashlib
import os
import selectors
import socket
import threading
import zlib
from pathlib import Path
from typing import Any, Mapping

CARRIER_ORDER: tuple[str, ...] = ("lan", "wifi", "bluetooth", "rf", "photon")
CARRIER_NAMES: dict[str, str] = {
    "lan": "LAN",
    "wifi": "Wi-Fi",
    "bluetooth": "Bluetooth",
    "rf": "RF",
    "photon": "photon",
}

HEAD = (
    "An alternative internet is not live (alt_internet_live is false). "
    "A packet path is not live (packet_path_live is false)."
)
TAIL = " ".join(
    (
        "Still missing: a packet that leaves this machine and arrives on a different machine id.",
        "A same-machine mesh frame does not count.",
        "Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP.",
        "WireGuard, OpenVPN, an L3 exit pool, kernel UDP, and TUN/TAP stay SLOT.",
        "Public mail send, the kernel, and boot stay not live.",
        "The public door stays FG-STUB.",
        "Isolation is single-node security-awareness.",
        "Phoenix is a local wait and re-seal.",
        "That is not a loopback fence.",
    )
)
ISOLATE_CLAUSE = "This isolate cannot see host hardware (worker_hardware is false)."
ISOLATE_SENTENCE = f"{HEAD} {ISOLATE_CLAUSE} {TAIL}"

RADIO_ABSENT = "QNM-RADIO-ABSENT"
PACKET_CARRIED = "PACKET-CARRIED"
PACKET_NOT_CARRIED = "PACKET-NOT-CARRIED"
HOST_ABSENT = "MESH-HOST-ABSENT"

_CACHE: dict[str, Any] | None = None
_CACHE_LOCK = threading.Lock()


def guest_log_is_boot(log: str) -> bool:
    """A guest log line does not boot the host."""
    del log
    return False


def guest_log_is_path(log: str) -> bool:
    """A guest log line is not a live public path."""
    del log
    return False


def second_device(local_host: str | None, remote_host: str | None) -> bool:
    """Two ends are a second device only when their machine ids differ."""
    return bool(local_host and remote_host and local_host != remote_host)


def foreign_arrival(
    *,
    bytes_match: bool,
    local_host: str | None,
    remote_host: str | None,
    source_ip: str | None,
    local_addrs: set[str],
    mock: bool,
) -> bool:
    """True only when the reply address is not an address of this machine."""
    if mock or not bytes_match:
        return False
    if not source_ip or source_ip in local_addrs:
        return False
    return second_device(local_host, remote_host)


def machine_id() -> str | None:
    try:
        text = Path("/etc/machine-id").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if len(text) == 32 and all(ch in "0123456789abcdef" for ch in text):
        return text
    return None


def _crc(body: bytes) -> bytes:
    return zlib.crc32(body).to_bytes(4, "big")


def _frame(body: bytes) -> bytes:
    return body + _crc(body)


def _crc_ok(frame: bytes) -> bool:
    if len(frame) < 5:
        return False
    return frame[-4:] == _crc(frame[:-4])


def _pad(text: str, size: int) -> bytes:
    raw = text.encode("utf-8")[:size]
    return raw + bytes(size - len(raw))


def _text(raw: bytes) -> str:
    return raw.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def encode_mesh(src: str, dst: str, host: str, payload: bytes) -> bytes:
    raw = bytearray(74 + len(payload))
    raw[0:7] = b"AZMESH1"
    raw[7] = 1
    raw[8:24] = _pad(src, 16)
    raw[24:40] = _pad(dst, 16)
    raw[40:72] = _pad(host, 32)
    raw[72] = (len(payload) >> 8) & 0xFF
    raw[73] = len(payload) & 0xFF
    raw[74:] = payload
    return _frame(bytes(raw))


def parse_mesh(frame: bytes) -> dict[str, Any] | None:
    if len(frame) < 78 or not _crc_ok(frame) or frame[0:7] != b"AZMESH1" or frame[7] != 1:
        return None
    length = (frame[72] << 8) | frame[73]
    if 74 + length + 4 != len(frame):
        return None
    return {
        "src": _text(frame[8:24]),
        "dst": _text(frame[24:40]),
        "host": _text(frame[40:72]),
        "payload": frame[74:74 + length],
        "packet_live": False,
        "mock": False,
    }


def encode_wifi(payload: bytes) -> bytes:
    header = bytearray(24)
    header[0] = 0x08
    header[4:10] = bytes((0x02, 0x00, 0x00, 0x00, 0x00, 0x01))
    header[10:16] = bytes((0x02, 0x00, 0x00, 0x00, 0x00, 0x02))
    header[16:22] = bytes((0x02, 0x00, 0x00, 0x00, 0x00, 0x03))
    return _frame(bytes(header) + payload)


def parse_wifi(frame: bytes) -> dict[str, Any] | None:
    if len(frame) < 28 or not _crc_ok(frame) or frame[0] != 0x08:
        return None
    return {"payload": frame[24:-4], "packet_live": False, "mock": False}


def encode_bluetooth(payload: bytes) -> bytes:
    raw = bytearray(8 + len(payload))
    raw[0] = 0x02
    size = len(payload) + 4
    raw[2] = size & 0xFF
    raw[3] = (size >> 8) & 0xFF
    raw[4] = len(payload) & 0xFF
    raw[5] = (len(payload) >> 8) & 0xFF
    raw[6] = 0x40
    raw[8:] = payload
    return _frame(bytes(raw))


def parse_bluetooth(frame: bytes) -> dict[str, Any] | None:
    if len(frame) < 12 or not _crc_ok(frame) or frame[0] != 0x02:
        return None
    return {"payload": frame[8:-4], "packet_live": False, "mock": False}


def encode_rf(payload: bytes) -> bytes:
    raw = bytearray(5 + len(payload))
    raw[0] = 0xAA
    raw[1] = 0xD2
    raw[2] = 1
    raw[3] = len(payload) & 0xFF
    raw[4] = (len(payload) >> 8) & 0xFF
    raw[5:] = payload
    return _frame(bytes(raw))


def parse_rf(frame: bytes) -> dict[str, Any] | None:
    if len(frame) < 9 or not _crc_ok(frame) or frame[0] != 0xAA or frame[1] != 0xD2:
        return None
    return {"payload": frame[5:-4], "packet_live": False, "mock": False}


def encode_photon(payload: bytes) -> bytes:
    magic = b"AZPHOT1"
    raw = bytearray(len(magic) + 2 + len(payload))
    raw[0:len(magic)] = magic
    raw[len(magic)] = len(payload) & 0xFF
    raw[len(magic) + 1] = (len(payload) >> 8) & 0xFF
    raw[len(magic) + 2:] = payload
    return _frame(bytes(raw))


def parse_photon(frame: bytes) -> dict[str, Any] | None:
    magic = b"AZPHOT1"
    if len(frame) < len(magic) + 6 or not _crc_ok(frame) or frame[0:len(magic)] != magic:
        return None
    return {"payload": frame[len(magic) + 2:-4], "packet_live": False, "mock": False}


FRAME_CODEC = {
    "wifi": (encode_wifi, parse_wifi),
    "bluetooth": (encode_bluetooth, parse_bluetooth),
    "rf": (encode_rf, parse_rf),
    "photon": (encode_photon, parse_photon),
}


def frame_checks(kind: str) -> bool:
    codec = FRAME_CODEC.get(kind)
    if codec is None:
        return False
    payload = bytes((1, 2, 3, 4))
    parsed = codec[1](codec[0](payload))
    return bool(parsed and parsed["payload"] == payload and parsed["packet_live"] is False)


def _dir_filled(path: Path) -> bool:
    try:
        if not path.is_dir():
            return False
        return any(name not in {".", ".."} for name in os.listdir(path))
    except OSError:
        return False


def _ipv4(name: str) -> str | None:
    try:
        import fcntl
        import struct
    except ImportError:
        return None
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        res = fcntl.ioctl(sock.fileno(), 0x8915, struct.pack("256s", name.encode()[:15]))
    except OSError:
        return None
    finally:
        sock.close()
    address = socket.inet_ntoa(res[20:24])
    if address.startswith("127."):
        return None
    return address


def _wireless(name: str) -> bool:
    return (Path("/sys/class/net") / name / "wireless").exists()


def _wwan(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith(("wwan", "rmnet")) or "cdc-wdm" in lowered


def _lan_rank(name: str) -> tuple[int, str]:
    if name.startswith(("en", "eth")):
        return (0, name)
    if name.startswith(("docker", "br-", "veth", "virbr")):
        return (2, name)
    return (1, name)


def lan_interfaces() -> list[dict[str, str]]:
    root = Path("/sys/class/net")
    found: list[dict[str, str]] = []
    try:
        names = list(os.listdir(root))
    except OSError:
        return found
    for name in names:
        if not name or name == "lo" or _wireless(name) or _wwan(name):
            continue
        address = _ipv4(name)
        if address:
            found.append({"name": name, "address": address})
    found.sort(key=lambda row: _lan_rank(row["name"]))
    return found


def local_addrs() -> set[str]:
    addrs = {"127.0.0.1"}
    for row in lan_interfaces():
        addrs.add(row["address"])
    try:
        names = os.listdir("/sys/class/net")
    except OSError:
        return addrs
    for name in names:
        address = _ipv4(name)
        if address:
            addrs.add(address)
    return addrs


def hardware_seen() -> dict[str, bool]:
    leds = Path("/sys/class/leds")
    photon = Path("/dev/video0").exists()
    if not photon and leds.is_dir():
        try:
            photon = any("flash" in name.lower() or "torch" in name.lower() for name in os.listdir(leds))
        except OSError:
            photon = False
    wifi = _dir_filled(Path("/sys/class/ieee80211"))
    if not wifi:
        net = Path("/sys/class/net")
        try:
            wifi = any(_wireless(name) for name in os.listdir(net))
        except OSError:
            wifi = False
    rf = (
        _dir_filled(Path("/sys/class/sdr"))
        or _dir_filled(Path("/sys/class/wwan"))
        or _dir_filled(Path("/sys/bus/usb/drivers/dvb_usb_rtl28xxu"))
        or Path("/dev/swradio0").exists()
        or Path("/dev/cdc-wdm0").exists()
    )
    return {
        "lan": bool(lan_interfaces()),
        "wifi": wifi,
        "bluetooth": _dir_filled(Path("/sys/class/bluetooth")),
        "rf": rf,
        "photon": photon,
    }


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def exchange_mesh(address: str, host: str | None = None) -> dict[str, Any]:
    """Send one mesh frame to address and wait for the reply on that same bind."""
    local = host if host is not None else machine_id()
    if not local:
        return {
            "ok": False,
            "code": HOST_ABSENT,
            "bytes_match": False,
            "packet_live": False,
            "mock": False,
            "second_device": False,
            "foreign_arrival": False,
        }
    payload = os.urandom(16)
    request = encode_mesh("az-node-a", "az-node-b", local, payload)
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    selector: selectors.BaseSelector | None = None
    try:
        server.bind((address, 0))
        client.bind((address, 0))
        server.setblocking(False)
        client.setblocking(False)
        port = server.getsockname()[1]
        selector = selectors.DefaultSelector()
        selector.register(server, selectors.EVENT_READ)
        client.sendto(request, (address, port))
        events = selector.select(1.5)
        if not events:
            return _not_carried(local)
        message, rinfo = server.recvfrom(4096)
        remote = parse_mesh(message)
        if remote is None or remote["dst"] != "az-node-b" or remote["src"] != "az-node-a":
            return _not_carried(local)
        reply_host = local
        reply = encode_mesh("az-node-b", "az-node-a", reply_host, remote["payload"])
        selector.unregister(server)
        selector.register(client, selectors.EVENT_READ)
        server.sendto(reply, rinfo)
        back_events = selector.select(1.5)
        if not back_events:
            return _not_carried(local)
        reply_bytes, reply_from = client.recvfrom(4096)
        parsed = parse_mesh(reply_bytes)
        sent = _sha(payload)
        received = _sha(parsed["payload"]) if parsed else None
        match = bool(
            parsed
            and parsed["src"] == "az-node-b"
            and parsed["dst"] == "az-node-a"
            and received == sent
            and len(parsed["payload"]) == len(payload)
        )
        source_ip = reply_from[0]
        distinct = second_device(local, parsed["host"] if parsed else None)
        arrived = foreign_arrival(
            bytes_match=match,
            local_host=local,
            remote_host=parsed["host"] if parsed else None,
            source_ip=source_ip,
            local_addrs=local_addrs(),
            mock=False,
        )
        return {
            "ok": match,
            "code": PACKET_CARRIED if match else PACKET_NOT_CARRIED,
            "address": address,
            "source_ip": source_ip,
            "bytes": len(payload),
            "bytes_match": match,
            "sent_sha256": sent,
            "received_sha256": received,
            "sent_frame_sha256": _sha(request),
            "received_frame_sha256": _sha(reply_bytes) if parsed else None,
            "frame_magic": "AZMESH1",
            "src_node": "az-node-a",
            "dst_node": "az-node-b",
            "local_host": local,
            "remote_host": parsed["host"] if parsed else None,
            "second_device": bool(match and distinct and arrived),
            "foreign_arrival": arrived,
            "packet_live": False,
            "mock": False,
            "public_icann": False,
            "bgp": False,
        }
    except OSError:
        return _not_carried(local)
    finally:
        if selector is not None:
            selector.close()
        server.close()
        client.close()


def _not_carried(local: str | None) -> dict[str, Any]:
    return {
        "ok": False,
        "code": PACKET_NOT_CARRIED,
        "bytes_match": False,
        "packet_live": False,
        "mock": False,
        "local_host": local,
        "remote_host": None,
        "second_device": False,
        "foreign_arrival": False,
        "public_icann": False,
        "bgp": False,
    }


def _carrier_row(kind: str, present: bool, *, code: str | None = None, frame_ok: bool = False) -> dict[str, Any]:
    return {
        "id": kind,
        "name": CARRIER_NAMES[kind],
        "order": CARRIER_ORDER.index(kind) + 1,
        "state": "HW-PRESENT" if present else "REFUSE",
        "code": code,
        "packet_live": False,
        "mock": False,
        "frame_ok": frame_ok,
    }


def host_hardware_visible() -> bool:
    """Host sysfs is visible. A worker isolate does not have this directory."""
    return Path("/sys/class/net").is_dir()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def iface_up(name: str) -> bool:
    net = Path("/sys/class/net")
    if _read_text(net / name / "operstate") != "up":
        return False
    carrier = net / name / "carrier"
    if not carrier.exists():
        return True
    return _read_text(carrier) in {"1", ""}


def default_route_iface() -> str | None:
    """Default route with a gateway, else any default route. Loopback is not LAN."""
    try:
        lines = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    fallback: str | None = None
    for line in lines[1:]:
        cols = line.split()
        if len(cols) < 4:
            continue
        try:
            flags = int(cols[3], 16)
        except ValueError:
            continue
        if (flags & 1) == 0 or cols[1] != "00000000":
            continue
        name = cols[0]
        if not name or name == "lo":
            continue
        if len(cols) > 2 and cols[2] and cols[2] != "00000000":
            return name
        if fallback is None:
            fallback = name
    return fallback


def probe_lan() -> dict[str, Any]:
    """Prefer the up default-route interface. A down bridge is not the LAN path."""
    net = Path("/sys/class/net")
    try:
        if not net.is_dir():
            return {"present": False, "kind": None, "address": None, "up": False}
        names = [name for name in os.listdir(net) if name and name not in {"lo", ".", ".."}]
        preferred = default_route_iface()
        if preferred and preferred != "lo" and preferred in names and iface_up(preferred):
            address = _ipv4(preferred)
            if address:
                return {"present": True, "kind": preferred, "address": address, "up": True}
        for name in names:
            if not iface_up(name):
                continue
            address = _ipv4(name)
            if address:
                return {"present": True, "kind": name, "address": address, "up": True}
        if names:
            name = names[0]
            return {"present": True, "kind": name, "address": _ipv4(name), "up": False}
    except OSError:
        pass
    return {"present": False, "kind": None, "address": None, "up": False}


def probe_wifi() -> dict[str, Any]:
    if _dir_filled(Path("/sys/class/ieee80211")):
        return {"present": True, "kind": "ieee80211"}
    try:
        if any(_wireless(name) for name in os.listdir("/sys/class/net")):
            return {"present": True, "kind": "ieee80211"}
    except OSError:
        pass
    return {"present": False, "kind": None}


def probe_bluetooth() -> dict[str, Any]:
    if _dir_filled(Path("/sys/class/bluetooth")):
        return {"present": True, "kind": "bluetooth"}
    return {"present": False, "kind": None}


def probe_rf_hw() -> dict[str, Any]:
    if (
        Path("/dev/swradio0").exists()
        or _dir_filled(Path("/sys/class/sdr"))
        or _dir_filled(Path("/sys/bus/usb/drivers/dvb_usb_rtl28xxu"))
    ):
        return {"present": True, "kind": "sdr"}
    return {"present": False, "kind": None}


def probe_modem() -> dict[str, Any]:
    if _dir_filled(Path("/sys/class/wwan")) or Path("/dev/cdc-wdm0").exists():
        return {"present": True, "kind": "modem"}
    try:
        if not Path("/sys/class/net").is_dir():
            return {"present": False, "kind": None}
        for name in os.listdir("/sys/class/net"):
            if _wwan(name):
                return {"present": True, "kind": name}
    except OSError:
        pass
    return {"present": False, "kind": None}


def probe_flash_camera() -> dict[str, Any]:
    """Photon is a camera or a flash. Local qnsd is not this probe."""
    if Path("/dev/video0").exists():
        return {"present": True, "kind": "camera"}
    leds = Path("/sys/class/leds")
    try:
        if not leds.is_dir():
            return {"present": False, "kind": None}
        for name in os.listdir(leds):
            if "flash" in name.lower() or "torch" in name.lower():
                return {"present": True, "kind": name}
    except OSError:
        pass
    return {"present": False, "kind": None}


def track2_carrier_probe() -> dict[str, Any]:
    """Hardware presence is not a live packet hop. Absence is QNM-RADIO-ABSENT."""
    rf_hw = probe_rf_hw()
    rf = rf_hw if rf_hw["present"] else probe_modem()
    rows = (
        ("lan", probe_lan()),
        ("wifi", probe_wifi()),
        ("bluetooth", probe_bluetooth()),
        ("rf", rf),
        ("photon", probe_flash_camera()),
    )
    carriers: dict[str, dict[str, Any]] = {}
    for cid, probe in rows:
        down = probe["present"] is True and probe.get("up") is False
        if probe["present"] and not down:
            carriers[cid] = {
                "id": cid,
                "state": "HW-PRESENT",
                "hardware": probe["kind"],
                "address": probe.get("address") or None,
                "up": True,
                "code": None,
                "packet_live": False,
                "mock": False,
            }
        elif down:
            carriers[cid] = {
                "id": cid,
                "state": "REFUSE",
                "hardware": probe["kind"],
                "address": probe.get("address") or None,
                "up": False,
                "code": RADIO_ABSENT,
                "packet_live": False,
                "mock": False,
            }
        else:
            carriers[cid] = {
                "id": cid,
                "state": "REFUSE",
                "hardware": False,
                "address": None,
                "up": False,
                "code": RADIO_ABSENT,
                "packet_live": False,
                "mock": False,
            }
    return {
        "order": list(CARRIER_ORDER),
        "carriers": carriers,
        "packet_live": False,
        "alt_internet_live": False,
        "mock": False,
    }


def _carrier_clause(cid: str, row: Mapping[str, Any] | None) -> str:
    code = (row or {}).get("code") or RADIO_ABSENT
    if not row or row.get("state") == "REFUSE":
        if cid == "lan" and row and row.get("up") is False and row.get("hardware"):
            return f"LAN interface {row.get('hardware')} is down ({code})."
        if cid == "lan":
            return f"LAN hardware is absent ({code})."
        if cid == "wifi":
            return f"Wi-Fi hardware is absent ({code})."
        if cid == "bluetooth":
            return f"Bluetooth hardware is absent ({code})."
        if cid == "rf":
            return f"RF hardware is absent ({code})."
        return f"Photon camera or flash is absent ({code})."
    if cid == "lan":
        where = f" at {row['address']}" if row.get("address") else ""
        name = row.get("hardware") or "unnamed"
        return f"LAN interface {name}{where} is present on this machine and is not a second device."
    hardware = f" {row['hardware']}" if row.get("hardware") else ""
    if cid == "wifi":
        return f"Wi-Fi hardware{hardware} is present on this machine and is not a second device."
    if cid == "bluetooth":
        return f"Bluetooth hardware{hardware} is present on this machine and is not a second device."
    if cid == "rf":
        return f"RF hardware{hardware} is present on this machine and is not a second device."
    return f"Photon camera or flash hardware{hardware} is present on this machine and is not a second device."


def _machine_clause(machine: str | None) -> str:
    if machine:
        return (
            f"This machine id is {machine}. "
            "A second device stays false while both ends share that id."
        )
    return (
        "This machine id is absent (MESH-HOST-ABSENT). "
        "A second device stays false without two different ids."
    )


def _fact(
    sentence: str,
    *,
    visible: bool,
    machine: str | None,
    missing: list[str],
) -> dict[str, Any]:
    return {
        "alt_internet_live": False,
        "packet_path_live": False,
        "second_device": False,
        "machine_id": machine,
        "missing": missing,
        "not_live_sentence": sentence,
        "missing_line": sentence,
        "path_slots": {
            "wireguard": "SLOT",
            "openvpn": "SLOT",
            "l3": "SLOT",
            "kernel_udp": "SLOT",
            "tun_tap": "SLOT",
        },
        "public_door": "FG-STUB",
        "public_mail_send_live": False,
        "kernel_live": False,
        "boot_live": False,
        "cap7_name_only": True,
        "public_icann": False,
        "bgp": False,
        "worker_hardware": False,
        "host_hardware_visible": visible,
        "mock": False,
        "internet_base": {"live": False, "installed": False, "base": True},
    }


def current_alt_internet_fact() -> dict[str, Any]:
    """Standing fact. Does not send a packet. Does not accept a caller watch.

    The three live flags stay false. When this process cannot see host
    hardware, the sentence says that and does not invent absent radios.
    """
    if not host_hardware_visible():
        return _fact(
            ISOLATE_SENTENCE,
            visible=False,
            machine=None,
            missing=[
                "host hardware (worker_hardware is false)",
                "a packet that leaves this machine and arrives on a different machine id",
            ],
        )
    try:
        probe = track2_carrier_probe()
    except OSError:
        probe = None
    carriers = probe["carriers"] if isinstance(probe, Mapping) else {}
    mid = machine_id()
    clauses = [_carrier_clause(cid, carriers.get(cid) if isinstance(carriers, Mapping) else None) for cid in CARRIER_ORDER]
    missing = ["a packet that leaves this machine and arrives on a different machine id"]
    for cid in CARRIER_ORDER:
        row = carriers.get(cid) if isinstance(carriers, Mapping) else None
        if not isinstance(row, Mapping) or row.get("state") == "REFUSE":
            code = row.get("code") if isinstance(row, Mapping) else None
            missing.append(f"{cid} ({code or RADIO_ABSENT})")
    if not mid:
        missing.append("machine id (MESH-HOST-ABSENT)")
    sentence = f"{HEAD} {' '.join(clauses)} {_machine_clause(mid)} {TAIL}"
    return _fact(sentence, visible=True, machine=mid, missing=missing)


def sentence_for(report: Mapping[str, Any] | None = None) -> str:
    """The operating-system sentence. A caller report cannot make it live."""
    del report
    return str(current_alt_internet_fact()["not_live_sentence"])


def _base(earned: bool) -> dict[str, Any]:
    return {
        "ok": earned,
        "refused": not earned,
        "live": earned,
        "installed": False,
        "base": True,
        "packet_path_live": earned,
        "alt_internet_live": earned,
        "foreign_arrival": earned,
        "second_device": earned,
        "booted": False,
        "kernel": False,
        "kernel_base": False,
        "mock": False,
        "public_door": "FG-STUB",
        "d2d_status": "NOT-READY",
        "warn5": "STANDS-until-demonstrated",
        "cap7": "Cap-7",
        "aziel": ".aziel",
        "cap7_is_path": False,
        "aziel_is_path": False,
        "cap7_public_egress": False,
        "public_icann": False,
        "bgp": False,
        "carrier_order": list(CARRIER_ORDER),
        "internet_base": {"live": earned, "installed": False, "base": True},
    }


def carry_path(
    *,
    mock: bool = False,
    interfaces: list[dict[str, str]] | None = None,
    hardware: Mapping[str, bool] | None = None,
    guest_log: str = "",
) -> dict[str, Any]:
    """Try the real carriers. A mock and a guest log never count as live."""
    if guest_log_is_boot(guest_log) or guest_log_is_path(guest_log):
        raise AssertionError("a guest log line was treated as a boot or a live path")
    if mock:
        body = _base(False)
        body.update(
            {
                "mock_refused": True,
                "code": PACKET_NOT_CARRIED,
                "carriers": [_carrier_row(kind, False, code=RADIO_ABSENT) for kind in CARRIER_ORDER],
                "carry": None,
                "local_host": machine_id(),
                "remote_host": None,
            }
        )
        body["plain"] = sentence_for(body)
        return body

    lans = lan_interfaces() if interfaces is None else list(interfaces)
    seen = hardware_seen() if hardware is None else {kind: bool(hardware.get(kind)) for kind in CARRIER_ORDER}
    if interfaces is not None:
        seen["lan"] = bool(lans)
    refused: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    trip: dict[str, Any] | None = None
    used: dict[str, str] | None = None
    local = machine_id()

    if seen.get("lan") and lans:
        if not local:
            trip = {
                "ok": False,
                "code": HOST_ABSENT,
                "bytes_match": False,
                "local_host": None,
                "remote_host": None,
                "second_device": False,
                "foreign_arrival": False,
                "packet_live": False,
                "mock": False,
            }
        else:
            for cand in lans:
                trip = exchange_mesh(cand["address"], local)
                trip["interface"] = cand["name"]
                if trip.get("bytes_match") is True:
                    used = cand
                    break
        rows.append(_carrier_row("lan", True, code=(trip or {}).get("code"), frame_ok=False))
    else:
        rows.append(_carrier_row("lan", False, code=RADIO_ABSENT))
        refused.append({"id": "lan", "code": RADIO_ABSENT, "packet_live": False, "mock": False})

    for kind in CARRIER_ORDER[1:]:
        present = bool(seen.get(kind))
        if not present:
            rows.append(_carrier_row(kind, False, code=RADIO_ABSENT))
            refused.append({"id": kind, "code": RADIO_ABSENT, "packet_live": False, "mock": False, "frame_ok": frame_checks(kind)})
            continue
        rows.append(_carrier_row(kind, True, code=PACKET_NOT_CARRIED, frame_ok=frame_checks(kind)))
        refused.append({
            "id": kind,
            "code": PACKET_NOT_CARRIED,
            "packet_live": False,
            "mock": False,
            "frame_ok": frame_checks(kind),
        })

    # A same-machine frame is not a second device. These flags stay false.
    body = _base(False)
    if trip and trip.get("bytes_match") is True:
        body["code"] = PACKET_CARRIED
    elif trip and trip.get("code"):
        body["code"] = trip["code"]
    elif not any(row["state"] == "HW-PRESENT" for row in rows):
        body["code"] = RADIO_ABSENT
    elif seen.get("lan"):
        body["code"] = (trip or {}).get("code") or RADIO_ABSENT
    else:
        present = next((row for row in rows if row["state"] == "HW-PRESENT"), None)
        body["code"] = present["code"] if present else RADIO_ABSENT
    body.update(
        {
            "carriers": rows,
            "carry": None if trip is None else {**trip, "refused": refused, "packet_live": False, "alt_internet_live": False},
            "refused_carriers": refused,
            "local_host": None if trip is None else trip.get("local_host"),
            "remote_host": None if trip is None else trip.get("remote_host"),
            "interface": None if used is None else used["name"],
        }
    )
    body["second_device"] = False
    body["packet_path_live"] = False
    body["alt_internet_live"] = False
    body["live"] = False
    body["foreign_arrival"] = False
    body["ok"] = False
    body["refused"] = True
    body["internet_base"] = {"live": False, "installed": False, "base": True}
    body["plain"] = sentence_for(body)
    return body


def report() -> dict[str, Any]:
    """The path this process can actually run, computed once."""
    global _CACHE
    with _CACHE_LOCK:
        if _CACHE is None:
            _CACHE = carry_path()
        cached = _CACHE
    return copy.deepcopy(cached)
