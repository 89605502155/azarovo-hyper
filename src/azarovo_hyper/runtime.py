"""Process-level helpers: fork safety and child-process cleanup.

A forked child inherits open libvirt sockets, held locks and finalizers of
its parent. Objects registered with :func:`track_fork` get their
``_after_fork()`` called in the child, so they drop what belongs to the
parent (without closing it) and start with fresh locks.
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
import weakref
from collections.abc import Callable, Iterable
from typing import Any

_lock = threading.Lock()
_tracked: weakref.WeakSet[Any] = weakref.WeakSet()
_inherited: list[Any] = []


def keep_inherited(*objects: Any) -> None:
    """Keep objects inherited from the parent alive until the child exits.

    Collecting an inherited libvirt connection would run its destructor,
    which sends "close" over the socket the parent is still using.
    """
    _inherited.extend(o for o in objects if o is not None)


def track_fork(obj: Any) -> None:
    """Call ``obj._after_fork()`` in every child forked from this process."""
    with _lock:
        _tracked.add(obj)


def _reset_in_child() -> None:
    global _lock
    _lock = threading.Lock()
    for obj in list(_tracked):
        obj._after_fork()


os.register_at_fork(after_in_child=_reset_in_child)


def wait_until(
    condition: Callable[[], bool],
    *,
    timeout: float,
    interrupt: threading.Event,
    what: str,
    interval: float = 0.25,
) -> None:
    """Poll ``condition`` until true; ``interrupt`` aborts the wait early."""
    from azarovo_hyper.errors import OperationTimeoutError, VMClosedError

    deadline = time.monotonic() + timeout
    while not condition():
        left = deadline - time.monotonic()
        if left <= 0:
            raise OperationTimeoutError(f"{what}: not reached after {timeout:g} s")
        if interrupt.wait(min(interval, left)):
            raise VMClosedError(f"{what}: closed while waiting")


def terminate(processes: Iterable[subprocess.Popen[bytes]], timeout: float = 5.0) -> None:
    """Stop child processes: SIGTERM, then SIGKILL after ``timeout``."""
    for process in processes:
        if process.poll() is not None:
            continue
        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
