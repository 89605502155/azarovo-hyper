"""Read-only snapshots of guest and host metrics."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from azarovo_hyper.domain.state import VMState

#: Balloon fields that describe "free inside the guest", best first. ``usable``
#: is the guest's MemAvailable, ``unused`` its MemFree.
FREE_FIELDS = ("usable", "unused")


def _mib(stats: Mapping[str, int], key: str) -> float | None:
    value = stats.get(key)
    return None if value is None else value / 1024


@dataclass(frozen=True, slots=True)
class MemoryStats:
    """Balloon statistics of one guest, in MiB."""

    actual_mib: float
    available_mib: float | None = None
    usable_mib: float | None = None
    unused_mib: float | None = None
    rss_mib: float | None = None
    raw: Mapping[str, int] = field(default_factory=dict)

    @classmethod
    def from_libvirt(cls, stats: Mapping[str, int]) -> MemoryStats:
        return cls(
            actual_mib=(stats.get("actual") or 0) / 1024,
            available_mib=_mib(stats, "available"),
            usable_mib=_mib(stats, "usable"),
            unused_mib=_mib(stats, "unused"),
            rss_mib=_mib(stats, "rss"),
            raw=MappingProxyType(dict(stats)),
        )

    @property
    def guest_reports(self) -> bool:
        """``True`` once the guest balloon driver sends its own statistics."""
        return self.usable_mib is not None or self.unused_mib is not None

    @property
    def free_mib(self) -> float:
        """Free memory as the guest sees it; falls back to ``actual - rss``."""
        for value in (self.usable_mib, self.unused_mib):
            if value is not None:
                return min(max(value, 0.0), self.actual_mib)
        if self.rss_mib is None:
            return 0.0
        return min(max(self.actual_mib - self.rss_mib, 0.0), self.actual_mib)

    @property
    def used_mib(self) -> float:
        return max(self.actual_mib - self.free_mib, 0.0)

    @property
    def usage_percent(self) -> float:
        return self.used_mib / self.actual_mib * 100 if self.actual_mib else 0.0


@dataclass(frozen=True, slots=True)
class DiskStats:
    """Cumulative I/O counters of one block device."""

    device: str
    read_requests: int
    read_bytes: int
    write_requests: int
    written_bytes: int
    errors: int = 0

    @property
    def total_bytes(self) -> int:
        return self.read_bytes + self.written_bytes


@dataclass(frozen=True, slots=True)
class InterfaceStats:
    """Cumulative traffic counters of one network interface."""

    device: str
    rx_bytes: int
    rx_packets: int
    tx_bytes: int
    tx_packets: int


@dataclass(frozen=True, slots=True)
class GuestMetrics:
    """Everything the adaptive controller samples on one tick."""

    name: str
    state: VMState
    cpu_percent: float
    vcpus: int
    memory: MemoryStats | None
    disks: Mapping[str, DiskStats] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HostInfo:
    """Host resources as reported by the hypervisor connection."""

    uri: str
    hostname: str
    hypervisor: str
    cpus: int
    total_mib: float
    free_mib: float
    cached_mib: float = 0.0
    buffers_mib: float = 0.0

    @property
    def available_mib(self) -> float:
        return self.free_mib + self.cached_mib + self.buffers_mib

    @property
    def used_mib(self) -> float:
        return max(self.total_mib - self.available_mib, 0.0)

    @property
    def usage_percent(self) -> float:
        return self.used_mib / self.total_mib * 100 if self.total_mib else 0.0
