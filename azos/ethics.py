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
    "worm": False,
    "malware": False,
    "unrestricted_host_shell": False,
    "kills_caller_os": False,
    "prefab_desktop": True,
    "windows_shell": True,
    "integrity_lattice": "temporallock_staticclock",
    "author": AUTHOR,
}


def scope_dict() -> dict[str, object]:
    """JSON-ready honest scope (protocols, auth, sandbox)."""
    out: dict[str, object] = {}
    for key, value in SCOPE.items():
        if isinstance(value, tuple):
            out[key] = list(value)
        else:
            out[key] = value
    out["principles"] = list(PRINCIPLES)
    out["gates"] = list(GATES)
    out["motto"] = MOTTO
    return out


def principles_block() -> str:
    lines = [f"  {i}. {p}" for i, p in enumerate(PRINCIPLES, start=1)]
    return "Principles\n" + "\n".join(lines)
