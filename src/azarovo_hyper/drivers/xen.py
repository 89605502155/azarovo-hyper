"""Xen driver (libvirt libxl, ``xen:///system``)."""

from __future__ import annotations

from typing import Any

from azarovo_hyper.config.render import render
from azarovo_hyper.domain.spec import VMSpec
from azarovo_hyper.drivers.base import Capabilities, Hardware, HypervisorDriver
from azarovo_hyper.drivers.registry import register_driver
from azarovo_hyper.errors import ConfigurationError
from azarovo_hyper.ports.backend import Domain


@register_driver("xen")
class XenDriver(HypervisorDriver):
    """Xen HVM guests.

    Xen has no DIMM devices; memory "hot-plug" raises the domain's maximum
    memory live, and the xen balloon then grows the guest inside it.
    """

    domain_type = "xen"
    template = "xen.xml"
    capabilities = Capabilities(
        dimm_hotplug=False,
        live_max_memory=True,
        vcpu_hotplug=True,
        disk_hotplug=True,
        snapshots=False,
        screenshot=False,
    )
    hardware = Hardware(
        machine="xenfv",
        disk_bus="xen",
        nic_model=None,
        graphics="vnc",
        video="vga",
        usb_model="",
    )
    cdrom_boot_order = None

    def builtin_uri(self) -> str:
        return "xen:///system"

    def auto_network(self, uri: str) -> str:
        return "bridge:xenbr0"

    def cdrom_slot(self, spec: VMSpec) -> tuple[str, str]:
        return "hdc", "ide"

    def driver_values(self, spec: VMSpec) -> dict[str, Any]:
        if spec.graphics == "spice":
            raise ConfigurationError("the xen driver supports graphics 'vnc' or 'none'")
        graphics = render("devices/vnc.xml", listen=spec.listen) if spec.graphics == "vnc" else ""
        return {"graphics": graphics}

    def plug_memory(self, domain: Domain, size_mib: int, *, config: bool) -> None:
        domain.set_max_memory(domain.max_memory_kib() + size_mib * 1024, live=True, config=config)

    def unplug_memory(self, domain: Domain, size_mib: int, *, config: bool) -> None:
        domain.set_max_memory(domain.max_memory_kib() - size_mib * 1024, live=True, config=config)
