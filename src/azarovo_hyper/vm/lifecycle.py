"""Power and lifecycle operations; changing methods return ``self`` for chaining."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from azarovo_hyper.decorators import chainable, guarded, requires_running, validated
from azarovo_hyper.domain.numbers import NonNegativeFloat
from azarovo_hyper.domain.resources import Demand
from azarovo_hyper.domain.state import VMState
from azarovo_hyper.errors import InsufficientResourcesError, OperationTimeoutError, VMStateError

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Self

    from azarovo_hyper.vm.session import VMSession

logger = logging.getLogger(__name__)


class LifecycleMixin:
    """Define, start, stop, pause and delete a machine."""

    _session: VMSession
    close: Callable[[], None]

    @validated(timeout=NonNegativeFloat)
    def wait_for(self, *states: VMState, timeout: float = 60.0) -> Self:
        """Block until the machine is in one of ``states`` (default: running)."""
        wanted = states or (VMState.RUNNING,)
        names = "/".join(str(s) for s in wanted)
        session = self._session
        session.wait_until(lambda: session.state() in wanted, timeout=timeout, what=names)
        return self

    # ── define and start ────────────────────────────────────────────────────
    @chainable
    @guarded
    def define(self) -> None:
        """Create the disk and define the domain; adopt it if it already exists."""
        session = self._session
        existing = session.find_domain()
        if existing is not None:
            session.adopt(existing)
            return
        spec = session.spec
        disk = Demand(disk_mib=0 if session.disk_path.exists() else spec.disk_size_mib)
        with session.reserve(disk, disk_dir=session.disk_path.parent):
            created = session.disk_tool.create(
                session.disk_path, spec.disk_size_mib, spec.disk_format, spec.disk_preallocation
            )
        session.owns_disk = created
        xml = session.driver.render_domain(
            spec, disk_path=session.disk_path, owns_disk=created, uri=session.uri
        )
        try:
            connection = session.connection()
            domain = session.driver.finalize_definition(connection, connection.define(xml), spec)
        except BaseException:
            if created:
                session.disk_tool.remove(session.disk_path)
            raise
        session.remember(domain)
        if spec.autostart:
            domain.set_autostart(True)
        logger.info("%s: defined on %s", session.name, session.uri)

    @chainable
    @guarded
    @validated(timeout=NonNegativeFloat)
    def start(self, *, wait: bool = True, timeout: float = 60.0) -> None:
        """Define if needed and power on (or resume); RAM/vCPUs are checked atomically.

        Concurrent starts never overcommit the host; a refusal leaves nothing behind.
        """
        session = self._session
        existing = session.find_domain()
        if existing is not None and existing.state() is VMState.PAUSED:
            existing.resume()
        elif existing is None or not existing.state().is_active:
            try:
                self._boot(fresh=existing is None)
            except InsufficientResourcesError:
                if session.find_domain() is None:
                    session.release()
                raise
        if wait:
            self.wait_for(VMState.RUNNING, timeout=timeout)

    def _boot(self, *, fresh: bool) -> None:
        session = self._session
        if fresh:
            spec = session.spec
            with session.reserve(Demand(spec.memory_mib, spec.vcpus, vm_vcpus=spec.vcpus)):
                pass
        self.define()
        domain = session.domain()
        count = domain.vcpus()
        demand = Demand(domain.max_memory_kib() // 1024, count, vm_vcpus=count)
        session.cpu_sampler.reset()
        try:
            with session.reserve(demand):
                domain.start()
        except InsufficientResourcesError:
            if fresh:
                session.teardown()
            raise
        logger.info("%s: started", session.name)

    # ── stop ────────────────────────────────────────────────────────────────
    @chainable
    @guarded
    @validated(timeout=NonNegativeFloat)
    def shutdown(self, *, timeout: float = 120.0, force: bool = True) -> None:
        """ACPI power-off; after ``timeout`` pull the plug if ``force``."""
        session = self._session
        domain = session.find_domain()
        if domain is not None and domain.state().is_active:
            try:
                domain.shutdown()
                session.wait_until(
                    lambda: not session.state().is_active, timeout=timeout, what="shut off"
                )
            except OperationTimeoutError:
                if not force:
                    raise
                logger.warning("%s: guest ignored shutdown, powering off", session.name)
                self._power_off()
            except VMStateError:
                if force:
                    self._power_off()
        session.release()

    @chainable
    @guarded
    def stop(self) -> None:
        """Immediate power-off (like pulling the cable); the disk is kept."""
        self._power_off()
        self._session.release()

    def _power_off(self) -> None:
        domain = self._session.find_domain()
        if domain is not None and domain.state().is_active:
            try:
                domain.destroy()
            except VMStateError:
                logger.debug("%s: already off", self._session.name)

    @chainable
    @guarded
    @validated(timeout=NonNegativeFloat)
    def restart(self, *, timeout: float = 120.0) -> None:
        """Clean shutdown followed by a fresh start."""
        self.shutdown(timeout=timeout)
        self.start()

    @chainable
    @guarded
    @requires_running
    def reboot(self) -> None:
        """Ask the guest to reboot itself."""
        self._session.domain().reboot()

    @chainable
    @guarded
    @requires_running
    def reset(self) -> None:
        """Hardware reset without a clean shutdown."""
        self._session.cpu_sampler.reset()
        self._session.domain().reset()

    @chainable
    @guarded
    @requires_running
    def suspend(self) -> None:
        """Pause the vCPUs; memory stays allocated."""
        self._session.domain().suspend()

    @chainable
    @guarded
    def resume(self) -> None:
        domain = self._session.domain()
        if domain.state() is VMState.PAUSED:
            domain.resume()

    # ── delete ──────────────────────────────────────────────────────────────
    @guarded
    def delete(self, *, remove_disk: bool | None = None) -> None:
        """Power off, undefine, delete disks it created and close this object.

        ``remove_disk=None`` removes the main disk only if the library created it.
        """
        self._session.teardown(remove_disk=remove_disk)
        logger.info("%s: deleted", self._session.name)
        self.close()
