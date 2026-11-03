"""Reference-counted, thread-safe pool of hypervisor connections.

Every machine leases the connection for its URI. The connection is opened by
the first lease and closed as soon as the last lease is released, so stopped,
closed or garbage-collected machines leave no sockets behind.

The pool lock only guards the bookkeeping; opening a connection happens under a
per-URI lock, so a slow ``xen:///system`` never delays ``qemu:///session``.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field

from azarovo_hyper.errors import ConnectionFailedError
from azarovo_hyper.ports.backend import Connection, Connector

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class _Entry:
    refs: int = 0
    connection: Connection | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)


class Lease:
    """One holder's share of a pooled connection."""

    def __init__(self, pool: ConnectionPool, uri: str, entry: _Entry) -> None:
        self._pool = pool
        self._entry = entry
        self._lock = threading.Lock()
        self._released = False
        self.uri = uri

    @property
    def released(self) -> bool:
        return self._released

    @property
    def connection(self) -> Connection:
        connection = self._entry.connection
        if self._released or connection is None:
            raise ConnectionFailedError(f"the lease on {self.uri} was released")
        return connection

    def release(self) -> None:
        """Give the share back; safe to call more than once and from any thread."""
        with self._lock:
            if self._released:
                return
            self._released = True
        self._pool._drop(self.uri, self._entry)

    def __enter__(self) -> Connection:
        return self.connection

    def __exit__(self, *_exc: object) -> None:
        self.release()


class ConnectionPool:
    """Shares one connection per URI between all machines that use it."""

    def __init__(self, connector: Connector | None = None) -> None:
        self._connector = connector
        self._lock = threading.Lock()
        self._entries: dict[str, _Entry] = {}

    def _connect(self, uri: str) -> Connection:
        if self._connector is not None:
            return self._connector(uri)
        from azarovo_hyper.adapters.libvirt_connection import LibvirtConnection

        return LibvirtConnection.open(uri)

    def acquire(self, uri: str) -> Lease:
        with self._lock:
            entry = self._entries.setdefault(uri, _Entry())
            entry.refs += 1
        try:
            with entry.lock:
                if entry.connection is not None and not entry.connection.is_alive():
                    logger.info("connection to %s is dead, reopening", uri)
                    _close_quietly(entry.connection)
                    entry.connection = None
                if entry.connection is None:
                    entry.connection = self._connect(uri)
                    logger.debug("opened connection to %s", uri)
        except BaseException:
            self._drop(uri, entry)
            raise
        return Lease(self, uri, entry)

    def _drop(self, uri: str, entry: _Entry) -> None:
        with self._lock:
            entry.refs -= 1
            if entry.refs > 0:
                return
            if self._entries.get(uri) is entry:
                del self._entries[uri]
        with entry.lock:
            connection, entry.connection = entry.connection, None
        if connection is not None:
            _close_quietly(connection)
            logger.debug("closed connection to %s", uri)

    def refcount(self, uri: str) -> int:
        with self._lock:
            entry = self._entries.get(uri)
            return 0 if entry is None else entry.refs

    def active(self) -> dict[str, int]:
        """``{uri: number of leases}`` for every open connection."""
        with self._lock:
            return {uri: entry.refs for uri, entry in self._entries.items()}

    def close_all(self) -> None:
        """Close every connection, even if leases are still outstanding."""
        with self._lock:
            entries, self._entries = list(self._entries.values()), {}
        for entry in entries:
            with entry.lock:
                connection, entry.connection = entry.connection, None
            if connection is not None:
                _close_quietly(connection)


def _close_quietly(connection: Connection) -> None:
    try:
        connection.close()
    except Exception:
        logger.debug("ignoring error while closing a connection", exc_info=True)


_default_pool: ConnectionPool | None = None
_default_lock = threading.Lock()


def default_pool() -> ConnectionPool:
    """The process-wide pool used when no pool is passed explicitly."""
    global _default_pool
    with _default_lock:
        if _default_pool is None:
            _default_pool = ConnectionPool()
        return _default_pool
