"""The :class:`VirtualMachine` facade returned by ``hyper().kvm(...)``."""

from __future__ import annotations

import weakref
from typing import TYPE_CHECKING

from azarovo_hyper.decorators import guarded
from azarovo_hyper.domain.state import VMState
from azarovo_hyper.domain.stats import GuestMetrics, MemoryStats
from azarovo_hyper.errors import HyperError
from azarovo_hyper.vm.cpu import CpuController
from azarovo_hyper.vm.display import DisplayController
from azarovo_hyper.vm.lifecycle import LifecycleMixin
from azarovo_hyper.vm.memory import MemoryController
from azarovo_hyper.vm.network import NetworkController
from azarovo_hyper.vm.session import VMSession
from azarovo_hyper.vm.snapshots import SnapshotController
from azarovo_hyper.vm.storage import StorageController

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Self

    from azarovo_hyper.domain.spec import VMSpec
    from azarovo_hyper.drivers.base import HypervisorDriver


class VirtualMachine(LifecycleMixin):
    """One virtual machine.

    Creating the object touches nothing on the host: the disk and the domain
    appear on the first ``define()`` or ``start()``.

    Resources are released automatically:

    * ``stop()``/``shutdown()`` drop the connection lease and viewer windows;
    * ``close()``, ``del vm`` or leaving a ``with`` block release everything
      the object holds, and with ``ephemeral=True`` also delete the machine;
    * ``delete()`` removes the domain and the disks the library created.
    """

    def __init__(self, session: VMSession) -> None:
        self._session = session
        self.memory = MemoryController(session)
        self.cpu = CpuController(session)
        self.storage = StorageController(session)
        self.snapshots = SnapshotController(session)
        self.display = DisplayController(session)
        self.network = NetworkController(session)
        self._finalizer = weakref.finalize(self, session.finalize)

    # ── identity ────────────────────────────────────────────────────────────
    @property
    def name(self) -> str:
        return self._session.name

    @property
    def spec(self) -> VMSpec:
        """Specification with the driver defaults filled in."""
        return self._session.spec

    @property
    def driver(self) -> HypervisorDriver:
        return self._session.driver

    @property
    def hypervisor(self) -> str:
        return self._session.driver.name

    @property
    def uri(self) -> str:
        return self._session.uri

    @property
    def disk_path(self) -> Path:
        return self._session.disk_path

    @property
    def closed(self) -> bool:
        return self._session.closed.is_set()

    # ── state ───────────────────────────────────────────────────────────────
    @property
    def state(self) -> VMState:
        """Current state; ``UNDEFINED`` until the machine is defined."""
        session = self._session
        if session.closed.is_set():
            return VMState.UNDEFINED
        current = session.state()
        if not current.is_active:
            session.release_if_idle()
        return current

    @property
    def is_running(self) -> bool:
        return self.state is VMState.RUNNING

    @property
    def exists(self) -> bool:
        return self.state.is_defined

    @property
    @guarded
    def uuid(self) -> str:
        return self._session.domain().uuid

    @property
    @guarded
    def xml(self) -> str:
        """Live domain XML (as libvirt expanded it)."""
        return self._session.domain().xml()

    @property
    @guarded
    def autostart(self) -> bool:
        return self._session.domain().autostart()

    @autostart.setter
    @guarded
    def autostart(self, enabled: bool) -> None:
        self._session.domain().set_autostart(enabled)

    # ── metrics ─────────────────────────────────────────────────────────────
    @guarded
    def metrics(self) -> GuestMetrics:
        """One consistent sample of CPU, memory and disk counters (zeros when stopped)."""
        state = self._session.state()
        running = state is VMState.RUNNING
        memory: MemoryStats | None = None
        disks = {}
        cpu = 0.0
        if running:
            cpu = self.cpu.usage()
            memory = self.memory.stats()
            try:
                disks = self.storage.stats()
            except HyperError:
                disks = {}
        vcpus = self.cpu.count if state.is_defined else self.spec.vcpus
        return GuestMetrics(
            name=self.name,
            state=state,
            cpu_percent=cpu,
            vcpus=vcpus,
            memory=memory,
            disks=disks,
        )

    # ── resources ───────────────────────────────────────────────────────────
    def close(self) -> None:
        """Release everything this object holds; the machine keeps running.

        With ``ephemeral=True`` the machine is deleted instead. Idempotent.
        """
        self._finalizer()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"<VirtualMachine {self.name!r} {self.hypervisor} {self.uri} {self.state}>"
