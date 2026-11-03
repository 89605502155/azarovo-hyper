"""``virConnect`` over ctypes, API-compatible with the official binding."""

from __future__ import annotations

import contextlib
from ctypes import POINTER, byref, c_int, c_void_p
from typing import Any

from azarovo_hyper.adapters.native import library as clib
from azarovo_hyper.adapters.native.domain import virDomain
from azarovo_hyper.adapters.native.errors import libvirtError, ok, ptr
from azarovo_hyper.adapters.native.objects import _array, virStream


class virConnect:  # noqa: N801
    def __init__(self, pointer: int) -> None:
        self._ptr: int | None = pointer

    def _live(self) -> int:
        if not self._ptr:
            raise libvirtError("connection is closed")
        return self._ptr

    def close(self) -> int:
        pointer, self._ptr = self._ptr, None
        return ok(clib.lib().virConnectClose(pointer), "virConnectClose") if pointer else 0

    def __del__(self) -> None:
        if getattr(self, "_ptr", None):
            with contextlib.suppress(Exception):
                self.close()

    def isAlive(self) -> int:  # noqa: N802
        return 1 if self._ptr and clib.lib().virConnectIsAlive(self._ptr) == 1 else 0

    def defineXML(self, xml: str) -> virDomain:  # noqa: N802
        raw = clib.lib().virDomainDefineXML(self._live(), xml.encode())
        return virDomain(ptr(raw, "virDomainDefineXML"), self)

    def lookupByName(self, name: str) -> virDomain:  # noqa: N802
        raw = clib.lib().virDomainLookupByName(self._live(), name.encode())
        return virDomain(ptr(raw, "virDomainLookupByName"), self)

    def listAllDomains(self, flags: int = 0) -> list[virDomain]:  # noqa: N802
        items = POINTER(c_void_p)()
        count = ok(
            clib.lib().virConnectListAllDomains(self._live(), byref(items), flags),
            "virConnectListAllDomains",
        )
        return [virDomain(p, self) for p in _array(items, count)]

    def getInfo(self) -> list[Any]:  # noqa: N802
        data = clib.NodeInfo()
        ok(clib.lib().virNodeGetInfo(self._live(), byref(data)), "virNodeGetInfo")
        return [
            data.model.decode(), data.memory // 1024, data.cpus, data.mhz,
            data.nodes, data.sockets, data.cores, data.threads,
        ]  # fmt: skip

    def getMemoryStats(self, cell: int, flags: int = 0) -> dict[str, int]:  # noqa: N802
        count = c_int(0)
        name = "virNodeGetMemoryStats"
        ok(clib.lib().virNodeGetMemoryStats(self._live(), cell, None, byref(count), flags), name)
        stats = (clib.NodeMemoryStat * max(count.value, 1))()
        ok(clib.lib().virNodeGetMemoryStats(self._ptr, cell, stats, byref(count), flags), name)
        return {s.field.decode(): s.value for s in stats[: count.value]}

    def getFreeMemory(self) -> int:  # noqa: N802
        return int(clib.lib().virNodeGetFreeMemory(self._live()))

    def getHostname(self) -> str:  # noqa: N802
        raw = clib.lib().virConnectGetHostname(self._live())
        return clib.take_string(ptr(raw, "virConnectGetHostname"))

    def getType(self) -> str:  # noqa: N802
        return (ptr(clib.lib().virConnectGetType(self._live()), "virConnectGetType")).decode()

    def newStream(self, flags: int = 0) -> virStream:  # noqa: N802
        return virStream(ptr(clib.lib().virStreamNew(self._live(), flags), "virStreamNew"), self)
