"""The carrier path stays false until a packet arrives on another machine."""

from __future__ import annotations

from azos.carriers import (
    CARRIER_ORDER,
    ISOLATE_SENTENCE,
    carry_path,
    current_alt_internet_fact,
    encode_bluetooth,
    encode_photon,
    encode_rf,
    encode_wifi,
    foreign_arrival,
    frame_checks,
    guest_log_is_boot,
    guest_log_is_path,
    host_hardware_visible,
    lan_interfaces,
    machine_id,
    parse_bluetooth,
    parse_photon,
    parse_rf,
    parse_wifi,
    probe_lan,
    second_device,
)


def test_a_real_lan_frame_stays_on_this_machine() -> None:
    report = carry_path()
    assert report["alt_internet_live"] is False
    assert report["packet_path_live"] is False
    assert report["live"] is False
    assert report["second_device"] is False
    assert report["foreign_arrival"] is False
    assert report["booted"] is False
    assert report["installed"] is False
    assert report["kernel"] is False
    fact = current_alt_internet_fact()
    assert report["plain"] == fact["not_live_sentence"]
    assert fact["alt_internet_live"] is False
    assert fact["packet_path_live"] is False
    assert fact["internet_base"]["live"] is False
    assert "Still missing: a packet that leaves this machine and arrives on a different machine id." in report["plain"]
    if not lan_interfaces():
        return
    carry = report["carry"]
    assert carry["bytes_match"] is True
    assert carry["code"] == "SAME-MACHINE-REFUSED"
    assert carry["code"] != "PACKET-CARRIED"
    assert "PACKET-CARRIED" not in carry["code"]
    assert "not a live packet path" in carry["plain"]
    assert "not a second device" in carry["plain"]
    assert carry["local_host"] == carry["remote_host"]
    assert carry["source_ip"] == carry["address"]
    assert carry["interface"] != "lo"
    assert carry["packet_live"] is False
    assert carry["sent_sha256"] == carry["received_sha256"]
    assert "is present on this machine and is not a second device." in report["plain"]
    assert "A second device stays false while both ends share that id." in report["plain"]


def test_order_is_lan_then_wifi_then_bluetooth_then_rf_then_photon() -> None:
    assert CARRIER_ORDER == ("lan", "wifi", "bluetooth", "rf", "photon")


def test_absent_hardware_names_every_missing_carrier() -> None:
    report = carry_path(interfaces=[], hardware={kind: False for kind in CARRIER_ORDER})
    assert report["code"] == "QNM-RADIO-ABSENT"
    assert report["alt_internet_live"] is False
    assert report["packet_path_live"] is False
    assert report["live"] is False
    assert report["second_device"] is False
    assert report["foreign_arrival"] is False
    assert report["plain"] == current_alt_internet_fact()["not_live_sentence"]
    assert [row["code"] for row in report["carriers"]] == ["QNM-RADIO-ABSENT"] * 5


def test_wifi_without_lan_names_the_missing_round_trip() -> None:
    report = carry_path(
        interfaces=[],
        hardware={"lan": False, "wifi": True, "bluetooth": False, "rf": False, "photon": False},
    )
    assert report["code"] == "PACKET-NOT-CARRIED"
    assert report["packet_path_live"] is False
    assert report["alt_internet_live"] is False
    assert report["plain"] == current_alt_internet_fact()["not_live_sentence"]
    wifi = next(row for row in report["carriers"] if row["id"] == "wifi")
    assert wifi["state"] == "HW-PRESENT"
    assert wifi["frame_ok"] is True
    assert wifi["packet_live"] is False


def test_preference_names_lan_before_wifi_when_lan_cannot_leave() -> None:
    report = carry_path(
        interfaces=[{"name": "en-test", "address": "203.0.113.1"}],
        hardware={"lan": True, "wifi": True, "bluetooth": False, "rf": False, "photon": False},
    )
    assert report["code"] == "PACKET-NOT-CARRIED"
    assert report["packet_path_live"] is False
    assert report["alt_internet_live"] is False
    assert report["plain"] == current_alt_internet_fact()["not_live_sentence"]
    assert report["internet_base"]["live"] is False


def test_mock_is_not_a_live_path() -> None:
    report = carry_path(mock=True, guest_log="AZOS-BOOTED")
    assert report["mock"] is False
    assert report["alt_internet_live"] is False
    assert report["packet_path_live"] is False
    assert report["booted"] is False
    assert report["kernel"] is False
    assert report["installed"] is False
    assert report["plain"] == current_alt_internet_fact()["not_live_sentence"]
    assert report["internet_base"]["live"] is False


def test_guest_log_does_not_boot_or_open_a_path() -> None:
    guest = "\n".join(
        (
            "AZOS-BOOTED",
            "AZOS-INSTALLED",
            "MAIL-SENT",
            "MESH-NODE-LIVE",
            "PHOENIX-RESEALED",
            "packet_path_live true",
            "second_device true",
        )
    )
    assert guest_log_is_boot(guest) is False
    assert guest_log_is_path(guest) is False
    assert guest_log_is_boot("AZOS-BOOTED\nAZOS-INSTALLED") is False
    assert guest_log_is_path("AZOS-BOOTED") is False


def _published_text(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(_published_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(_published_text(item) for item in value)
    return ""


def test_guest_boot_line_does_not_imply_host_boot_install_mail_or_mesh() -> None:
    guest = "\n".join(
        (
            "AZOS-BOOTED",
            "AZOS-INSTALLED",
            "MAIL-SENT",
            "mesh_node_live true",
            "PHOENIX-RESEALED",
            "host phoenix live",
        )
    )
    report = carry_path(mock=True, guest_log=guest)
    for key in (
        "alt_internet_live",
        "packet_path_live",
        "second_device",
        "foreign_arrival",
        "live",
        "booted",
        "kernel",
        "installed",
        "os_yet",
        "mail_send",
        "mesh_node_live",
        "one_click_install_live",
    ):
        assert report[key] is False
    assert report["internet_base"]["live"] is False
    assert report["internet_base"]["installed"] is False
    published = _published_text(report)
    assert "AZOS-BOOTED" not in published
    assert "AZOS-INSTALLED" not in published
    assert "PHOENIX-RESEALED" not in published
    assert "Phoenix is a local wait and re-seal." in report["plain"]
    assert "host phoenix" not in report["plain"].lower()


def test_same_machine_frame_is_not_painted_as_a_live_path(monkeypatch) -> None:
    host = "ab" * 16

    def fake(address: str, local: str) -> dict:
        return {
            "ok": True,
            "code": "PACKET-CARRIED",
            "address": address,
            "source_ip": address,
            "bytes_match": True,
            "local_host": local,
            "remote_host": local,
            "second_device": True,
            "foreign_arrival": True,
            "packet_live": True,
            "packet_path_live": True,
            "alt_internet_live": True,
            "mock": False,
        }

    monkeypatch.setattr("azos.carriers.exchange_mesh", fake)
    monkeypatch.setattr("azos.carriers.machine_id", lambda: host)
    report = carry_path(interfaces=[{"name": "en-test", "address": "203.0.113.10"}])
    assert report["code"] == "SAME-MACHINE-REFUSED"
    assert report["carry"]["code"] == "SAME-MACHINE-REFUSED"
    assert "PACKET-CARRIED" not in _published_text(report)
    for key in (
        "alt_internet_live",
        "packet_path_live",
        "second_device",
        "foreign_arrival",
        "live",
        "booted",
        "installed",
        "kernel",
        "mail_send",
        "mesh_node_live",
    ):
        assert report[key] is False
    assert report["carry"]["packet_live"] is False
    assert report["carry"]["second_device"] is False
    assert report["carry"]["foreign_arrival"] is False
    assert report["carry"]["packet_path_live"] is False
    assert "not a live packet path" in report["carry"]["plain"]
    assert "not a second device" in report["carry"]["plain"]
    assert report["local_host"] == report["remote_host"] == host


def test_same_machine_id_is_not_a_second_device() -> None:
    host = "a" * 32
    assert second_device(host, host) is False
    assert second_device(host, "b" * 32) is True
    assert (
        foreign_arrival(
            bytes_match=True,
            local_host=host,
            remote_host="b" * 32,
            source_ip="127.0.0.1",
            local_addrs={"127.0.0.1", "203.0.113.2"},
            mock=False,
        )
        is False
    )
    assert (
        foreign_arrival(
            bytes_match=True,
            local_host=host,
            remote_host=host,
            source_ip="203.0.113.8",
            local_addrs={"127.0.0.1"},
            mock=False,
        )
        is False
    )
    assert (
        foreign_arrival(
            bytes_match=True,
            local_host=host,
            remote_host="b" * 32,
            source_ip="203.0.113.8",
            local_addrs={"127.0.0.1"},
            mock=True,
        )
        is False
    )


def test_frames_check_without_becoming_live() -> None:
    payload = bytes((1, 2, 3, 4))
    for encode, parse in (
        (encode_wifi, parse_wifi),
        (encode_bluetooth, parse_bluetooth),
        (encode_rf, parse_rf),
        (encode_photon, parse_photon),
    ):
        parsed = parse(encode(payload))
        assert parsed is not None
        assert parsed["payload"] == payload
        assert parsed["packet_live"] is False
        assert parsed["mock"] is False
    for kind in ("wifi", "bluetooth", "rf", "photon"):
        assert frame_checks(kind) is True


def test_cap7_and_aziel_stay_names() -> None:
    report = carry_path(interfaces=[], hardware={kind: False for kind in CARRIER_ORDER})
    assert report["cap7"] == "Cap-7"
    assert report["aziel"] == ".aziel"
    assert report["cap7_is_path"] is False
    assert report["aziel_is_path"] is False
    assert report["cap7_public_egress"] is False
    assert "Cap-7 and .aziel stay names, not a public registrar and not ICANN or BGP." in report["plain"]
    assert report["public_icann"] is False
    assert report["bgp"] is False


def test_fact_matches_the_host_probe() -> None:
    fact = current_alt_internet_fact()
    assert fact["alt_internet_live"] is False
    assert fact["packet_path_live"] is False
    assert fact["second_device"] is False
    assert fact["internet_base"] == {"live": False, "installed": False, "base": True}
    assert fact["public_mail_send_live"] is False
    assert fact["kernel_live"] is False
    assert fact["boot_live"] is False
    assert fact["public_door"] == "FG-STUB"
    assert fact["worker_hardware"] is False
    assert fact["cap7_name_only"] is True
    assert fact["not_live_sentence"] == fact["missing_line"]
    sentence = fact["not_live_sentence"]
    assert sentence.startswith(
        "An alternative internet is not live (alt_internet_live is false). "
        "A packet path is not live (packet_path_live is false)."
    )
    if host_hardware_visible():
        assert fact["host_hardware_visible"] is True
        assert "cannot see host hardware" not in sentence
        lan = probe_lan()
        if lan["present"] and lan["up"] and lan["address"]:
            named = (
                f"LAN interface {lan['kind']} at {lan['address']} "
                "is present on this machine and is not a second device."
            )
            assert named in sentence
        mid = machine_id()
        if mid:
            assert fact["machine_id"] == mid
            assert f"This machine id is {mid}." in sentence
            assert "A second device stays false while both ends share that id." in sentence
    else:
        assert sentence == ISOLATE_SENTENCE
        assert fact["machine_id"] is None
        assert "QNM-RADIO-ABSENT" not in sentence


def test_invisible_hardware_does_not_invent_radios(monkeypatch) -> None:
    monkeypatch.setattr("azos.carriers.host_hardware_visible", lambda: False)
    fact = current_alt_internet_fact()
    assert fact["not_live_sentence"] == ISOLATE_SENTENCE
    assert fact["machine_id"] is None
    assert fact["host_hardware_visible"] is False
    assert fact["alt_internet_live"] is False
    assert fact["packet_path_live"] is False
    assert "QNM-RADIO-ABSENT" not in fact["not_live_sentence"]
    assert "Wi-Fi hardware is absent" not in fact["not_live_sentence"]
    assert "Bluetooth hardware is absent" not in fact["not_live_sentence"]


def test_public_pages_do_not_bake_this_host() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    banned: list[str] = []
    mid = machine_id()
    if mid:
        banned.append(mid)
    lan = probe_lan()
    if lan.get("address"):
        banned.append(str(lan["address"]))
    pages = (
        root / "workers" / "download-tracker" / "src" / "runtime.js",
        root / "workers" / "download-tracker" / "src" / "homepage.js",
        root / "azos" / "templates" / "ui.html",
        root / "README.md",
        root / "SKILL.md",
    )
    for page in pages:
        text = page.read_text(encoding="utf-8")
        assert ISOLATE_SENTENCE in text
        for secret in banned:
            assert secret not in text
