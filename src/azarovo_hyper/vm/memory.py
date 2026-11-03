"""Guest memory: balloon resizing, memory hot-plug and balloon statistics.

* ``set``/``grow``/``shrink`` move the balloon inside the current maximum;
* ``plug``/``unplug`` change the maximum itself (DIMM modules on KVM, the
  live memory ceiling on Xen) within ``max_memory`` of the spec.
"""

from __future__ import annotations

from azarovo_hyper.decorators import guarded, requires_running, validated
from azarovo_hyper.domain.numbers import NonNegativeInt
from azarovo_hyper.domain.resources import Demand
from azarovo_hyper.domain.sizes import Size, to_mib
from azarovo_hyper.domain.stats import MemoryStats
from azarovo_hyper.domain.xml_view import DomainXml
from azarovo_hyper.errors import ConfigurationError, UnsupportedOperationError, VMStateError
from azarovo_hyper.vm.session import SessionBound


class MemoryController(SessionBound):
    """``vm.memory``"""

    __slots__ = ()

    # ── reading ─────────────────────────────────────────────────────────────
    @property
    @guarded
    def current_mib(self) -> float:
        """Balloon size of a running guest, the configured size otherwise."""
        domain = self._session.domain()
        if domain.state().is_active:
            actual = domain.memory_stats().get("actual")
            if actual:
                return actual / 1024
        return self._session.spec.current_memory_mib

    @property
    @guarded
    def maximum_mib(self) -> float:
        """Current ceiling for the balloon (boot memory plus hot-plugged memory)."""
        return self._session.domain().max_memory_kib() / 1024

    @property
    def minimum_mib(self) -> int:
        return self._session.spec.min_memory_mib

    @property
    def limit_mib(self) -> int:
        """Ceiling for hot-plug: ``max_memory`` of the spec."""
        return self._session.spec.max_memory_mib

    @guarded
    @requires_running
    def stats(self) -> MemoryStats:
        return MemoryStats.from_libvirt(self._session.domain().memory_stats())

    @guarded
    def dimms(self) -> list[int]:
        """Sizes (MiB) of hot-plugged DIMM modules."""
        return DomainXml(self._session.domain().xml()).dimms()

    # ── balloon ─────────────────────────────────────────────────────────────
    @guarded
    @requires_running
    def set(self, size: Size, *, persist: bool = False) -> int:
        """Resize the balloon; the target is clamped to ``[min_memory, maximum]``.

        Returns the size actually requested from the hypervisor, in MiB.
        """
        target = to_mib(size)
        ceiling = int(self.maximum_mib)
        applied = max(self.minimum_mib, min(target, ceiling))
        self._session.domain().set_memory(applied * 1024, live=True, config=persist)
        return applied

    @guarded
    def grow(self, by: Size = "128M") -> int:
        return self.set(int(self.current_mib) + to_mib(by))

    @guarded
    def shrink(self, by: Size = "128M") -> int:
        return self.set(max(int(self.current_mib) - to_mib(by), 0))

    @guarded
    @validated(seconds=NonNegativeInt)
    def set_stats_period(self, seconds: int = 1) -> None:
        """How often the guest balloon driver refreshes ``stats()``."""
        domain = self._session.domain()
        live = domain.state().is_active
        domain.set_stats_period(seconds, live=live, config=not live)

    # ── hot-plug ────────────────────────────────────────────────────────────
    def _check_hotplug(self) -> None:
        caps = self._session.driver.capabilities
        if not (caps.dimm_hotplug or caps.live_max_memory):
            raise UnsupportedOperationError(f"{self._session.driver.name}: no memory hot-plug")
        if caps.dimm_hotplug and not self._session.spec.memory_hotplug:
            raise UnsupportedOperationError(
                f"{self._session.name}: memory hot-plug is off (max_memory == memory "
                "or memory_slots == 0)"
            )

    @guarded
    @requires_running
    def plug(self, size: Size | None = None, *, persist: bool = False) -> float:
        """Add memory to the running guest; returns the new maximum in MiB."""
        self._check_hotplug()
        session = self._session
        amount = to_mib(size) if size is not None else session.spec.dimm_mib
        if amount <= 0:
            raise ConfigurationError("hot-plug size must be positive")
        if self.maximum_mib + amount > self.limit_mib:
            raise ConfigurationError(
                f"{session.name}: {self.maximum_mib:.0f} + {amount} MiB exceeds "
                f"max_memory {self.limit_mib} MiB"
            )
        slots = session.spec.memory_slots
        if session.driver.capabilities.dimm_hotplug and len(self.dimms()) >= slots:
            raise VMStateError(f"{session.name}: all {slots} slots used")
        with session.reserve(Demand(memory_mib=amount)):
            session.driver.plug_memory(session.domain(), amount, config=persist)
        return self.maximum_mib

    @guarded
    @requires_running
    def unplug(self, size: Size | None = None, *, persist: bool = False) -> float:
        """Remove hot-plugged memory (the guest must release it on KVM)."""
        self._check_hotplug()
        session = self._session
        if session.driver.capabilities.dimm_hotplug:
            modules = self.dimms()
            if not modules:
                raise VMStateError(f"{session.name}: no hot-plugged DIMM to remove")
            amount = to_mib(size) if size is not None else modules[-1]
            if amount not in modules:
                raise ConfigurationError(f"{session.name}: no {amount} MiB DIMM plugged")
        else:
            amount = to_mib(size) if size is not None else session.spec.dimm_mib
            if self.maximum_mib - amount < session.spec.memory_mib:
                raise ConfigurationError(f"{session.name}: cannot go below boot memory")
        session.driver.unplug_memory(session.domain(), amount, config=persist)
        return self.maximum_mib
