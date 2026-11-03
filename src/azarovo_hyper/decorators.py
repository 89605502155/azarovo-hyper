"""Reusable decorators for machine objects and adapters.

Machine-bound decorators expect ``self._session`` to be a
:class:`~azarovo_hyper.vm.session.VMSession`: it carries the per-machine lock,
the closed flag, the driver capabilities and the current state.
"""

from __future__ import annotations

import functools
import inspect
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

from azarovo_hyper.domain.state import VMState
from azarovo_hyper.errors import UnsupportedOperationError, VMClosedError, VMStateError

F = TypeVar("F", bound=Callable[..., Any])
C = TypeVar("C", bound=type)

logger = logging.getLogger(__name__)


def synchronized(method: F) -> F:
    """Run the method under the machine lock.

    Each machine has its own re-entrant lock, so operations on one machine are
    serialised while different machines never wait for each other.
    """

    @functools.wraps(method)
    def wrapper(self: Any, /, *args: Any, **kwargs: Any) -> Any:
        with self._session.lock:
            return method(self, *args, **kwargs)

    return cast("F", wrapper)


def alive(method: F) -> F:
    """Refuse to run once the machine object has been closed or deleted."""

    @functools.wraps(method)
    def wrapper(self: Any, /, *args: Any, **kwargs: Any) -> Any:
        session = self._session
        if session.closed.is_set():
            raise VMClosedError(f"{session.name}: the machine object is closed")
        return method(self, *args, **kwargs)

    return cast("F", wrapper)


def guarded(method: F) -> F:
    """``synchronized`` + ``alive``: the closed flag is checked under the lock."""
    return synchronized(alive(method))


def chainable(method: F) -> F:
    """Return ``self`` so calls can be chained: ``vm.define().start()``."""

    @functools.wraps(method)
    def wrapper(self: Any, /, *args: Any, **kwargs: Any) -> Any:
        method(self, *args, **kwargs)
        return self

    return cast("F", wrapper)


def requires_state(*states: VMState) -> Callable[[F], F]:
    """Allow the method only when the machine is in one of ``states``."""

    def decorate(method: F) -> F:
        @functools.wraps(method)
        def wrapper(self: Any, /, *args: Any, **kwargs: Any) -> Any:
            current = self._session.state()
            if current not in states:
                allowed = ", ".join(s.name.lower() for s in states)
                raise VMStateError(
                    f"{self._session.name}: {method.__name__}() needs state {allowed}, "
                    f"but the machine is {current.name.lower()}"
                )
            return method(self, *args, **kwargs)

        return cast("F", wrapper)

    return decorate


def requires_running(method: F) -> F:
    """Shortcut for operations that only make sense on a live machine."""
    return requires_state(VMState.RUNNING, VMState.PAUSED, VMState.BLOCKED)(method)


def requires_capability(flag: str) -> Callable[[F], F]:
    """Allow the method only when the hypervisor driver supports ``flag``."""

    def decorate(method: F) -> F:
        @functools.wraps(method)
        def wrapper(self: Any, /, *args: Any, **kwargs: Any) -> Any:
            driver = self._session.driver
            if not getattr(driver.capabilities, flag):
                raise UnsupportedOperationError(
                    f"{driver.name}: {method.__name__}() is not supported ({flag})"
                )
            return method(self, *args, **kwargs)

        return cast("F", wrapper)

    return decorate


def retry(
    times: int = 3,
    delay: float = 0.2,
    on: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[F], F]:
    """Retry a call that may fail transiently, sleeping ``delay`` between tries."""
    if times < 1:
        raise ValueError("times must be >= 1")

    def decorate(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except on as exc:
                    if attempt == times:
                        raise
                    logger.debug("%s failed (%s), retry %d/%d", func.__name__, exc, attempt, times)
                    time.sleep(delay)
            raise AssertionError("unreachable")  # pragma: no cover

        return cast("F", wrapper)

    return decorate


def decorate_public_methods(decorator: Callable[[Any], Any]) -> Callable[[C], C]:
    """Class decorator: apply ``decorator`` to every public method of the class."""

    def apply(cls: C) -> C:
        for name, member in list(vars(cls).items()):
            if name.startswith("_") or not inspect.isfunction(member):
                continue
            setattr(cls, name, decorator(member))
        return cls

    return apply
