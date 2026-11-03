"""KVM/QEMU driver (libvirt ``qemu://`` URIs)."""

from __future__ import annotations

import os
from typing import Any

from azarovo_hyper.config.render import Markup, join, render
from azarovo_hyper.domain.spec import VMSpec
from azarovo_hyper.drivers.base import Capabilities, Hardware, HypervisorDriver, next_target
from azarovo_hyper.drivers.pcie import add_root_ports, free_root_ports
from azarovo_hyper.drivers.registry import register_driver
from azarovo_hyper.ports.backend import Connection, Domain

_PCIE_ROOT = "    <controller type='pci' index='0' model='pcie-root'/>"


def dimm_xml(size_mib: int) -> str:
    return str(render("devices/dimm.xml", size=size_mib))


@register_driver("kvm")
class KvmDriver(HypervisorDriver):
    """Hardware-accelerated QEMU guests."""

    domain_type = "kvm"
    template = "kvm.xml"
    capabilities = Capabilities(
        dimm_hotplug=True,
        live_max_memory=False,
        vcpu_hotplug=True,
        disk_hotplug=True,
        snapshots=True,
        screenshot=True,
    )
    hardware = Hardware(
        machine="q35",
        disk_bus="virtio",
        nic_model="virtio",
        graphics="spice",
        video="virtio",
        usb_model="qemu-xhci",
    )

    def builtin_uri(self) -> str:
        return "qemu:///system" if os.geteuid() == 0 else "qemu:///session"

    def auto_network(self, uri: str) -> str:
        """User-mode networking needs no privileges, so it is the session default."""
        return "user" if "session" in uri else "network:default"

    @staticmethod
    def is_pcie(spec: VMSpec) -> bool:
        return "q35" in (spec.machine or "q35")

    def cdrom_slot(self, spec: VMSpec) -> tuple[str, str]:
        if not self.is_pcie(spec):
            return "hdc", "ide"
        disk_bus = spec.disk_bus or self.hardware.disk_bus
        used = {next_target(disk_bus, set())} if disk_bus in ("sata", "scsi", "usb") else set()
        return next_target("sata", used), "sata"

    def driver_values(self, spec: VMSpec) -> dict[str, Any]:
        max_memory = ""
        if spec.memory_hotplug:
            max_memory = (
                f"  <maxMemory slots='{spec.memory_slots}' unit='MiB'>"
                f"{spec.max_memory_mib}</maxMemory>"
            )
        balloon = ""
        if spec.balloon_autodeflate:
            balloon += " autodeflate='on'"
        if spec.free_page_reporting:
            balloon += " freePageReporting='on'"
        last = spec.effective_max_vcpus - 1
        ports = [_PCIE_ROOT] if self.is_pcie(spec) else []
        return {
            "max_memory": Markup(max_memory),
            "cpu_range": f"0-{last}" if last else "0",
            "pcie_ports": join(ports),
            "usb_model": spec.usb_model,
            "graphics": self.graphics_xml(spec),
            "agent": render("devices/agent.xml") if spec.guest_agent else Markup(""),
            "balloon_attrs": Markup(balloon),
            "balloon_period": spec.balloon_period,
        }

    @staticmethod
    def graphics_xml(spec: VMSpec) -> Markup:
        if spec.graphics in ("spice", "vnc"):
            return render(f"devices/{spec.graphics}.xml", listen=spec.listen)
        return Markup("")

    def finalize_definition(self, connection: Connection, domain: Domain, spec: VMSpec) -> Domain:
        """Reserve ``pcie_ports`` empty root ports for disk and NIC hot-plug.

        libvirt places existing devices on root ports first, so the spare ones
        can only be counted after the first definition.
        """
        if not self.is_pcie(spec):
            return domain
        missing = spec.pcie_ports - len(free_root_ports(domain.xml(inactive=True)))
        if missing <= 0:
            return domain
        return connection.define(add_root_ports(domain.xml(inactive=True), missing))

    def plug_memory(self, domain: Domain, size_mib: int, *, config: bool) -> None:
        domain.attach(dimm_xml(size_mib), live=True, config=config)

    def unplug_memory(self, domain: Domain, size_mib: int, *, config: bool) -> None:
        domain.detach(dimm_xml(size_mib), live=True, config=config)
