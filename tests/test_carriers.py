"""The carrier path stays false until a packet arrives on another machine."""

from __future__ import annotations

from azos.carriers import (
    CARRIER_ORDER,
    carry_path,
    lan_interfaces,
    encode_bluetooth,
    encode_photon,
    encode_rf,
    encode_wifi,
    foreign_arrival,
    frame_checks,
    guest_log_is_boot,
    guest_log_is_path,
    parse_bluetooth,
    parse_photon,
    parse_rf,
    parse_wifi,
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
    if not lan_interfaces():
        assert "still missing" in report["plain"]
        return
    carry = report["carry"]
    assert carry["bytes_match"] is True
    assert carry["code"] == "PACKET-CARRIED"
    assert carry["local_host"] == carry["remote_host"]
    assert carry["source_ip"] == carry["address"]
    assert carry["interface"] != "lo"
    assert carry["packet_live"] is False
    assert carry["sent_sha256"] == carry["received_sha256"]
    assert report["plain"].endswith(
        "A frame moved on this machine. A second device is still missing. Both ends share one machine id."
    )


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
    assert report["plain"].endswith(
        "LAN, Wi-Fi, Bluetooth, RF, and photon hardware are still missing."
    )
    assert [row["code"] for row in report["carriers"]] == ["QNM-RADIO-ABSENT"] * 5


def test_wifi_without_lan_names_the_missing_round_trip() -> None:
    report = carry_path(
        interfaces=[],
        hardware={"lan": False, "wifi": True, "bluetooth": False, "rf": False, "photon": False},
    )
    assert report["code"] == "PACKET-NOT-CARRIED"
    assert report["packet_path_live"] is False
    assert report["alt_internet_live"] is False
    assert "Wi-Fi hardware is present. A round trip on that hardware is still missing." in report["plain"]
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
    assert "Wi-Fi hardware is present" not in report["plain"]
    assert report["plain"].endswith(
        "A packet that leaves this machine and arrives on a different machine is still missing."
    )


def test_mock_is_not_a_live_path() -> None:
    report = carry_path(mock=True, guest_log="AZOS-BOOTED")
    assert report["mock"] is False
    assert report["alt_internet_live"] is False
    assert report["packet_path_live"] is False
    assert report["booted"] is False
    assert report["kernel"] is False
    assert report["installed"] is False
    assert report["plain"].endswith(
        "A mock path is not a live path. A real packet on a different machine is still missing."
    )


def test_guest_log_does_not_boot_or_open_a_path() -> None:
    assert guest_log_is_boot("AZOS-BOOTED\nAZOS-INSTALLED") is False
    assert guest_log_is_path("AZOS-BOOTED") is False


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
            local_addrs={"127.0.0.1", "172.30.0.2"},
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
    assert "Cap-7" not in report["plain"]
    assert ".aziel" not in report["plain"]
