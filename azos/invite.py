"""Voluntary adoption. Propagation is invitation, not infection.

`azos invite` prints principles and a download URL. It does not copy
this overlay onto other machines, write outside cwd, or self-replicate.
"""

from __future__ import annotations

from typing import TextIO

from azos.ethics import MOTTO

DOWNLOAD_URL = "https://azos-download-tracker.vibelock.workers.dev/"
SOURCE_URL = "https://github.com/AzielEliab/azos"

PRINCIPLES = """AZ-OS — ethics-coded remote shell (voluntary; not an infection)

AZ-OS is a true remote shell gated by coded ethics. You run it because
you choose to. It is not a kernel, bootloader, hypervisor, or malware.
It is not unrestricted host bash and not SSH.

""" + MOTTO + """

Principles
  1. Integrity precedes execution.
     No module, session, or command runs without a token from ARC.
  2. Time-bound actions are final.
     Authorized executions append to an immutable sha256 chain. No rewrite.
  3. Understanding precedes modification.
     Extending or loading a module requires an explicit comprehension
     checkbox and a short restatement of intent.
  4. The system protects itself architecturally.
     Unsigned or unauthorized run() raises AuthorizationError. Default deny.
  5. Propagation is not infection.
     This invite prints principles and a download URL. AZ-OS does not
     copy itself onto other machines.

Scope (honest)
  Protocols: HTTPS JSON (hosted Worker), HTTP loopback 127.0.0.1:8800,
             CLI stdin (`azos shell`).
  Auth:      ARC 32-byte token after the five ethics gates. Hashed at rest.
  Sandbox:   session vfs under .azos/workspace (local) or KV vfs (hosted).
             No host subprocess. Halt stops the overlay session, not the
             caller OS.

You are invited to run AZ-OS yourself. This is not a silent block.
Adoption is voluntary.

Counted download:
  {download}

Source:
  {source}
""".strip()


def invite_text() -> str:
    return PRINCIPLES.format(download=DOWNLOAD_URL, source=SOURCE_URL) + "\n"


def emit_invite(stream: TextIO) -> None:
    """Print the invite. Writes nothing to the filesystem."""
    stream.write(invite_text())
    if not invite_text().endswith("\n"):
        stream.write("\n")
