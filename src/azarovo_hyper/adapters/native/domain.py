"""``virDomain`` over ctypes, API-compatible with the official binding."""

from __future__ import annotations

import ctypes
from ctypes import POINTER, byref, c_int, c_void_p, create_string_buffer, sizeof
from typing import Any

from azarovo_hyper.adapters.native import library as clib
from azarovo_hyper.adapters.native.errors import ok, ptr
from azarovo_hyper.adapters.native.objects import (
    MEMORY_TAGS,
    _array,
    _Handle,
    virDomainSnapshot,
    virStream,
)


def _call(name: str, *args: Any) -> int:
    return ok(getattr(clib.lib(), name)(*args), name)


class virDomain(_Handle):  # noqa: N801
    _free = "virDomainFree"

    def name(self) -> str:
        return (clib.lib().virDomainGetName(self._ptr) or b"").decode()

    def UUIDString(self) -> str:  # noqa: N802
        buffer = create_string_buffer(37)
        _call("virDomainGetUUIDString", self._ptr, buffer)
        return buffer.value.decode()

    def state(self, flags: int = 0) -> list[int]:
        state, reason = c_int(), c_int()
        _call("virDomainGetState", self._ptr, byref(state), byref(reason), flags)
        return [state.value, reason.value]

    def info(self) -> list[int]:
        data = clib.DomainInfo()
        _call("virDomainGetInfo", self._ptr, byref(data))
        return [data.state, data.max_mem, data.memory, data.vcpus, data.cpu_time]

    def create(self) -> int:
        return _call("virDomainCreate", self._ptr)

    def shutdown(self) -> int:
        return _call("virDomainShutdown", self._ptr)

    def destroy(self) -> int:
        return _call("virDomainDestroy", self._ptr)

    def suspend(self) -> int:
        return _call("virDomainSuspend", self._ptr)

    def resume(self) -> int:
        return _call("virDomainResume", self._ptr)

    def undefine(self) -> int:
        return _call("virDomainUndefine", self._ptr)

    def reboot(self, flags: int = 0) -> int:
        return _call("virDomainReboot", self._ptr, flags)

    def reset(self, flags: int = 0) -> int:
        return _call("virDomainReset", self._ptr, flags)

    def undefineFlags(self, flags: int = 0) -> int:  # noqa: N802
        return _call("virDomainUndefineFlags", self._ptr, flags)

    def XMLDesc(self, flags: int = 0) -> str:  # noqa: N802
        return clib.take_string(ptr(clib.lib().virDomainGetXMLDesc(self._ptr, flags), "XMLDesc"))

    def autostart(self) -> int:
        value = c_int()
        _call("virDomainGetAutostart", self._ptr, byref(value))
        return value.value

    def setAutostart(self, enabled: int) -> int:  # noqa: N802
        return _call("virDomainSetAutostart", self._ptr, enabled)

    def maxMemory(self) -> int:  # noqa: N802
        return int(ptr(clib.lib().virDomainGetMaxMemory(self._ptr), "virDomainGetMaxMemory"))

    def setMemoryFlags(self, kib: int, flags: int = 0) -> int:  # noqa: N802
        return _call("virDomainSetMemoryFlags", self._ptr, kib, flags)

    def setMemoryStatsPeriod(self, period: int, flags: int = 0) -> int:  # noqa: N802
        return _call("virDomainSetMemoryStatsPeriod", self._ptr, period, flags)

    def memoryStats(self) -> dict[str, int]:  # noqa: N802
        stats = (clib.MemoryStat * 16)()
        count = _call("virDomainMemoryStats", self._ptr, stats, 16, 0)
        return {MEMORY_TAGS[s.tag]: s.val for s in stats[:count] if s.tag < len(MEMORY_TAGS)}

    def setVcpusFlags(self, count: int, flags: int = 0) -> int:  # noqa: N802
        return _call("virDomainSetVcpusFlags", self._ptr, count, flags)

    def attachDeviceFlags(self, xml: str, flags: int = 0) -> int:  # noqa: N802
        return _call("virDomainAttachDeviceFlags", self._ptr, xml.encode(), flags)

    def detachDeviceFlags(self, xml: str, flags: int = 0) -> int:  # noqa: N802
        return _call("virDomainDetachDeviceFlags", self._ptr, xml.encode(), flags)

    def updateDeviceFlags(self, xml: str, flags: int = 0) -> int:  # noqa: N802
        return _call("virDomainUpdateDeviceFlags", self._ptr, xml.encode(), flags)

    def blockStats(self, path: str) -> tuple[int, ...]:  # noqa: N802
        data = clib.BlockStats()
        _call("virDomainBlockStats", self._ptr, path.encode(), byref(data), sizeof(data))
        return tuple(getattr(data, n) for n, _t in clib.BlockStats._fields_)

    def interfaceStats(self, path: str) -> tuple[int, ...]:  # noqa: N802
        data = clib.InterfaceStats()
        _call("virDomainInterfaceStats", self._ptr, path.encode(), byref(data), sizeof(data))
        return tuple(getattr(data, n) for n, _t in clib.InterfaceStats._fields_)

    def interfaceAddresses(self, source: int, flags: int = 0) -> dict[str, Any]:  # noqa: N802
        ifaces = POINTER(POINTER(clib.Interface))()
        count = _call("virDomainInterfaceAddresses", self._ptr, byref(ifaces), source, flags)
        result: dict[str, Any] = {}
        for address in _array(ifaces, count):
            item = ctypes.cast(address, POINTER(clib.Interface))
            iface = item.contents
            addrs = [
                {"type": a.type, "addr": (a.addr or b"").decode(), "prefix": a.prefix}
                for a in iface.addrs[: iface.naddrs]
            ]
            hwaddr = (iface.hwaddr or b"").decode() or None
            result[(iface.name or b"").decode()] = {"hwaddr": hwaddr, "addrs": addrs}
            clib.lib().virDomainInterfaceFree(item)
        return result

    def screenshot(self, stream: virStream, screen: int, flags: int = 0) -> str:
        raw = clib.lib().virDomainScreenshot(self._ptr, stream._ptr, screen, flags)
        return clib.take_string(ptr(raw, "virDomainScreenshot"))

    def snapshotCreateXML(self, xml: str, flags: int = 0) -> virDomainSnapshot:  # noqa: N802
        raw = clib.lib().virDomainSnapshotCreateXML(self._ptr, xml.encode(), flags)
        return virDomainSnapshot(ptr(raw, "virDomainSnapshotCreateXML"), self)

    def snapshotListNames(self, flags: int = 0) -> list[str]:  # noqa: N802
        items = POINTER(c_void_p)()
        count = _call("virDomainListAllSnapshots", self._ptr, byref(items), flags)
        return [virDomainSnapshot(p, self).getName() for p in _array(items, count)]

    def snapshotLookupByName(self, name: str, flags: int = 0) -> virDomainSnapshot:  # noqa: N802
        raw = clib.lib().virDomainSnapshotLookupByName(self._ptr, name.encode(), flags)
        return virDomainSnapshot(ptr(raw, "virDomainSnapshotLookupByName"), self)

    def revertToSnapshot(self, snapshot: virDomainSnapshot, flags: int = 0) -> int:  # noqa: N802
        return _call("virDomainRevertToSnapshot", snapshot._ptr, flags)
