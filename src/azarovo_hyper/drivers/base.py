"""Common machinery of hypervisor drivers.

A driver knows how one hypervisor wants its XML, which URI and directories
to use by default and which operations it supports. Adding a hypervisor means
subclassing :class:`HypervisorDriver` and registering it with
:func:`~azarovo_hyper.drivers.registry.register_driver`.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from azarovo_hyper.config.render import Markup, render, xml_escape
from azarovo_hyper.domain.spec import VMSpec
from azarovo_hyper.domain.xml_view import NAMESPACE
from azarovo_hyper.drivers.network import interface_xml, parse_network
from azarovo_hyper.ports.backend import Connection, Domain
from azarovo_hyper.version import __version__

TARGET_PREFIX = {"virtio": "vd", "sata": "sd", "scsi": "sd", "usb": "sd", "ide": "hd", "xen": "xvd"}


@dataclass(frozen=True, slots=True)
class Capabilities:
    """What a driver can do on a live machine."""

    dimm_hotplug: bool = False
    live_max_memory: bool = False
    vcpu_hotplug: bool = True
    disk_hotplug: bool = True
    snapshots: bool = False
    screenshot: bool = False


@dataclass(frozen=True, slots=True)
class Hardware:
    """Values used for ``VMSpec`` fields that were left as ``None``."""

    machine: str
    disk_bus: str
    nic_model: str | None
    graphics: str
    video: str
    usb_model: str


def next_target(bus: str, used: set[str]) -> str:
    """First free device name for ``bus``: ``vda``, ``vdb``, ... ``sdz``."""
    prefix = TARGET_PREFIX.get(bus, "sd")
    for letter in "abcdefghijklmnopqrstuvwxyz":
        if f"{prefix}{letter}" not in used:
            return f"{prefix}{letter}"
    raise ValueError(f"no free {bus} device names left")


class HypervisorDriver(ABC):
    """Base class of every hypervisor driver."""

    name: ClassVar[str]
    domain_type: ClassVar[str]
    template: ClassVar[str]
    capabilities: ClassVar[Capabilities]
    hardware: ClassVar[Hardware]

    # ── defaults ────────────────────────────────────────────────────────────
    def default_uri(self) -> str:
        """``AZAROVO_<NAME>_URI`` from the environment, else the driver default."""
        return os.environ.get(f"AZAROVO_{self.name.upper()}_URI") or self.builtin_uri()

    @abstractmethod
    def builtin_uri(self) -> str: ...

    @abstractmethod
    def auto_network(self, uri: str) -> str: ...

    def default_images_dir(self, uri: str) -> Path:
        if os.geteuid() == 0 and "session" not in uri:
            return Path("/var/lib/libvirt/images")
        data_home = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
        return Path(data_home) / "azarovo-hyper" / "images"

    def resolve(self, spec: VMSpec) -> VMSpec:
        """Fill every ``None`` hardware field with this driver's default."""
        changes = {
            key: getattr(self.hardware, key)
            for key in ("machine", "disk_bus", "nic_model", "graphics", "video", "usb_model")
            if getattr(spec, key) is None
        }
        return spec.with_(**changes) if changes else spec

    # ── XML ─────────────────────────────────────────────────────────────────
    def render_domain(self, spec: VMSpec, *, disk_path: Path, owns_disk: bool, uri: str) -> str:
        spec = self.resolve(spec)
        values = self.common_values(spec, disk_path=disk_path, owns_disk=owns_disk, uri=uri)
        values.update(self.driver_values(spec))
        return render(spec.template or self.template, **values)

    def common_values(
        self, spec: VMSpec, *, disk_path: Path, owns_disk: bool, uri: str
    ) -> dict[str, Any]:
        network = parse_network(spec.network, self.auto_network(uri))
        title = f"  <title>{xml_escape(spec.title)}</title>" if spec.title else ""
        firmware = " firmware='efi'" if spec.firmware == "efi" else ""
        bus = spec.disk_bus or self.hardware.disk_bus
        return {
            "domain_type": self.domain_type,
            "name": spec.name,
            "title": Markup(title),
            "namespace": NAMESPACE,
            "version": __version__,
            "owns_disk": "yes" if owns_disk else "no",
            "memory": spec.memory_mib,
            "current_memory": spec.current_memory_mib,
            "vcpus": spec.vcpus,
            "max_vcpus": spec.effective_max_vcpus,
            "arch": spec.arch,
            "machine": spec.machine,
            "firmware": Markup(firmware),
            "cpu_mode": spec.cpu_mode,
            "clock": spec.clock,
            "disk": self.disk_xml(disk_path, next_target(bus, set()), bus, spec.disk_format, 2),
            "cdrom": self.cdrom_xml(spec, spec.iso_path),
            "interface": interface_xml(network, spec.nic_model),
            "video": spec.video,
            "video_heads": spec.video_heads,
            "extra_devices": Markup("\n".join(spec.extra_devices)),
        }

    @abstractmethod
    def driver_values(self, spec: VMSpec) -> dict[str, Any]: ...

    def boot_markup(self, order: int | None) -> Markup:
        return Markup(f"\n      <boot order='{order}'/>" if order else "")

    def disk_xml(
        self, path: Path, target: str, bus: str, fmt: str = "qcow2", boot: int | None = None
    ) -> Markup:
        discard = " discard='unmap'" if bus in ("virtio", "scsi", "sata") else ""
        return render(
            "devices/disk.xml",
            format=fmt,
            discard=Markup(discard),
            path=path,
            target=target,
            bus=bus,
            boot=self.boot_markup(boot),
        )

    @abstractmethod
    def cdrom_slot(self, spec: VMSpec) -> tuple[str, str]:
        """``(target, bus)`` of the always-present CD-ROM drive."""

    def cdrom_xml(self, spec: VMSpec, iso: Path | None) -> Markup:
        target, bus = self.cdrom_slot(self.resolve(spec))
        source = f"\n      <source file='{xml_escape(iso)}'/>" if iso else ""
        return render(
            "devices/cdrom.xml",
            source=Markup(source),
            target=target,
            bus=bus,
            boot=self.boot_markup(self.cdrom_boot_order),
        )

    cdrom_boot_order: ClassVar[int | None] = 1

    def finalize_definition(self, connection: Connection, domain: Domain, spec: VMSpec) -> Domain:
        """Hook run right after the first definition; may redefine the domain."""
        return domain

    # ── memory hot-plug strategy ────────────────────────────────────────────
    @abstractmethod
    def plug_memory(self, domain: Domain, size_mib: int, *, config: bool) -> None: ...

    @abstractmethod
    def unplug_memory(self, domain: Domain, size_mib: int, *, config: bool) -> None: ...
