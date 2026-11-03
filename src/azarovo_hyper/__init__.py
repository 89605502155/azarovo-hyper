"""azarovo-hyper: high-level control of KVM and Xen virtual machines.

>>> from azarovo_hyper import hyper
>>> kvm1 = hyper().kvm(iso="~/ubuntu.iso", preset="ubuntu").start()  # doctest: +SKIP
>>> kvm1.memory.set("3G")  # doctest: +SKIP
"""

import logging

from azarovo_hyper.adapters import ConnectionPool, QemuImg, default_pool, libvirt_available
from azarovo_hyper.config import preset_names
from azarovo_hyper.decorators import chainable, guarded, requires_running, retry, synchronized
from azarovo_hyper.domain import (
    DiskStats,
    GuestMetrics,
    HostInfo,
    InterfaceStats,
    MemoryStats,
    VMOptions,
    VMSpec,
    VMState,
    to_mib,
)
from azarovo_hyper.drivers import (
    Capabilities,
    HypervisorDriver,
    KvmDriver,
    XenDriver,
    driver_names,
    get_driver,
    register_driver,
)
from azarovo_hyper.errors import (
    BackendError,
    BackendUnavailableError,
    ConfigurationError,
    ConnectionFailedError,
    DiskError,
    DomainNotFoundError,
    HyperError,
    OperationTimeoutError,
    UnsupportedOperationError,
    VMClosedError,
    VMStateError,
)
from azarovo_hyper.hyper import Hyper, hyper
from azarovo_hyper.version import __version__
from azarovo_hyper.vm import VirtualMachine

logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "BackendError",
    "BackendUnavailableError",
    "Capabilities",
    "ConfigurationError",
    "ConnectionFailedError",
    "ConnectionPool",
    "DiskError",
    "DiskStats",
    "DomainNotFoundError",
    "GuestMetrics",
    "HostInfo",
    "Hyper",
    "HyperError",
    "HypervisorDriver",
    "InterfaceStats",
    "KvmDriver",
    "MemoryStats",
    "OperationTimeoutError",
    "QemuImg",
    "UnsupportedOperationError",
    "VMClosedError",
    "VMOptions",
    "VMSpec",
    "VMState",
    "VMStateError",
    "VirtualMachine",
    "XenDriver",
    "__version__",
    "chainable",
    "default_pool",
    "driver_names",
    "get_driver",
    "guarded",
    "hyper",
    "libvirt_available",
    "preset_names",
    "register_driver",
    "requires_running",
    "retry",
    "synchronized",
    "to_mib",
]
