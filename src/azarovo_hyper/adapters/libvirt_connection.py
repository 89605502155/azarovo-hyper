"""libvirt implementation of the :class:`~azarovo_hyper.ports.Connection` port.

libvirt connections are thread-safe and the binding releases the GIL during
every call, so one connection is shared by all machines on the same URI.
"""

from __future__ import annotations

import threading
from typing import Any

from azarovo_hyper.adapters.errors import is_libvirt_error, libvirt_errors
from azarovo_hyper.adapters.libvirt_domain import LibvirtDomain
from azarovo_hyper.adapters.loader import load_libvirt
from azarovo_hyper.decorators import decorate_public_methods
from azarovo_hyper.domain.resources import HostUsage
from azarovo_hyper.domain.stats import HostInfo
from azarovo_hyper.errors import ConnectionFailedError


@decorate_public_methods(libvirt_errors)
class LibvirtConnection:
    """An open ``virConnect`` handle."""

    def __init__(self, uri: str) -> None:
        libvirt = load_libvirt()
        try:
            conn = libvirt.open(uri)
        except Exception as exc:
            if not is_libvirt_error(exc):
                raise
            raise ConnectionFailedError(
                f"cannot connect to {uri}: {exc}\n"
                "Run `uv run azarovo-hyper doctor` to see what is missing."
            ) from exc
        if conn is None:  # pragma: no cover - old bindings returned None
            raise ConnectionFailedError(f"cannot connect to {uri}")
        self._uri = uri
        self._conn: Any = conn
        self._close_lock = threading.Lock()

    @classmethod
    def open(cls, uri: str) -> LibvirtConnection:
        return cls(uri)

    @property
    def uri(self) -> str:
        return self._uri

    @property
    def raw(self) -> Any:
        """The underlying ``libvirt.virConnect`` for anything not wrapped here."""
        return self._conn

    def define(self, xml: str) -> LibvirtDomain:
        return LibvirtDomain(self._conn.defineXML(xml), self._conn)

    def lookup(self, name: str) -> LibvirtDomain:
        return LibvirtDomain(self._conn.lookupByName(name), self._conn)

    def names(self) -> list[str]:
        return sorted(str(d.name()) for d in self._conn.listAllDomains(0))

    def host_info(self) -> HostInfo:
        libvirt = load_libvirt()
        _model, total_mib, cpus, *_rest = self._conn.getInfo()
        cached = buffers = 0.0
        try:
            stats = self._conn.getMemoryStats(libvirt.VIR_NODE_MEMORY_STATS_ALL_CELLS, 0)
            free_mib = stats.get("free", 0) / 1024
            cached = stats.get("cached", 0) / 1024
            buffers = stats.get("buffers", 0) / 1024
            total_mib = stats.get("total", total_mib * 1024) / 1024
        except Exception as exc:
            if not is_libvirt_error(exc):
                raise
            free_mib = self._conn.getFreeMemory() / 1024**2
        return HostInfo(
            uri=self._uri,
            hostname=str(self._conn.getHostname()),
            hypervisor=str(self._conn.getType()),
            cpus=int(cpus),
            total_mib=float(total_mib),
            free_mib=float(free_mib),
            cached_mib=float(cached),
            buffers_mib=float(buffers),
        )

    def usage(self) -> HostUsage:
        """Host capacity plus what running guests use or may still balloon up to."""
        libvirt = load_libvirt()
        info = self.host_info()
        vcpus, unbacked = 0, 0.0
        for dom in self._conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE):
            try:
                _state, ceiling_kib, _memory, count, _time = dom.info()
                rss = dom.memoryStats().get("rss")
            except Exception as exc:
                if not is_libvirt_error(exc):
                    raise
                continue
            vcpus += count
            unbacked += max(ceiling_kib - (rss or 0), 0) / 1024
        return HostUsage(
            hostname=info.hostname,
            total_mib=info.total_mib,
            available_mib=info.available_mib,
            cpus=info.cpus,
            guest_vcpus=vcpus,
            guest_unbacked_mib=unbacked,
        )

    def is_alive(self) -> bool:
        with self._close_lock:
            return self._conn is not None and bool(self._conn.isAlive())

    def close(self) -> None:
        with self._close_lock:
            conn, self._conn = self._conn, None
        if conn is not None:
            conn.close()
