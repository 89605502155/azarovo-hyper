"""Hypervisor drivers. Importing this package registers KVM and Xen."""

from azarovo_hyper.drivers import kvm, xen
from azarovo_hyper.drivers.base import Capabilities, Hardware, HypervisorDriver
from azarovo_hyper.drivers.registry import driver_names, get_driver, register_driver

KvmDriver = kvm.KvmDriver
XenDriver = xen.XenDriver

__all__ = [
    "Capabilities",
    "Hardware",
    "HypervisorDriver",
    "KvmDriver",
    "XenDriver",
    "driver_names",
    "get_driver",
    "register_driver",
]
