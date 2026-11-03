"""ctypes bindings to the system ``libvirt.so.0``: no compiler, no headers.

Only the functions the library uses are declared. Opaque libvirt objects are
plain ``void*``; strings that libvirt allocates are returned as ``void*`` so
they can be freed after copying.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import functools
from ctypes import (
    CFUNCTYPE,
    POINTER,
    Structure,
    c_char,
    c_char_p,
    c_int,
    c_longlong,
    c_size_t,
    c_ubyte,
    c_uint,
    c_ulong,
    c_ulonglong,
    c_ushort,
    c_void_p,
)

LIBRARY = "libvirt.so.0"
P = c_void_p


class NodeInfo(Structure):
    _fields_ = (
        ("model", c_char * 32),
        ("memory", c_ulong),
        ("cpus", c_uint),
        ("mhz", c_uint),
        ("nodes", c_uint),
        ("sockets", c_uint),
        ("cores", c_uint),
        ("threads", c_uint),
    )


class DomainInfo(Structure):
    _fields_ = (
        ("state", c_ubyte),
        ("max_mem", c_ulong),
        ("memory", c_ulong),
        ("vcpus", c_ushort),
        ("cpu_time", c_ulonglong),
    )


class MemoryStat(Structure):
    _fields_ = (("tag", c_int), ("val", c_ulonglong))


class NodeMemoryStat(Structure):
    _fields_ = (("field", c_char * 80), ("value", c_ulonglong))


class BlockStats(Structure):
    _fields_ = tuple((n, c_longlong) for n in ("rd_req", "rd_bytes", "wr_req", "wr_bytes", "errs"))


class InterfaceStats(Structure):
    _fields_ = tuple(
        (n, c_longlong)
        for n in (
            "rx_bytes",
            "rx_packets",
            "rx_errs",
            "rx_drop",
            "tx_bytes",
            "tx_packets",
            "tx_errs",
            "tx_drop",
        )
    )


class IPAddress(Structure):
    _fields_ = (("type", c_int), ("addr", c_char_p), ("prefix", c_uint))


class Interface(Structure):
    _fields_ = (
        ("name", c_char_p),
        ("hwaddr", c_char_p),
        ("naddrs", c_uint),
        ("addrs", POINTER(IPAddress)),
    )


class Error(Structure):
    _fields_ = (
        ("code", c_int),
        ("domain", c_int),
        ("message", c_char_p),
        ("level", c_int),
        ("conn", P),
        ("dom", P),
        ("str1", c_char_p),
        ("str2", c_char_p),
        ("str3", c_char_p),
        ("int1", c_int),
        ("int2", c_int),
        ("net", P),
    )


ErrorFunc = CFUNCTYPE(None, P, POINTER(Error))
_I, _U, _S = c_int, c_uint, c_char_p

SIGNATURES: dict[str, tuple[object, tuple[object, ...]]] = {
    "virGetVersion": (_I, (POINTER(c_ulong), _S, POINTER(c_ulong))),
    "virGetLastError": (POINTER(Error), ()),
    "virResetLastError": (None, ()),
    "virSetErrorFunc": (None, (P, ErrorFunc)),
    "virConnectOpen": (P, (_S,)),
    "virConnectClose": (_I, (P,)),
    "virConnectIsAlive": (_I, (P,)),
    "virConnectGetHostname": (P, (P,)),
    "virConnectGetType": (_S, (P,)),
    "virConnectListAllDomains": (_I, (P, POINTER(POINTER(P)), _U)),
    "virNodeGetInfo": (_I, (P, POINTER(NodeInfo))),
    "virNodeGetFreeMemory": (c_ulonglong, (P,)),
    "virNodeGetMemoryStats": (_I, (P, _I, POINTER(NodeMemoryStat), POINTER(_I), _U)),
    "virDomainDefineXML": (P, (P, _S)),
    "virDomainLookupByName": (P, (P, _S)),
    "virDomainFree": (_I, (P,)),
    "virDomainGetName": (_S, (P,)),
    "virDomainGetUUIDString": (_I, (P, _S)),
    "virDomainGetState": (_I, (P, POINTER(_I), POINTER(_I), _U)),
    "virDomainGetInfo": (_I, (P, POINTER(DomainInfo))),
    "virDomainGetXMLDesc": (P, (P, _U)),
    "virDomainGetAutostart": (_I, (P, POINTER(_I))),
    "virDomainSetAutostart": (_I, (P, _I)),
    "virDomainGetMaxMemory": (c_ulong, (P,)),
    "virDomainSetMemoryFlags": (_I, (P, c_ulong, _U)),
    "virDomainSetMemoryStatsPeriod": (_I, (P, _I, _U)),
    "virDomainMemoryStats": (_I, (P, POINTER(MemoryStat), _U, _U)),
    "virDomainSetVcpusFlags": (_I, (P, _U, _U)),
    "virDomainBlockStats": (_I, (P, _S, POINTER(BlockStats), c_size_t)),
    "virDomainInterfaceStats": (_I, (P, _S, POINTER(InterfaceStats), c_size_t)),
    "virDomainInterfaceAddresses": (_I, (P, POINTER(POINTER(POINTER(Interface))), _U, _U)),
    "virDomainInterfaceFree": (None, (POINTER(Interface),)),
    "virDomainScreenshot": (P, (P, P, _U, _U)),
    "virDomainSnapshotCreateXML": (P, (P, _S, _U)),
    "virDomainListAllSnapshots": (_I, (P, POINTER(POINTER(P)), _U)),
    "virDomainSnapshotGetName": (_S, (P,)),
    "virDomainSnapshotLookupByName": (P, (P, _S, _U)),
    "virDomainRevertToSnapshot": (_I, (P, _U)),
    "virDomainSnapshotDelete": (_I, (P, _U)),
    "virDomainSnapshotFree": (_I, (P,)),
    "virStreamNew": (P, (P, _U)),
    "virStreamRecv": (_I, (P, c_char_p, c_size_t)),
    "virStreamFinish": (_I, (P,)),
    "virStreamAbort": (_I, (P,)),
    "virStreamFree": (_I, (P,)),
}
for _name in ("Create", "Shutdown", "Destroy", "Suspend", "Resume", "Undefine"):
    SIGNATURES[f"virDomain{_name}"] = (_I, (P,))
for _name in ("Reboot", "Reset", "UndefineFlags"):
    SIGNATURES[f"virDomain{_name}"] = (_I, (P, _U))
for _name in ("AttachDeviceFlags", "DetachDeviceFlags", "UpdateDeviceFlags"):
    SIGNATURES[f"virDomain{_name}"] = (_I, (P, _S, _U))


@functools.cache
def lib() -> ctypes.CDLL:
    """Load ``libvirt.so.0`` and declare every prototype (raises ``OSError``)."""
    handle = ctypes.CDLL(LIBRARY)
    for name, (restype, argtypes) in SIGNATURES.items():
        function = getattr(handle, name)
        function.restype = restype
        function.argtypes = argtypes
    return handle


@functools.cache
def libc() -> ctypes.CDLL:
    handle = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
    handle.free.argtypes = (P,)
    handle.free.restype = None
    return handle


def take_string(pointer: int | None) -> str:
    """Copy a libvirt-allocated string and free it."""
    if not pointer:
        return ""
    try:
        return ctypes.string_at(pointer).decode()
    finally:
        libc().free(pointer)
