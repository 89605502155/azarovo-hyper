"""Admission control: measure the host, check a demand and act, atomically."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from azarovo_hyper.domain.resources import Demand, ResourcePolicy, shortfalls
from azarovo_hyper.errors import InsufficientResourcesError
from azarovo_hyper.ports.backend import Connection
from azarovo_hyper.resources.lock import HostLock, default_lock

MIB = 1024 * 1024
FreeSpace = Callable[[Path], float]


def nearest_existing(path: Path) -> Path:
    while not path.exists() and path != path.parent:
        path = path.parent
    return path


def free_space_mib(path: Path) -> float:
    return shutil.disk_usage(nearest_existing(path)).free / MIB


class Admission:
    """Grants demands only while the host can still satisfy them."""

    def __init__(self, lock: HostLock | None = None, free_space: FreeSpace | None = None) -> None:
        self._lock = lock
        self.free_space = free_space or free_space_mib

    @property
    def lock(self) -> HostLock:
        return self._lock or default_lock()

    @contextmanager
    def reserve(
        self,
        demand: Demand,
        *,
        policy: ResourcePolicy,
        connection: Callable[[], Connection],
        disk_dir: Path | None = None,
    ) -> Iterator[None]:
        """Raise if ``demand`` does not fit, otherwise run the block under the host lock.

        The block must contain only the call that takes the resource (not the
        wait for a guest to boot), so the lock is held for milliseconds.
        """
        if not policy.check_resources or not demand:
            yield
            return
        needs_host = bool(demand.memory_mib or demand.vcpus or demand.vm_vcpus)
        with self.lock.held():
            usage = connection().usage() if needs_host else None
            free = None
            if demand.disk_mib and disk_dir is not None:
                free = self.free_space(disk_dir)
            problems = shortfalls(demand, policy=policy, usage=usage, free_disk_mib=free)
            if problems:
                raise InsufficientResourcesError(
                    "not enough host resources: " + "; ".join(map(str, problems)),
                    tuple(problems),
                )
            yield
