"""AZ-OS + AZ Interface: ethics-coded remote shell.

July 2026 papers by Aziel Eliab. Integrity precedes execution.
Propagation is invitation, not infection. Forks are welcome.

AZ-OS is a true remote shell gated by coded ethics. Sessions and
commands are principle-bound. It is not a kernel, bootloader,
hypervisor, worm, malware, or unrestricted host bash.
"""

from __future__ import annotations

from azos.errors import (
    AppendOnlyError,
    AuthorizationError,
    AzosError,
    GateFail,
)
from azos.ethics import KIND, PRINCIPLES, scope_dict
from azos.gate import GATES, Proposal
from azos.invite import DOWNLOAD_URL, invite_text
from azos.runtime import Runtime

__version__ = "0.2.0"
__author__ = "Aziel Eliab"
__all__ = [
    "AppendOnlyError",
    "AuthorizationError",
    "AzosError",
    "DOWNLOAD_URL",
    "GATES",
    "KIND",
    "PRINCIPLES",
    "GateFail",
    "Proposal",
    "Runtime",
    "invite_text",
    "scope_dict",
    "__version__",
]
