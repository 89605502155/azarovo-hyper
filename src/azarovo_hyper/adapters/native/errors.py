"""``libvirtError`` for the native backend, filled from ``virGetLastError``.

libvirt keeps the last error per thread, so reading it right after a failed
call is safe even when many threads talk to the hypervisor at once.
"""

from __future__ import annotations

from typing import TypeVar

from azarovo_hyper.adapters.native.library import ErrorFunc, lib

T = TypeVar("T")


class libvirtError(Exception):  # noqa: N801 - same name as in the official binding
    """A failed libvirt call (API-compatible with ``libvirt.libvirtError``)."""

    def __init__(self, what: str) -> None:
        error = lib().virGetLastError()
        if error:
            self.code = int(error.contents.code)
            self.domain = int(error.contents.domain)
            message = (error.contents.message or b"").decode(errors="replace")
        else:
            self.code, self.domain, message = 1, 0, ""
        lib().virResetLastError()
        super().__init__(message or f"{what}() failed")

    def get_error_code(self) -> int:
        return self.code

    def get_error_domain(self) -> int:
        return self.domain

    def get_error_message(self) -> str:
        return str(self)


def ok(result: int, what: str) -> int:
    """Raise for a ``-1`` return code."""
    if result < 0:
        raise libvirtError(what)
    return result


def ptr(result: T | None, what: str) -> T:
    """Raise for a ``NULL`` result."""
    if not result:
        raise libvirtError(what)
    return result


@ErrorFunc
def _silent(_context: object, _error: object) -> None:
    """Keep libvirt from printing every error to stderr; errors are raised instead."""


def silence_stderr() -> None:
    lib().virSetErrorFunc(None, _silent)
