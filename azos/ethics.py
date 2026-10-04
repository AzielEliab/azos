"""Coded ethics from the AZ-OS whitepaper.

Every session open and every command is principle-bound. The five gates
are the executable form of the five principles. Default is deny.

This module does not vend DecisionGATE as a product. It reimplements the
tiny inline check the papers describe.
"""

from __future__ import annotations

from typing import Mapping

AUTHOR = "Aziel Eliab"
MOTTO = "Integrity precedes execution."
KIND = "ethics_coded_remote_shell"
VERSION_HINT = "0.3.0"

PRINCIPLES: tuple[str, ...] = (
    "Integrity precedes execution.",
    "Time-bound actions are final.",
    "Understanding precedes modification.",
    "The system protects itself architecturally.",
    "Propagation is not infection.",
)

GATES: tuple[str, ...] = (
    "definition",
    "evidence",
    "impact",
    "integrity",
    "responsibility",
)

# Closed shell verb list. Names only. Never a user-supplied callable.
SHELL_VERBS: frozenset[str] = frozenset(
    {
        "help",
        "pwd",
        "ls",
        "cat",
        "write",
        "echo",
        "mkdir",
        "rm",
        "cd",
        "status",
        "principles",
        "invite",
        "modules",
        "list_modules",
        "history",
        "whoami",
        "session",
        "halt",
        "exit",
        "close",
        "id",
        "uname",
    }
)

# Verbs that must never run, even if someone tries to register them later.
DENIED_VERBS: frozenset[str] = frozenset(
    {
        "sudo",
        "bash",
        "sh",
        "zsh",
        "fish",
        "python",
        "perl",
        "ruby",
        "node",
        "curl",
        "wget",
        "nc",
        "ncat",
        "nmap",
        "ssh",
        "scp",
        "sftp",
        "chmod",
        "chown",
        "mkfs",
        "dd",
        "reboot",
        "shutdown",
        "kill",
        "pkill",
        "eval",
        "exec",
        "compile",
        "system",
        "popen",
        "apt",
        "yum",
        "brew",
        "docker",
        "kubectl",
    }
)

BANNED_IMPACT: tuple[str, ...] = (
    "wipe disk",
    "format drive",
    "mkfs",
    "self-replicate",
    "self replicate",
    "worm",
    "ransom",
    "infect",
)

# Host-shell metacharacters imply spawn. The ethics shell is not bash.
HOST_META: tuple[str, ...] = ("|", ";", "`", "$(", "&&", "||", "\n", "\r")

MAX_COMMAND_CHARS = 4096
MAX_FILE_BYTES = 65536
HISTORY_CAP = 100

USERSPACE_YES = "The userspace base is present. That is a base, not a boot."

SCOPE: Mapping[str, object] = {
    "kind": KIND,
    "remote_shell": True,
    "ethics_gated": True,
    "protocols": ("https-json", "http-loopback", "cli-stdin"),
    "auth": "arc-token-after-five-gates",
    "sandbox": "session-vfs",
    "host_subprocess": False,
    "ssh": False,
    "kernel": False,
    "kernel_base": False,
    "booted": False,
    "installed": False,
    "os_yet": False,
    "userspace_base": True,
    "internet_base": {"live": False, "installed": False},
    "alt_internet_live": False,
    "mail_send": False,
    "one_click_install_live": False,
    "mesh_node_live": False,
    "doors_replaced": False,
    "app_shells_started": False,
    "worm": False,
    "malware": False,
    "unrestricted_host_shell": False,
    "kills_caller_os": False,
    "prefab_desktop": True,
    "windows_shell": True,
    "integrity_lattice": "temporallock_staticclock",
    "author": AUTHOR,
}


def _copy_scope_value(value: object) -> object:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return {key: _copy_scope_value(item) for key, item in value.items()}
    return value


def plain_limits(facts: Mapping[str, object] | None = None) -> str:
    """Short sentences for a person. True stays true. False stays false."""
    src: Mapping[str, object] = facts if facts is not None else SCOPE
    internet = src.get("internet_base")
    net = internet if isinstance(internet, Mapping) else {}

    def said(flag: str, yes: str, no: str) -> str:
        return yes if src.get(flag) is True else no

    if src.get("userspace_base") is True:
        userspace = USERSPACE_YES
    else:
        userspace = "The userspace base is absent."
    net_live = "live" if net.get("live") is True else "not live"
    net_installed = "installed" if net.get("installed") is True else "not installed"
    return " ".join(
        (
            said("kernel", "There is a kernel.", "There is no kernel."),
            said("kernel_base", "The kernel base is present.", "The kernel base is absent."),
            said("booted", "This has booted.", "This has not booted."),
            said(
                "installed",
                "This is installed as an operating system.",
                "This is not installed as an operating system.",
            ),
            said("os_yet", "This is an operating system.", "This is not an operating system yet."),
            userspace,
            f"The internet base is {net_live} and {net_installed}.",
            said(
                "alt_internet_live",
                "An alternative internet is live.",
                "An alternative internet is not live.",
            ),
            said("mail_send", "Mail can be sent from here.", "Mail is not sent from here."),
            said(
                "one_click_install_live",
                "One-click install is live.",
                "One-click install is not live.",
            ),
            said("mesh_node_live", "This is a live mesh node.", "This is not a live mesh node."),
            said("doors_replaced", "An existing door was replaced.", "Existing doors stay in place."),
            said("app_shells_started", "App shells were started.", "App shells are not started."),
        )
    )


def plain_news_listing(news: object) -> str:
    """AZNews and 4DMap stay unjoined and not live until a fetched item lands."""
    record = news if isinstance(news, Mapping) else {}
    paths = record.get("paths") if isinstance(record.get("paths"), Mapping) else {}
    joined = paths.get("joined") if isinstance(paths.get("joined"), Mapping) else {}
    landed = record.get("item_landed") is True
    live = (
        record.get("live") is True
        or joined.get("live") is True
        or record.get("merged") is True
    )
    if landed and live:
        return (
            "AZNews and 4DMap are listed. A fetched news item has landed as a map pin, "
            "so the join is marked live."
        )
    if landed:
        return (
            "AZNews and 4DMap are listed. A fetched news item has landed as a map pin. "
            "They are not marked live."
        )
    return (
        "AZNews and 4DMap are listed. They are not joined and not live. "
        "No fetched news item has landed as a map pin."
    )


INTERFACE_LINE = (
    "AZ Interface is a separate shell. It is not this kernel and not this boot."
)


def human_limits(status: Mapping[str, object] | None = None) -> str:
    """OS limits, the news listing, and the separate interface shell, as sentences."""
    news = status.get("news_map") if isinstance(status, Mapping) else None
    return plain_limits(status) + " " + plain_news_listing(news) + " " + INTERFACE_LINE


def scope_dict() -> dict[str, object]:
    """JSON-ready honest scope (protocols, auth, sandbox)."""
    out: dict[str, object] = {}
    for key, value in SCOPE.items():
        out[key] = _copy_scope_value(value)
    out["principles"] = list(PRINCIPLES)
    out["gates"] = list(GATES)
    out["motto"] = MOTTO
    out["limits_plain"] = plain_limits(out)
    return out


def principles_block() -> str:
    lines = [f"  {i}. {p}" for i, p in enumerate(PRINCIPLES, start=1)]
    return "Principles\n" + "\n".join(lines)
