"""Host-wide lock that makes "check capacity, then take it" one atomic step.

Every admission holds it while it measures the host *and* performs the
hypervisor call (start, vCPU or memory hot-plug, disk preallocation). When the
lock is released the hypervisor already reports the resource as used, so the
next caller sees it — across threads and processes, with nothing to count
twice and no reservations to expire.
"""

from __future__ import annotations

import fcntl
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from azarovo_hyper.runtime import track_fork


def default_path() -> Path:
    """``$AZAROVO_LOCK``, else ``$XDG_RUNTIME_DIR/azarovo-hyper/``, else ``~/.cache``."""
    if explicit := os.environ.get("AZAROVO_LOCK"):
        return Path(explicit)
    base = os.environ.get("XDG_RUNTIME_DIR") or Path.home() / ".cache"
    return Path(base) / "azarovo-hyper" / "capacity.lock"


class HostLock:
    """Exclusive ``flock`` plus an in-process lock (one holder at a time)."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_path()
        self._lock = threading.Lock()
        track_fork(self)

    def _after_fork(self) -> None:
        self._lock = threading.Lock()

    @contextmanager
    def held(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, self.path.open("a+") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)


_default: HostLock | None = None
_default_lock = threading.Lock()


def default_lock() -> HostLock:
    global _default
    with _default_lock:
        if _default is None or _default.path != default_path():
            _default = HostLock()
        return _default
