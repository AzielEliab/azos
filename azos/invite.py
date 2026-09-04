"""Voluntary adoption. Propagation is invitation, not infection.

`azos invite` prints principles and a download URL. It does not copy
this overlay onto other machines, write outside cwd, or self-replicate.
"""

from __future__ import annotations

from typing import TextIO

from azos.ethics import MOTTO

DOWNLOAD_URL = "https://azos-download-tracker.vibelock.workers.dev/"
SOURCE_URL = "https://github.com/AzielEliab/azos"

PRINCIPLES = (
    "AZ-OS — ethics-coded remote shell (voluntary; not an infection)\n"
    "\n"
    "AZ-OS is a true remote shell gated by coded ethics. You run it because\n"
    "you choose to. It is not a kernel, bootloader, hypervisor, or malware.\n"
    "It is not unrestricted host bash and not SSH.\n"
    "\n"
    f"{MOTTO}\n"
    "\n"
    "Principles\n"
    "  1. Integrity precedes execution.\n"
    "     No module, session, or command runs without a token from ARC.\n"
    "  2. Time-bound actions are final.\n"
    "     Authorized executions append to an immutable sha256 chain. No rewrite.\n"
    "  3. Understanding precedes modification.\n"
    "     Extending or loading a module requires an explicit comprehension\n"
    "     checkbox and a short restatement of intent.\n"
    "  4. The system protects itself architecturally.\n"
    "     Unsigned or unauthorized run() raises AuthorizationError. Default deny.\n"
    "  5. Propagation is not infection.\n"
    "     This invite prints principles and a download URL. AZ-OS does not\n"
    "     copy itself onto other machines.\n"
    "\n"
    "Scope (honest)\n"
    "  Protocols: HTTPS JSON (hosted Worker), HTTP loopback 127.0.0.1:8800,\n"
    "             CLI stdin (`azos shell`).\n"
    "  Auth:      ARC 32-byte token after the five ethics gates. Hashed at rest.\n"
    "  Sandbox:   session vfs under .azos/workspace (local) or KV vfs (hosted).\n"
    "             No host subprocess. Halt stops the overlay session, not the\n"
    "             caller OS.\n"
    "\n"
    "You are invited to run AZ-OS yourself. This is not a silent block.\n"
    "Adoption is voluntary.\n"
    "\n"
    "Counted download:\n"
    "  {download}\n"
    "\n"
    "Source:\n"
    "  {source}"
)


def invite_text() -> str:
    return PRINCIPLES.format(download=DOWNLOAD_URL, source=SOURCE_URL) + "\n"


def emit_invite(stream: TextIO) -> None:
    """Print the invite. Writes nothing to the filesystem."""
    stream.write(invite_text())
    if not invite_text().endswith("\n"):
        stream.write("\n")
