"""Keyword arguments accepted by ``hyper().kvm(...)`` and ``hyper().xen(...)``.

The keys mirror :class:`~azarovo_hyper.domain.spec.VMSpec`; the TypedDict only
exists so editors can complete them. A unit test keeps both in sync.
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from azarovo_hyper.domain.sizes import Size


class VMOptions(TypedDict, total=False):
    name: str
    title: str
    iso: str | Path | None
    disk: str | Path | None
    disk_size: Size
    disk_format: str
    disk_bus: str | None
    images_dir: str | Path | None
    memory: Size
    current_memory: Size | None
    min_memory: Size
    max_memory: Size
    memory_slots: int
    dimm_size: Size
    balloon_period: int
    balloon_autodeflate: bool
    free_page_reporting: bool
    vcpus: int
    max_vcpus: int | None
    cpu_mode: str
    arch: str
    machine: str | None
    firmware: str
    clock: str
    network: str
    nic_model: str | None
    graphics: str | None
    listen: str
    video: str | None
    video_heads: int
    usb_model: str | None
    pcie_ports: int
    guest_agent: bool
    autostart: bool
    ephemeral: bool
    template: str | Path | None
    extra_devices: tuple[str, ...]
