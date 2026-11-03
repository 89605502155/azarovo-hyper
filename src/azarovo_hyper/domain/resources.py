"""Host capacity checks: how much RAM, CPU and disk a new demand may take.

Guest memory is counted at its ceiling (boot memory plus hot-plugged memory):
the balloon can grow a guest up to it at any moment, so ``memory.set()`` never
needs a check, while ``start()`` and memory hot-plug do. Pure arithmetic; the
atomic check-and-act lives in :mod:`azarovo_hyper.resources`.
"""

from __future__ import annotations

from dataclasses import dataclass

from azarovo_hyper.domain.numbers import Ratio
from azarovo_hyper.domain.sizes import Size, to_mib
from azarovo_hyper.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class ResourcePolicy:
    """How strictly a machine's demands are checked against the host.

    ``memory_overcommit=1.0`` never promises more RAM than the host can give;
    ``cpu_overcommit=4.0`` allows four running vCPUs per host CPU in total.
    A single machine never gets more vCPUs than the host has.
    """

    check_resources: bool = True
    memory_overcommit: float = 1.0
    cpu_overcommit: float = 4.0
    host_memory_reserve: Size = "512M"
    host_disk_reserve: Size = "1G"

    def __post_init__(self) -> None:
        for name in ("memory_overcommit", "cpu_overcommit"):
            object.__setattr__(self, name, Ratio(getattr(self, name), name))
        for name in ("host_memory_reserve", "host_disk_reserve"):
            try:
                to_mib(getattr(self, name))
            except ConfigurationError as exc:
                raise ConfigurationError(f"{name}: {exc}") from None


@dataclass(frozen=True, slots=True)
class Demand:
    """What one operation is about to take from the host."""

    memory_mib: int = 0
    vcpus: int = 0
    disk_mib: int = 0
    vm_vcpus: int = 0
    """vCPUs the machine will have afterwards (checked against host CPUs)."""

    def __bool__(self) -> bool:
        return bool(self.memory_mib or self.vcpus or self.disk_mib or self.vm_vcpus)

    def __add__(self, other: Demand) -> Demand:
        return Demand(
            self.memory_mib + other.memory_mib,
            self.vcpus + other.vcpus,
            self.disk_mib + other.disk_mib,
            max(self.vm_vcpus, other.vm_vcpus),
        )


@dataclass(frozen=True, slots=True)
class HostUsage:
    """Host resources and what running guests already hold or were promised."""

    hostname: str
    total_mib: float
    available_mib: float
    cpus: int
    guest_vcpus: int = 0
    guest_unbacked_mib: float = 0.0
    """Memory running guests may still take: their ceiling minus what they use."""


@dataclass(frozen=True, slots=True)
class Shortfall:
    resource: str
    requested: float
    available: float

    def __str__(self) -> str:
        unit = "" if self.resource == "cpu" else " MiB"
        return (
            f"{self.resource}: requested {self.requested:.0f}{unit}, "
            f"available {max(self.available, 0):.0f}{unit}"
        )


def memory_headroom(usage: HostUsage, policy: ResourcePolicy) -> float:
    reserve = to_mib(policy.host_memory_reserve)
    spare = usage.available_mib - reserve - usage.guest_unbacked_mib
    return spare + (policy.memory_overcommit - 1) * usage.total_mib


def cpu_headroom(usage: HostUsage, policy: ResourcePolicy) -> float:
    return usage.cpus * policy.cpu_overcommit - usage.guest_vcpus


def disk_headroom(free_mib: float, policy: ResourcePolicy) -> float:
    return free_mib - to_mib(policy.host_disk_reserve)


def shortfalls(
    demand: Demand,
    *,
    policy: ResourcePolicy,
    usage: HostUsage | None,
    free_disk_mib: float | None,
) -> list[Shortfall]:
    """Every resource the demand cannot get; an empty list means it fits."""
    found: list[Shortfall] = []
    if usage is not None:
        if demand.vm_vcpus > usage.cpus:
            found.append(Shortfall("cpu", demand.vm_vcpus, usage.cpus))
        if demand.vcpus and demand.vcpus > (room := cpu_headroom(usage, policy)):
            found.append(Shortfall("cpu", demand.vcpus, room))
        room_mem = memory_headroom(usage, policy)
        if demand.memory_mib and demand.memory_mib > room_mem:
            found.append(Shortfall("memory", demand.memory_mib, room_mem))
    if free_disk_mib is not None and demand.disk_mib:
        room_disk = disk_headroom(free_disk_mib, policy)
        if demand.disk_mib > room_disk:
            found.append(Shortfall("disk", demand.disk_mib, room_disk))
    return found
