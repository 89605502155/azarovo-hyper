"""Adapters: concrete implementations of the ports (libvirt, qemu-img)."""

from azarovo_hyper.adapters.disk import QemuImg
from azarovo_hyper.adapters.loader import libvirt_available, load_libvirt
from azarovo_hyper.adapters.pool import ConnectionPool, Lease, default_pool

__all__ = [
    "ConnectionPool",
    "Lease",
    "QemuImg",
    "default_pool",
    "libvirt_available",
    "load_libvirt",
]
