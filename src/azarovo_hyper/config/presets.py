"""Ready-made hardware presets for common guest systems.

A preset only supplies defaults: anything passed explicitly wins, e.g.
``hyper().kvm(preset="ubuntu", memory="8G")``.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from azarovo_hyper.errors import ConfigurationError

_LEGACY_PC: dict[str, Any] = {
    "machine": "pc",
    "disk_bus": "ide",
    "video": "vga",
    "graphics": "vnc",
    "usb_model": "piix3-uhci",
    "guest_agent": False,
    "cpu_mode": "host-model",
}

PRESETS: Mapping[str, Mapping[str, Any]] = MappingProxyType(
    {
        "linux": {},
        "ubuntu": {
            "memory": "4G",
            "current_memory": "2G",
            "min_memory": "1536M",
            "disk_size": "25G",
        },
        "fedora": {
            "memory": "4G",
            "current_memory": "2148M",
            "min_memory": "1850M",
            "disk_size": "25G",
        },
        "debian": {"memory": "2G", "min_memory": "512M", "disk_size": "20G"},
        "alpine": {
            "memory": "512M",
            "min_memory": "128M",
            "disk_size": "4G",
            "vcpus": 1,
        },
        "windows": {
            "memory": "4G",
            "min_memory": "2G",
            "disk_size": "64G",
            "disk_bus": "sata",
            "nic_model": "e1000e",
            "video": "qxl",
            "clock": "localtime",
            "firmware": "efi",
        },
        "reactos": {
            **_LEGACY_PC,
            "arch": "i686",
            "memory": "1G",
            "max_memory": "3G",
            "min_memory": "512M",
            "disk_size": "8G",
            "nic_model": "rtl8139",
            "usb_model": "pci-ohci",
            "clock": "localtime",
        },
        "redox": {
            **_LEGACY_PC,
            "memory": "2G",
            "min_memory": "1G",
            "disk_size": "8G",
            "nic_model": "e1000",
            "usb_model": "nec-xhci",
        },
    }
)


def preset(name: str | None) -> dict[str, Any]:
    """Options of a preset (a fresh dict), or ``{}`` for ``None``."""
    if name is None:
        return {}
    try:
        return dict(PRESETS[name.lower()])
    except KeyError:
        known = ", ".join(sorted(PRESETS))
        raise ConfigurationError(f"unknown preset {name!r}; known presets: {known}") from None


def preset_names() -> list[str]:
    return sorted(PRESETS)
