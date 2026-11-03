"""virConnect, virDomain, snapshots and streams over ctypes.

Method names and return shapes copy the official Python binding, so the
adapters work unchanged with either backend.
"""

from __future__ import annotations

import contextlib
import ctypes
from collections.abc import Callable
from ctypes import c_void_p, create_string_buffer
from typing import Any

from azarovo_hyper.adapters.native import library as clib
from azarovo_hyper.adapters.native.errors import ok

MEMORY_TAGS = (
    "swap_in", "swap_out", "major_fault", "minor_fault", "unused", "available", "actual",
    "rss", "usable", "last_update", "disk_caches", "hugetlb_pgalloc", "hugetlb_pgfail",
)  # fmt: skip


class _Handle:
    """Owns one libvirt object pointer and frees it exactly once."""

    _free: str = ""

    def __init__(self, pointer: int, owner: object = None) -> None:
        self._ptr = pointer
        self._owner = owner

    def __del__(self) -> None:
        pointer, self._ptr = getattr(self, "_ptr", None), None
        if pointer and self._free:
            with contextlib.suppress(Exception):
                getattr(clib.lib(), self._free)(pointer)


def _array(pointer: Any, count: int) -> list[int]:
    """Copy the addresses out of a libvirt-allocated array, then free the array.

    Indexing a ctypes pointer array returns views into the array itself, so
    the addresses must be copied as integers before ``free``.
    """
    if not pointer:
        return []
    raw = ctypes.cast(pointer, ctypes.POINTER(c_void_p))
    try:
        return [int(raw[i] or 0) for i in range(count)]
    finally:
        clib.libc().free(ctypes.cast(pointer, c_void_p))


class virStream(_Handle):  # noqa: N801
    _free = "virStreamFree"

    def recvAll(self, handler: Callable[..., object], opaque: object) -> None:  # noqa: N802
        buffer = create_string_buffer(256 * 1024)
        while got := ok(clib.lib().virStreamRecv(self._ptr, buffer, len(buffer)), "virStreamRecv"):
            handler(self, buffer.raw[:got], opaque)

    def finish(self) -> None:
        ok(clib.lib().virStreamFinish(self._ptr), "virStreamFinish")

    def abort(self) -> None:
        clib.lib().virStreamAbort(self._ptr)


class virDomainSnapshot(_Handle):  # noqa: N801
    _free = "virDomainSnapshotFree"

    def getName(self) -> str:  # noqa: N802
        return (clib.lib().virDomainSnapshotGetName(self._ptr) or b"").decode()

    def delete(self, flags: int = 0) -> None:
        ok(clib.lib().virDomainSnapshotDelete(self._ptr, flags), "virDomainSnapshotDelete")
