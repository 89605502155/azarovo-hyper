"""In-memory hypervisor: connections, a domain store and a disk tool."""

from __future__ import annotations

import threading
import time
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from azarovo_hyper.domain.stats import HostInfo
from azarovo_hyper.errors import ConnectionFailedError, DomainNotFoundError
from fakes.domain import FakeDomain


class FakeHypervisor:
    """Shared state behind every fake connection, like a libvirtd daemon."""

    def __init__(self, *, delay: float = 0.0) -> None:
        self.delay = delay
        self.guest_obeys_acpi = True
        self.fail_connect = False
        self.opened: Counter[str] = Counter()
        self.closed: Counter[str] = Counter()
        self.connections: list[FakeConnection] = []
        self._store: dict[str, dict[str, FakeDomain]] = {}
        self._lock = threading.Lock()
        self._running = 0
        self.max_parallel = 0

    def domains(self, uri: str) -> dict[str, FakeDomain]:
        with self._lock:
            return self._store.setdefault(uri, {})

    def busy(self, _op: str) -> None:
        """Simulate a slow hypervisor call and record how many overlap."""
        if not self.delay:
            return
        with self._lock:
            self._running += 1
            self.max_parallel = max(self.max_parallel, self._running)
        try:
            time.sleep(self.delay)
        finally:
            with self._lock:
                self._running -= 1

    def connect(self, uri: str) -> FakeConnection:
        if self.fail_connect:
            raise ConnectionFailedError(f"cannot connect to {uri}")
        connection = FakeConnection(self, uri)
        with self._lock:
            self.opened[uri] += 1
            self.connections.append(connection)
        return connection

    @property
    def open_connections(self) -> int:
        return sum(1 for c in self.connections if not c.is_closed)


class FakeConnection:
    def __init__(self, hypervisor: FakeHypervisor, uri: str) -> None:
        self.hv = hypervisor
        self._uri = uri
        self.is_closed = False
        self.alive = True

    @property
    def uri(self) -> str:
        return self._uri

    def _check(self) -> None:
        if self.is_closed:
            raise ConnectionFailedError("connection closed")

    def define(self, xml: str) -> FakeDomain:
        self._check()
        self.hv.busy("define")
        name = ET.fromstring(xml).findtext("name") or ""
        store = self.hv.domains(self._uri)
        if name in store:
            old = store[name]
            new = FakeDomain(self.hv, self._uri, xml)
            new.status = old.status
            store[name] = new
            return new
        domain = FakeDomain(self.hv, self._uri, xml)
        store[name] = domain
        return domain

    def lookup(self, name: str) -> FakeDomain:
        self._check()
        try:
            return self.hv.domains(self._uri)[name]
        except KeyError:
            raise DomainNotFoundError(f"Domain not found: {name}") from None

    def names(self) -> list[str]:
        self._check()
        return sorted(self.hv.domains(self._uri))

    def host_info(self) -> HostInfo:
        self._check()
        return HostInfo(self._uri, "fakehost", "FAKE", 8, 16384.0, 4096.0, 2048.0, 512.0)

    def is_alive(self) -> bool:
        return self.alive and not self.is_closed

    def close(self) -> None:
        if not self.is_closed:
            self.is_closed = True
            self.hv.closed[self._uri] += 1


class FakeDiskTool:
    """Writes small placeholder files instead of calling qemu-img."""

    def __init__(self) -> None:
        self.created: list[Path] = []
        self.removed: list[Path] = []
        self._lock = threading.Lock()

    def create(self, path: Path, size_mib: int, fmt: str = "qcow2") -> bool:
        if path.exists():
            return False
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{fmt}:{size_mib}")
        with self._lock:
            self.created.append(path)
        return True

    def remove(self, path: Path) -> bool:
        if not path.exists():
            return False
        path.unlink()
        with self._lock:
            self.removed.append(path)
        return True
