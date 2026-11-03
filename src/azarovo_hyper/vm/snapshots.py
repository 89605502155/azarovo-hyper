"""Snapshots of the whole machine (disk and, when running, memory)."""

from __future__ import annotations

import time
from collections.abc import Iterator

from azarovo_hyper.config.render import render
from azarovo_hyper.decorators import guarded, requires_capability
from azarovo_hyper.errors import ConfigurationError
from azarovo_hyper.vm.session import SessionBound


class SnapshotController(SessionBound):
    """``vm.snapshots``"""

    __slots__ = ()

    @guarded
    @requires_capability("snapshots")
    def create(self, name: str | None = None, *, description: str = "") -> str:
        """Take a snapshot and return its name (default: a timestamp)."""
        name = name or time.strftime("snap-%Y%m%d-%H%M%S")
        if name in self.names():
            raise ConfigurationError(f"{self._session.name}: snapshot {name!r} already exists")
        xml = render("devices/snapshot.xml", name=name, description=description)
        self._session.domain().snapshot_create(str(xml))
        return name

    @guarded
    @requires_capability("snapshots")
    def names(self) -> list[str]:
        return self._session.domain().snapshot_names()

    @guarded
    @requires_capability("snapshots")
    def revert(self, name: str) -> None:
        """Return the machine to a snapshot (its power state included)."""
        self._session.cpu_sampler.reset()
        self._session.domain().snapshot_revert(name)

    @guarded
    @requires_capability("snapshots")
    def delete(self, name: str) -> None:
        self._session.domain().snapshot_delete(name)

    def __iter__(self) -> Iterator[str]:
        return iter(self.names())

    def __contains__(self, name: object) -> bool:
        return name in self.names()

    def __len__(self) -> int:
        return len(self.names())
