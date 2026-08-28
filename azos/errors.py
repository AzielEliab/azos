"""AZ-OS errors. Default is deny."""

from __future__ import annotations


class AzosError(Exception):
    """Base error for the overlay."""


class AuthorizationError(AzosError):
    """Unsigned or unauthorized run(). Default deny.

    Unauthorized environments receive an invite, not a silent block.
    """

    def __init__(self, message: str = "unauthorized: no ARC token") -> None:
        super().__init__(message)
        self.invite = True


class AppendOnlyError(AzosError):
    """The execution log cannot be rewritten."""


class GateFail(AzosError):
    """A proposed action failed one or more of the five gates."""


class HaltedError(AuthorizationError):
    """The overlay is halted. Lumen still runs (revoke / purge only)."""

    def __init__(self, message: str = "halted: execution authority is final") -> None:
        super().__init__(message)
