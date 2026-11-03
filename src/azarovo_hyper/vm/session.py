"""Runtime state of one machine object and the resources it holds.

The session owns the connection lease, the cached domain handle, viewer
processes and the CPU sampler. It never references the
:class:`~azarovo_hyper.vm.machine.VirtualMachine` itself, so dropping the last
reference to a machine collects it at once and its finalizer releases all of
the above.
"""

from __future__ import annotations

import logging
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from azarovo_hyper.adapters.pool import ConnectionPool, Lease
from azarovo_hyper.domain.sampler import CpuSampler
from azarovo_hyper.domain.spec import VMSpec
from azarovo_hyper.domain.state import VMState
from azarovo_hyper.domain.xml_view import DomainXml
from azarovo_hyper.drivers.base import HypervisorDriver
from azarovo_hyper.errors import (
    DomainNotFoundError,
    HyperError,
    OperationTimeoutError,
    VMClosedError,
    VMStateError,
)
from azarovo_hyper.ports.backend import Connection, DiskTool, Domain

logger = logging.getLogger(__name__)


class VMSession:
    """Everything a machine needs at runtime."""

    def __init__(
        self,
        *,
        spec: VMSpec,
        driver: HypervisorDriver,
        uri: str,
        pool: ConnectionPool,
        disk_tool: DiskTool,
    ) -> None:
        self.spec = driver.resolve(spec)
        self.driver = driver
        self.uri = uri
        self.pool = pool
        self.disk_tool = disk_tool
        self.disk_path = self.spec.disk_path(driver.default_images_dir(uri))
        self.images_dir = self.disk_path.parent
        self.owns_disk = False
        self.owned_disks: set[Path] = set()
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.interrupt = threading.Event()
        self.cpu_sampler = CpuSampler()
        self.viewers: list[subprocess.Popen[bytes]] = []
        self._cache_lock = threading.RLock()
        self._lease: Lease | None = None
        self._domain: Domain | None = None

    @property
    def name(self) -> str:
        return self.spec.name

    # ── connection and domain handle ────────────────────────────────────────
    def connection(self) -> Connection:
        if self.closed.is_set():
            raise VMClosedError(f"{self.name}: the machine object is closed")
        with self._cache_lock:
            if self._lease is None or self._lease.released:
                self._lease = self.pool.acquire(self.uri)
            return self._lease.connection

    def domain(self) -> Domain:
        with self._cache_lock:
            if self._domain is None:
                self._domain = self.connection().lookup(self.name)
            return self._domain

    def find_domain(self) -> Domain | None:
        try:
            return self.domain()
        except DomainNotFoundError:
            self.forget_domain()
            return None

    def remember(self, domain: Domain) -> None:
        with self._cache_lock:
            self._domain = domain

    def adopt(self, domain: Domain) -> None:
        """Take over a domain that already exists on the hypervisor."""
        self.remember(domain)
        self.owns_disk = DomainXml(domain.xml(inactive=True)).owns_disk()

    def forget_domain(self) -> None:
        with self._cache_lock:
            self._domain = None

    def state(self) -> VMState:
        domain = self.find_domain()
        if domain is None:
            return VMState.UNDEFINED
        try:
            return domain.state()
        except DomainNotFoundError:
            self.forget_domain()
            return VMState.UNDEFINED

    # ── waiting ─────────────────────────────────────────────────────────────
    def wait_until(
        self, condition: Callable[[], bool], *, timeout: float, what: str, interval: float = 0.25
    ) -> None:
        """Poll ``condition``; closing the machine interrupts the wait."""
        deadline = time.monotonic() + timeout
        while not condition():
            left = deadline - time.monotonic()
            if left <= 0:
                raise OperationTimeoutError(f"{self.name}: not {what} after {timeout:g} s")
            if self.interrupt.wait(min(interval, left)):
                raise VMClosedError(f"{self.name}: closed while waiting to be {what}")

    # ── cleanup ─────────────────────────────────────────────────────────────
    def close_viewers(self) -> None:
        viewers, self.viewers = self.viewers, []
        for process in viewers:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

    def release(self) -> None:
        """Drop the connection lease, cached handle, viewers and CPU history.

        Called after the guest is switched off and when the object is closed;
        the next call that needs the hypervisor leases a connection again.
        """
        self.close_viewers()
        self.cpu_sampler.reset()
        with self._cache_lock:
            lease, self._lease, self._domain = self._lease, None, None
        if lease is not None:
            lease.release()

    def teardown(self, *, remove_disk: bool | None = None) -> None:
        """Power off, undefine and remove the disks this library created."""
        domain = self.find_domain()
        if domain is not None:
            if domain.state().is_active:
                try:
                    domain.destroy()
                except VMStateError:
                    logger.debug("%s: already off", self.name)
            domain.undefine()
            self.forget_domain()
        if remove_disk if remove_disk is not None else self.owns_disk:
            self.disk_tool.remove(self.disk_path)
        for path in sorted(self.owned_disks):
            self.disk_tool.remove(path)
        self.owned_disks.clear()

    def release_if_idle(self) -> None:
        """Release resources of a stopped machine unless another call is using it."""
        if self.lock.acquire(blocking=False):
            try:
                if not self.state().is_active:
                    self.release()
            finally:
                self.lock.release()

    def finalize(self) -> None:
        """Last cleanup: runs from ``close()``, garbage collection or exit."""
        self.interrupt.set()
        with self.lock:
            try:
                if self.spec.ephemeral and not self.closed.is_set():
                    self.teardown()
            except HyperError:
                logger.warning("%s: ephemeral cleanup failed", self.name, exc_info=True)
            finally:
                self.closed.set()
                self.release()


class SessionBound:
    """Base of every object that works on behalf of one session."""

    __slots__ = ("_session",)

    def __init__(self, session: VMSession) -> None:
        self._session = session
