"""AZ-OS + AZ Interface: a portable ethical overlay, not a kernel.

July 2026 papers by Aziel Eliab. Integrity precedes execution.
Propagation is invitation, not infection. Forks are welcome.

This package is a soft overlay (a folder + control surface). It is not
an operating system, bootloader, hypervisor, worm, or malware.
"""

from __future__ import annotations

from azos.errors import (
    AppendOnlyError,
    AuthorizationError,
    AzosError,
    GateFail,
)
from azos.gate import GATES, Proposal
from azos.invite import DOWNLOAD_URL, invite_text
from azos.runtime import Runtime

__version__ = "0.1.0"
__author__ = "Aziel Eliab"
__all__ = [
    "AppendOnlyError",
    "AuthorizationError",
    "AzosError",
    "DOWNLOAD_URL",
    "GATES",
    "GateFail",
    "Proposal",
    "Runtime",
    "invite_text",
    "__version__",
]
