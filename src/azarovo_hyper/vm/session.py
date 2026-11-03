"""Runtime state of one machine object and the resources it holds.

The session owns the connection lease, the cached domain handle, viewers and
the CPU sampler. It never references the machine object, so dropping the last
reference to a machine collects it at once and its finalizer releases them.
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path

from azarovo_hyper.adapters.pool import ConnectionPool, Lease
from azarovo_hyper.domain.resources import Demand
from azarovo_hyper.domain.sampler import CpuSampler
from azarovo_hyper.domain.spec import VMSpec
from azarovo_hyper.domain.state import VMState
from azarovo_hyper.domain.xml_view import DomainXml
from azarovo_hyper.drivers.base import HypervisorDriver
from azarovo_hyper.errors import (
    DomainNotFoundError,
    HyperError,
    VMClosedError,
    VMStateError,
)
from azarovo_hyper.ports.backend import Connection, DiskTool, Domain
from azarovo_hyper.resources.admission import Admission
from azarovo_hyper.runtime import keep_inherited, terminate, track_fork, wait_until

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
        admission: Admission,
    ) -> None:
        self.spec = driver.resolve(spec)
        self.driver = driver
        self.uri = uri
        self.pool = pool
        self.disk_tool = disk_tool
        self.admission = admission
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
        self.pid = os.getpid()
        track_fork(self)

    def _after_fork(self) -> None:
        """In a forked child: fresh locks, nothing of the parent's is reused."""
        keep_inherited(self._lease, self._domain)
        self.lock, self._cache_lock = threading.RLock(), threading.RLock()
        self._lease, self._domain, self.viewers = None, None, []
        self.cpu_sampler = CpuSampler()

    name = property(lambda self: self.spec.name)

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
            self.remember(None)
            return None

    def remember(self, domain: Domain | None) -> None:
        with self._cache_lock:
            self._domain = domain

    def adopt(self, domain: Domain) -> None:
        self.remember(domain)
        self.owns_disk = DomainXml(domain.xml(inactive=True)).owns_disk()

    def state(self) -> VMState:
        domain = self.find_domain()
        if domain is None:
            return VMState.UNDEFINED
        try:
            return domain.state()
        except DomainNotFoundError:
            self.remember(None)
            return VMState.UNDEFINED

    def reserve(self, demand: Demand, disk_dir: Path | None = None) -> AbstractContextManager[None]:
        """Atomically check and hold host capacity for ``demand`` (see resources)."""
        return self.admission.reserve(
            demand, policy=self.spec.resources, connection=self.connection, disk_dir=disk_dir
        )

    # ── waiting ─────────────────────────────────────────────────────────────
    def wait_until(self, condition: Callable[[], bool], *, timeout: float, what: str) -> None:
        """Poll ``condition``; closing the machine interrupts the wait."""
        wait_until(
            condition, timeout=timeout, interrupt=self.interrupt, what=f"{self.name}: {what}"
        )

    # ── cleanup ─────────────────────────────────────────────────────────────
    def close_viewers(self) -> None:
        viewers, self.viewers = self.viewers, []
        terminate(viewers)

    def release(self) -> None:
        """Drop the lease, cached handle, viewers and CPU history (re-leased on demand)."""
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
            self.owns_disk |= DomainXml(domain.xml(inactive=True)).owns_disk()
            if domain.state().is_active:
                try:
                    domain.destroy()
                except VMStateError:
                    logger.debug("%s: already off", self.name)
            domain.undefine()
            self.remember(None)
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
        """Last cleanup: runs from ``close()``, garbage collection or exit.

        Only the process that created the object may delete an ephemeral guest;
        a forked child merely drops its copy.
        """
        self.interrupt.set()
        with self.lock:
            try:
                owner = self.pid == os.getpid()
                if self.spec.ephemeral and owner and not self.closed.is_set():
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
