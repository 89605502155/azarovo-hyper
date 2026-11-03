"""Machine states, numbered exactly like libvirt's ``virDomainState``."""

from __future__ import annotations

import enum


class VMState(enum.Enum):
    """Lifecycle state of a virtual machine."""

    UNDEFINED = -1
    NOSTATE = 0
    RUNNING = 1
    BLOCKED = 2
    PAUSED = 3
    SHUTDOWN = 4
    SHUTOFF = 5
    CRASHED = 6
    PMSUSPENDED = 7

    @classmethod
    def from_code(cls, code: int) -> VMState:
        """Map a libvirt state code; unknown codes become ``NOSTATE``."""
        try:
            return cls(int(code))
        except ValueError:
            return cls.NOSTATE

    @property
    def is_active(self) -> bool:
        """The guest is loaded in memory (running, paused, shutting down...)."""
        return self in _ACTIVE

    @property
    def is_defined(self) -> bool:
        return self is not VMState.UNDEFINED

    def __str__(self) -> str:
        return self.name.lower()


_ACTIVE = frozenset(
    {
        VMState.RUNNING,
        VMState.BLOCKED,
        VMState.PAUSED,
        VMState.SHUTDOWN,
        VMState.PMSUSPENDED,
    }
)
