"""CPU load from cumulative ``cpu_time`` counters.

libvirt reports CPU time accumulated since the guest started, so the current
load is the increase between two samples divided by the elapsed wall time and
the number of vCPUs. Each machine owns its own sampler, so samplers of
different machines never share state across threads.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

NANOSECONDS = 1e9


class CpuSampler:
    """Turns successive ``cpu_time`` readings into a load percentage."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._last: tuple[int, float] | None = None

    def sample(self, cpu_time_ns: int, vcpus: int) -> float:
        """Load since the previous sample, 0..100 %. The first sample returns 0."""
        now = self._clock()
        with self._lock:
            previous, self._last = self._last, (cpu_time_ns, now)
        if previous is None or vcpus <= 0:
            return 0.0
        busy_ns = cpu_time_ns - previous[0]
        elapsed_s = now - previous[1]
        if busy_ns < 0 or elapsed_s <= 0:
            return 0.0
        return min(busy_ns / (elapsed_s * NANOSECONDS * vcpus) * 100.0, 100.0)

    def reset(self) -> None:
        """Forget the previous sample, e.g. after the guest was restarted."""
        with self._lock:
            self._last = None
