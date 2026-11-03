"""Native libvirt backend: the binding's API over ctypes and ``libvirt.so.0``.

Used by default, so ``uv add azarovo-hyper`` needs no compiler, no libvirt
headers and no ``libvirt-python``. The official binding can still be chosen
with ``AZAROVO_LIBVIRT_BACKEND=python``.
"""

from __future__ import annotations

from collections.abc import Callable
from ctypes import byref, c_ulong

from azarovo_hyper.adapters.native import library as _library
from azarovo_hyper.adapters.native.connection import virConnect
from azarovo_hyper.adapters.native.domain import virDomain
from azarovo_hyper.adapters.native.errors import libvirtError, ptr, silence_stderr

VIR_DOMAIN_AFFECT_LIVE = 1
VIR_DOMAIN_AFFECT_CONFIG = 2
VIR_DOMAIN_MEM_MAXIMUM = 4
VIR_DOMAIN_XML_INACTIVE = 2
VIR_DOMAIN_UNDEFINE_MANAGED_SAVE = 1
VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA = 2
VIR_DOMAIN_UNDEFINE_NVRAM = 4
VIR_DOMAIN_UNDEFINE_CHECKPOINTS_METADATA = 16
VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE = 0
VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT = 1
VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_ARP = 2
VIR_NODE_MEMORY_STATS_ALL_CELLS = -1
VIR_CONNECT_LIST_DOMAINS_ACTIVE = 1

VIR_ERR_NO_SUPPORT = 3
VIR_ERR_NO_CONNECT = 5
VIR_ERR_INVALID_CONN = 6
VIR_ERR_SYSTEM_ERROR = 38
VIR_ERR_RPC = 39
VIR_ERR_NO_DOMAIN = 42
VIR_ERR_AUTH_FAILED = 45
VIR_ERR_OPERATION_INVALID = 55
VIR_ERR_CONFIG_UNSUPPORTED = 67
VIR_ERR_OPERATION_TIMEOUT = 68
VIR_ERR_NO_DOMAIN_SNAPSHOT = 72
VIR_ERR_ARGUMENT_UNSUPPORTED = 74
VIR_ERR_OPERATION_UNSUPPORTED = 84
VIR_ERR_AGENT_UNRESPONSIVE = 86


def open(uri: str | None = None) -> virConnect:
    raw = _library.lib().virConnectOpen(uri.encode() if uri else None)
    return virConnect(ptr(raw, "virConnectOpen"))


def getVersion() -> int:  # noqa: N802
    version = c_ulong()
    _library.lib().virGetVersion(byref(version), None, None)
    return version.value


def registerErrorHandler(_handler: Callable[..., object], _context: object) -> int:  # noqa: N802
    """Errors are always raised; libvirt's own stderr printing is switched off."""
    silence_stderr()
    return 0


def available() -> bool:
    try:
        _library.lib()
    except OSError:
        return False
    return True


__all__ = ["libvirtError", "virConnect", "virDomain"]
