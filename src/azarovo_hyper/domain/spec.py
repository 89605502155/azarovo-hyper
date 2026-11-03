"""Machine specification: every knob has a default, so ``VMSpec()`` is valid.

Fields left as ``None`` are filled in by the hypervisor driver (KVM and Xen
pick different video cards, disk buses and so on).
"""

from __future__ import annotations

import dataclasses
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from azarovo_hyper.domain.sizes import Size, to_mib
from azarovo_hyper.errors import ConfigurationError

_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}")
FIRMWARES = ("bios", "efi")
GRAPHICS = ("spice", "vnc", "none")


def generated_name() -> str:
    return f"azarovo-{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True, slots=True, kw_only=True)
class VMSpec:
    """Everything needed to define one virtual machine."""

    name: str = field(default_factory=generated_name)
    title: str = ""
    iso: str | Path | None = None
    disk: str | Path | None = None
    disk_size: Size = "20G"
    disk_format: str = "qcow2"
    disk_bus: str | None = None
    images_dir: str | Path | None = None

    memory: Size = "2G"
    current_memory: Size | None = None
    min_memory: Size = "256M"
    max_memory: Size = "8G"
    memory_slots: int = 16
    dimm_size: Size = "128M"
    balloon_period: int = 1
    balloon_autodeflate: bool = False
    free_page_reporting: bool = False

    vcpus: int = 2
    max_vcpus: int | None = None
    cpu_mode: str = "host-passthrough"
    arch: str = "x86_64"
    machine: str | None = None
    firmware: str = "bios"
    clock: str = "utc"

    network: str = "auto"
    nic_model: str | None = None
    graphics: str | None = None
    listen: str = "127.0.0.1"
    video: str | None = None
    video_heads: int = 1
    usb_model: str | None = None
    pcie_ports: int = 4
    guest_agent: bool = True

    autostart: bool = False
    ephemeral: bool = False
    template: str | Path | None = None
    extra_devices: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _NAME.fullmatch(self.name):
            raise ConfigurationError(
                f"invalid machine name {self.name!r}: use letters, digits and _.+- (max 64)"
            )
        if "\n" in self.title:
            raise ConfigurationError("title must be a single line")
        self._check_memory()
        self._check_cpu()
        self._check_choices()

    def _check_memory(self) -> None:
        low, cur, boot, top = (
            self.min_memory_mib,
            self.current_memory_mib,
            self.memory_mib,
            self.max_memory_mib,
        )
        if boot <= 0:
            raise ConfigurationError("memory must be positive")
        if not low <= cur <= boot:
            raise ConfigurationError(
                f"need min_memory <= current_memory <= memory, got {low} / {cur} / {boot} MiB"
            )
        if top < boot:
            raise ConfigurationError(f"max_memory ({top} MiB) is below memory ({boot} MiB)")
        if self.memory_slots < 0:
            raise ConfigurationError("memory_slots must be >= 0")
        if self.dimm_mib < 2:
            raise ConfigurationError("dimm_size must be at least 2 MiB")
        if self.balloon_period < 0:
            raise ConfigurationError("balloon_period must be >= 0")
        if self.disk_size_mib <= 0:
            raise ConfigurationError("disk_size must be positive")

    def _check_cpu(self) -> None:
        if self.vcpus < 1:
            raise ConfigurationError("vcpus must be >= 1")
        if self.max_vcpus is not None and self.max_vcpus < self.vcpus:
            raise ConfigurationError(f"max_vcpus ({self.max_vcpus}) is below vcpus ({self.vcpus})")

    def _check_choices(self) -> None:
        if self.firmware not in FIRMWARES:
            raise ConfigurationError(f"firmware must be one of {FIRMWARES}")
        if self.graphics is not None and self.graphics not in GRAPHICS:
            raise ConfigurationError(f"graphics must be one of {GRAPHICS}")
        if self.video_heads < 1 or self.pcie_ports < 0:
            raise ConfigurationError("video_heads must be >= 1 and pcie_ports >= 0")
        if isinstance(self.extra_devices, str):
            raise ConfigurationError("extra_devices must be a tuple of XML strings")

    # ── derived values ──────────────────────────────────────────────────────
    @property
    def memory_mib(self) -> int:
        return to_mib(self.memory)

    @property
    def current_memory_mib(self) -> int:
        if self.current_memory is None:
            return self.memory_mib
        return to_mib(self.current_memory)

    @property
    def min_memory_mib(self) -> int:
        return to_mib(self.min_memory)

    @property
    def max_memory_mib(self) -> int:
        return to_mib(self.max_memory)

    @property
    def dimm_mib(self) -> int:
        return to_mib(self.dimm_size)

    @property
    def disk_size_mib(self) -> int:
        return to_mib(self.disk_size)

    @property
    def effective_max_vcpus(self) -> int:
        """Upper bound for vCPU hot-plug: ``max_vcpus`` or ``max(vcpus, 8)``."""
        return self.max_vcpus if self.max_vcpus is not None else max(self.vcpus, 8)

    @property
    def iso_path(self) -> Path | None:
        return None if self.iso is None else Path(self.iso).expanduser().absolute()

    @property
    def memory_hotplug(self) -> bool:
        return self.memory_slots > 0 and self.max_memory_mib > self.memory_mib

    def disk_path(self, default_dir: Path) -> Path:
        """Disk image path: explicit ``disk`` or ``<images_dir>/<name>.<format>``."""
        if self.disk is not None:
            return Path(self.disk).expanduser().absolute()
        base = Path(self.images_dir).expanduser() if self.images_dir else default_dir
        return (base / f"{self.name}.{self.disk_format}").absolute()

    def with_(self, **changes: Any) -> VMSpec:
        """Copy of the spec with some fields replaced (validated again)."""
        return dataclasses.replace(self, **changes)


def spec_fields() -> frozenset[str]:
    return frozenset(f.name for f in dataclasses.fields(VMSpec))
