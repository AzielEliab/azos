"""The human app may show a userspace base. It may not call a refused door live."""

from __future__ import annotations

import re
from pathlib import Path

from azos.carriers import ISOLATE_SENTENCE
from azos.ethics import USERSPACE_YES
from azos.invite import invite_text

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "mobile" / "lib"
MOBILE = ROOT / "mobile"

# Affirmative claims. Negative sentences such as "This has not booted." do not match.
LIVE_CLAIMS = (
    "There is a kernel.",
    "The kernel is live",
    "The kernel base is present.",
    "kernel is true",
    "This has booted.",
    "The host has booted",
    "booted is true",
    "This is installed as an operating system.",
    "This app is installed",
    "The app is installed",
    "installed is true",
    "The internet base is live",
    "internet base is live",
    "An alternative internet is live.",
    "alternative internet is live",
    "alt_internet_live is true",
    "A packet path is live",
    "packet_path_live is true",
    "Mail can be sent from here.",
    "Mail is sent from here.",
    "mail send is live",
    "This is a live mesh node.",
    "mesh node is live",
    "A second device is marked present",
    "A second device is live",
    "There is a second device",
    "second device is true",
    "One-click install is live.",
    "userspace_is_boot': true",
    "That is a boot.",
)

TRUE_FLAGS = (
    "kernel",
    "booted",
    "installed",
    "internet_base_live",
    "alt_internet_live",
    "packet_path_live",
    "mail_send",
    "mesh_node_live",
    "second_device",
    "userspace_is_boot",
)


def _lib_text() -> str:
    parts = [path.read_text(encoding="utf-8") for path in sorted(LIB.glob("*.dart"))]
    return "\n".join(parts)


def _flags(text: str) -> dict[str, str]:
    block = re.search(r"const Map<String, bool> kFlags = <String, bool>\{(.*?)\};", text, re.S)
    assert block, "kFlags missing"
    return dict(re.findall(r"'([A-Za-z0-9_]+)': (true|false)", block.group(1)))


def _dart_string(text: str, name: str) -> str:
    """Join the literal assigned to a const String, including adjacent quotes."""
    match = re.search(rf"const String {name}\s*=", text)
    assert match, name
    rest = text[match.end() :].lstrip()
    if rest.startswith("'''"):
        end = rest.index("'''", 3)
        return rest[3:end]
    end = rest.index(";")
    parts = re.findall(r"'((?:\\'|[^'])*)'", rest[:end])
    return "".join(part.replace("\\'", "'") for part in parts)


def published_limits() -> str:
    """The public worker hardcodes the isolate sentence. A host radio probe is not that page."""
    return " ".join(
        (
            "There is no kernel.",
            "The kernel base is absent.",
            "This has not booted.",
            "This is not installed as an operating system.",
            "This is not an operating system yet.",
            USERSPACE_YES,
            ISOLATE_SENTENCE,
            "Mail is not sent from here.",
            "One-click install is not live.",
            "This is not a live mesh node.",
            "Existing doors stay in place.",
            "App shells are not started.",
        )
    )


def test_app_sentences_match_the_worker_and_invite() -> None:
    text = _lib_text()
    limits = published_limits()
    homepage = (ROOT / "workers" / "download-tracker" / "src" / "homepage.js").read_text(encoding="utf-8")
    assert f'id="limits-plain">{limits}</p>' in homepage
    assert _dart_string(text, "kLimitsPlain") == limits
    assert "The userspace base is present. That is a base, not a boot." in text
    assert "alt_internet_live is false" in text
    assert "packet_path_live is false" in text
    assert "The public door stays FG-STUB." in text
    assert "Isolation is single-node security-awareness." in text
    assert "Phoenix is a local wait and re-seal." in text
    assert "One-click install is not live." in text
    assert "AZNews and 4DMap are listed. They are not joined and not live." in text
    assert "There is no second device." in text
    assert "The public worker does not run a kernel." in text
    assert "Boot does not run on the public worker." in text
    assert "AZ Interface is a separate shell. It is not this kernel and not this boot." in text
    assert _dart_string(text, "kInvite") == invite_text()


def test_app_does_not_say_refused_doors_are_live() -> None:
    text = _lib_text()
    flags = _flags(text)
    assert flags["userspace_base"] == "true"
    assert set(flags) == {
        "kernel",
        "booted",
        "installed",
        "internet_base_live",
        "alt_internet_live",
        "packet_path_live",
        "mail_send",
        "mesh_node_live",
        "second_device",
        "userspace_base",
        "userspace_is_boot",
    }
    for name in TRUE_FLAGS:
        assert flags[name] == "false"
        assert re.search(rf"['\"]{name}['\"]\s*:\s*true", text) is None
    for claim in LIVE_CLAIMS:
        assert claim not in text, claim
    assert "curl -fsSL" not in text
    assert "install.sh" not in text
    assert "play.google.com" not in text
    assert "apps.apple.com" not in text


def test_platform_projects_are_real_and_not_a_store_listing() -> None:
    assert (MOBILE / "android" / "app" / "build.gradle.kts").is_file()
    gradle = (MOBILE / "android" / "app" / "build.gradle.kts").read_text(encoding="utf-8")
    assert 'applicationId = "com.azieeliab.azos"' in gradle
    assert (MOBILE / "android" / "app" / "src" / "main" / "kotlin" / "com" / "azieeliab" / "azos" / "MainActivity.kt").is_file()

    pbx = (MOBILE / "ios" / "Runner.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
    assert "PRODUCT_BUNDLE_IDENTIFIER = com.azieeliab.azos;" in pbx
    assert (MOBILE / "ios" / "Runner.xcworkspace" / "contents.xcworkspacedata").is_file()
    assert (MOBILE / "ios" / "Runner" / "AppDelegate.swift").is_file()
    assert (MOBILE / "ios" / "Runner" / "Info.plist").is_file()

    assert (MOBILE / "linux" / "CMakeLists.txt").is_file()
    assert 'set(APPLICATION_ID "com.azieeliab.azos")' in (MOBILE / "linux" / "CMakeLists.txt").read_text(encoding="utf-8")
    assert (MOBILE / "macos" / "Runner.xcodeproj" / "project.pbxproj").is_file()
    assert (MOBILE / "windows" / "CMakeLists.txt").is_file()
    assert (MOBILE / "windows" / "runner" / "main.cpp").is_file()

    assert not (MOBILE / "fastlane").exists()
    assert not (MOBILE / "store").exists()
    assert not list(MOBILE.rglob("*.ipa"))
    assert not list(MOBILE.rglob("install.sh"))
