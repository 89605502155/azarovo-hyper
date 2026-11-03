"""Guest vCPUs: hot-plug and load sampling."""

from __future__ import annotations

from azarovo_hyper.decorators import guarded, requires_capability, requires_running, validated
from azarovo_hyper.domain.numbers import PositiveInt
from azarovo_hyper.domain.resources import Demand
from azarovo_hyper.errors import ConfigurationError
from azarovo_hyper.vm.session import SessionBound


class CpuController(SessionBound):
    """``vm.cpu``"""

    __slots__ = ()

    @property
    @guarded
    def count(self) -> int:
        """vCPUs the guest has right now (configured count when it is off)."""
        domain = self._session.find_domain()
        return self._session.spec.vcpus if domain is None else domain.vcpus()

    @property
    def maximum(self) -> int:
        """Upper bound for hot-plug (``max_vcpus`` of the spec)."""
        return self._session.spec.effective_max_vcpus

    @guarded
    @requires_capability("vcpu_hotplug")
    @validated(count=PositiveInt)
    def set(self, count: int, *, persist: bool = False) -> int:
        """Set the number of vCPUs.

        On a running guest the change is live (and saved too if ``persist``);
        on a stopped guest it is written to the configuration.
        """
        if not 1 <= count <= self.maximum:
            raise ConfigurationError(f"vcpus must be within 1..{self.maximum}, got {count}")
        domain = self._session.domain()
        live = domain.state().is_active
        added = max(count - domain.vcpus(), 0) if live else 0
        with self._session.reserve(Demand(vcpus=added, vm_vcpus=count)):
            domain.set_vcpus(count, live=live, config=persist or not live)
        return count

    @guarded
    @validated(count=PositiveInt)
    def plug(self, count: int = 1) -> int:
        return self.set(self.count + count)

    @guarded
    @validated(count=PositiveInt)
    def unplug(self, count: int = 1) -> int:
        return self.set(self.count - count)

    @guarded
    @requires_running
    def time_ns(self) -> int:
        """CPU time consumed by the guest since it started."""
        return self._session.domain().cpu_time_ns()

    @guarded
    @requires_running
    def usage(self) -> float:
        """Average load of all vCPUs since the previous call, 0..100 %.

        The first call after start only records a baseline and returns 0.
        """
        domain = self._session.domain()
        return self._session.cpu_sampler.sample(domain.cpu_time_ns(), domain.vcpus())
