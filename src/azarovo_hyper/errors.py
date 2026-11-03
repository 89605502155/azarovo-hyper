"""Exception hierarchy.

Every error raised by the library derives from :class:`HyperError`, so callers
can catch one type and still tell the cases apart when they need to.
"""

from __future__ import annotations


class HyperError(Exception):
    """Base class for all azarovo-hyper errors."""


class BackendUnavailableError(HyperError):
    """The libvirt Python binding is not installed on this machine."""


class ConnectionFailedError(HyperError):
    """The hypervisor connection could not be opened or was lost."""


class DomainNotFoundError(HyperError):
    """The virtual machine (or one of its snapshots) does not exist."""


class VMStateError(HyperError):
    """The operation is not allowed in the current state of the machine."""


class UnsupportedOperationError(HyperError):
    """The hypervisor driver does not support the requested operation."""


class ConfigurationError(HyperError, ValueError):
    """A machine specification or an argument is invalid."""


class OperationTimeoutError(HyperError, TimeoutError):
    """The machine did not reach the expected state in time."""


class VMClosedError(HyperError):
    """The machine object was closed or deleted and cannot be used any more."""


class DiskError(HyperError):
    """A disk image could not be created or removed."""


class InsufficientResourcesError(HyperError):
    """The host lacks the RAM, CPU or disk space the operation needs.

    ``shortfalls`` lists each missing resource with the requested and the
    available amount. Nothing is created or changed when this is raised.
    """

    def __init__(self, message: str, shortfalls: tuple[object, ...] = ()) -> None:
        super().__init__(message)
        self.shortfalls = shortfalls

    @property
    def resources(self) -> set[str]:
        return {getattr(s, "resource", "unknown") for s in self.shortfalls}


class BackendError(HyperError):
    """Any other error reported by the hypervisor backend."""
