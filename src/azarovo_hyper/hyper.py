"""Entry point: ``hyper().kvm(...)`` and ``hyper().xen(...)``."""

from __future__ import annotations

import threading
import weakref
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Unpack

from azarovo_hyper import drivers
from azarovo_hyper.adapters.disk import QemuImg
from azarovo_hyper.adapters.pool import ConnectionPool, default_pool
from azarovo_hyper.config.presets import preset as preset_options
from azarovo_hyper.domain.options import VMOptions
from azarovo_hyper.domain.spec import VMSpec, spec_fields
from azarovo_hyper.domain.stats import HostInfo
from azarovo_hyper.domain.xml_view import DomainXml
from azarovo_hyper.errors import ConfigurationError
from azarovo_hyper.ports.backend import Connector, DiskTool
from azarovo_hyper.vm.machine import VirtualMachine
from azarovo_hyper.vm.session import VMSession

if TYPE_CHECKING:
    from typing import Self


class Hyper:
    """Factory and registry of machines.

    One ``Hyper`` can drive any number of machines on any hypervisors at the
    same time; they share one connection per URI and never lock each other.
    """

    def __init__(
        self,
        *,
        pool: ConnectionPool | None = None,
        connector: Connector | None = None,
        disk_tool: DiskTool | None = None,
    ) -> None:
        if pool is not None and connector is not None:
            raise ConfigurationError("pass either pool or connector, not both")
        self._pool = pool or (ConnectionPool(connector) if connector else default_pool())
        self._disk_tool = disk_tool or QemuImg()
        self._machines: weakref.WeakSet[VirtualMachine] = weakref.WeakSet()
        self._lock = threading.Lock()

    @property
    def pool(self) -> ConnectionPool:
        return self._pool

    @property
    def machines(self) -> list[VirtualMachine]:
        """Open machine objects created by this factory."""
        with self._lock:
            return [vm for vm in self._machines if not vm.closed]

    # ── machines ────────────────────────────────────────────────────────────
    def machine(
        self,
        hypervisor: str,
        name: str | None = None,
        /,
        *,
        uri: str | None = None,
        preset: str | None = None,
        spec: VMSpec | None = None,
        **options: Unpack[VMOptions],
    ) -> VirtualMachine:
        """A machine on any registered hypervisor. Nothing is created yet."""
        driver = drivers.get_driver(hypervisor)
        if name is not None:
            options["name"] = name
        if spec is None:
            unknown = set(options) - spec_fields()
            if unknown:
                raise ConfigurationError(f"unknown options: {', '.join(sorted(unknown))}")
            spec = VMSpec(**{**preset_options(preset), **options})
        elif options or preset:
            spec = spec.with_(**{**preset_options(preset), **options})
        session = VMSession(
            spec=spec,
            driver=driver,
            uri=uri or driver.default_uri(),
            pool=self._pool,
            disk_tool=self._disk_tool,
        )
        vm = VirtualMachine(session)
        with self._lock:
            self._machines.add(vm)
        return vm

    def kvm(
        self,
        name: str | None = None,
        /,
        *,
        uri: str | None = None,
        preset: str | None = None,
        spec: VMSpec | None = None,
        **options: Unpack[VMOptions],
    ) -> VirtualMachine:
        """A KVM machine. ``hyper().kvm().start()`` boots one with all defaults."""
        return self.machine("kvm", name, uri=uri, preset=preset, spec=spec, **options)

    def xen(
        self,
        name: str | None = None,
        /,
        *,
        uri: str | None = None,
        preset: str | None = None,
        spec: VMSpec | None = None,
        **options: Unpack[VMOptions],
    ) -> VirtualMachine:
        """A Xen HVM machine (``xen:///system``)."""
        return self.machine("xen", name, uri=uri, preset=preset, spec=spec, **options)

    def __getattr__(self, hypervisor: str) -> Callable[..., VirtualMachine]:
        """``hyper().<driver>(...)`` for drivers registered later on."""
        if hypervisor.startswith("_") or hypervisor not in drivers.driver_names():
            raise AttributeError(hypervisor)
        return lambda *args, **kwargs: self.machine(hypervisor, *args, **kwargs)

    def get(self, name: str, *, hypervisor: str = "kvm", uri: str | None = None) -> VirtualMachine:
        """Attach to a machine that already exists, keeping its memory/CPU limits."""
        driver = drivers.get_driver(hypervisor)
        uri = uri or driver.default_uri()
        with self._pool.acquire(uri) as connection:
            view = DomainXml(connection.lookup(name).xml(inactive=True))
        disks = view.disks()
        options: dict[str, Any] = view.spec_options()
        if disks:
            options["disk"] = next(iter(disks.values()))
        vm = self.machine(hypervisor, name, uri=uri, **options)
        return vm.define()

    # ── hypervisor-wide queries ─────────────────────────────────────────────
    def list(self, hypervisor: str = "kvm", *, uri: str | None = None) -> list[str]:
        """Names of all machines defined on the hypervisor."""
        with self._pool.acquire(uri or drivers.get_driver(hypervisor).default_uri()) as conn:
            return conn.names()

    def host(self, hypervisor: str = "kvm", *, uri: str | None = None) -> HostInfo:
        """CPU and memory of the host behind the connection."""
        with self._pool.acquire(uri or drivers.get_driver(hypervisor).default_uri()) as conn:
            return conn.host_info()

    # ── resources ───────────────────────────────────────────────────────────
    def close(self) -> None:
        """Close every machine object created here (machines keep running)."""
        for vm in self.machines:
            vm.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


def hyper(**kwargs: Any) -> Hyper:
    """Shortcut for :class:`Hyper`: ``kvm1 = hyper().kvm(memory="4G").start()``."""
    return Hyper(**kwargs)
