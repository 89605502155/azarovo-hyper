"""Translation of ``libvirt.libvirtError`` into the library's exceptions."""

from __future__ import annotations

import functools
import sys
from collections.abc import Callable
from typing import Any, TypeVar, cast

from azarovo_hyper.errors import (
    BackendError,
    ConnectionFailedError,
    DomainNotFoundError,
    HyperError,
    OperationTimeoutError,
    UnsupportedOperationError,
    VMStateError,
)

F = TypeVar("F", bound=Callable[..., Any])

_CODES: tuple[tuple[type[HyperError], tuple[str, ...]], ...] = (
    (DomainNotFoundError, ("VIR_ERR_NO_DOMAIN", "VIR_ERR_NO_DOMAIN_SNAPSHOT")),
    (VMStateError, ("VIR_ERR_OPERATION_INVALID",)),
    (
        UnsupportedOperationError,
        (
            "VIR_ERR_NO_SUPPORT",
            "VIR_ERR_OPERATION_UNSUPPORTED",
            "VIR_ERR_ARGUMENT_UNSUPPORTED",
            "VIR_ERR_CONFIG_UNSUPPORTED",
        ),
    ),
    (OperationTimeoutError, ("VIR_ERR_OPERATION_TIMEOUT", "VIR_ERR_AGENT_UNRESPONSIVE")),
    (
        ConnectionFailedError,
        ("VIR_ERR_NO_CONNECT", "VIR_ERR_INVALID_CONN", "VIR_ERR_RPC", "VIR_ERR_AUTH_FAILED"),
    ),
)


def is_libvirt_error(exc: BaseException) -> bool:
    return type(exc).__name__ == "libvirtError"


def translate(exc: BaseException) -> HyperError:
    """Pick the library exception that matches a libvirt error code."""
    libvirt = sys.modules.get("libvirt")
    get_code = getattr(exc, "get_error_code", None)
    code = get_code() if callable(get_code) else None
    message = str(exc)
    if libvirt is not None and code is not None:
        for error_type, names in _CODES:
            if code in {getattr(libvirt, n, object()) for n in names}:
                return error_type(message)
    return BackendError(message)


def libvirt_errors(func: F) -> F:
    """Decorator: re-raise libvirt errors as :class:`HyperError` subclasses."""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            if not is_libvirt_error(exc):
                raise
            raise translate(exc) from exc

    return cast("F", wrapper)
