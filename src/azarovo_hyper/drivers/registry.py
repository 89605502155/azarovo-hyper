"""Registry of hypervisor drivers, filled by the :func:`register_driver` decorator."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TypeVar

from azarovo_hyper.drivers.base import HypervisorDriver
from azarovo_hyper.errors import ConfigurationError

D = TypeVar("D", bound=type[HypervisorDriver])

_drivers: dict[str, type[HypervisorDriver]] = {}
_instances: dict[str, HypervisorDriver] = {}
_lock = threading.Lock()


def register_driver(name: str) -> Callable[[D], D]:
    """Class decorator that makes a driver available as ``hyper().<name>(...)``."""

    def decorate(cls: D) -> D:
        key = name.lower()
        with _lock:
            if key in _drivers and _drivers[key] is not cls:
                raise ConfigurationError(f"driver {key!r} is already registered")
            cls.name = key
            _drivers[key] = cls
            _instances.pop(key, None)
        return cls

    return decorate


def get_driver(name: str) -> HypervisorDriver:
    """Shared, stateless driver instance for ``name``."""
    key = name.lower()
    with _lock:
        if key not in _drivers:
            known = ", ".join(sorted(_drivers)) or "none"
            raise ConfigurationError(f"unknown hypervisor {name!r}; available: {known}")
        if key not in _instances:
            _instances[key] = _drivers[key]()
        return _instances[key]


def driver_names() -> list[str]:
    with _lock:
        return sorted(_drivers)
