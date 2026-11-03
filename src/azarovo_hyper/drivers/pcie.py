"""PCIe root-port bookkeeping for q35 machines (needed for hot-plug)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

_PORT = "pcie-root-port"


def free_root_ports(xml: str) -> list[int]:
    """Indexes of ``pcie-root-port`` controllers with nothing plugged into them."""
    root = ET.fromstring(xml)
    ports = {
        int(c.get("index", "-1"))
        for c in root.findall("./devices/controller[@type='pci']")
        if c.get("model") == _PORT
    }
    used = {
        int(address.get("bus", "0"), 0)
        for address in root.findall("./devices/*/address[@type='pci']")
    }
    return sorted(ports - used)


def add_root_ports(xml: str, count: int) -> str:
    """Domain XML with ``count`` more empty root ports."""
    root = ET.fromstring(xml)
    devices = root.find("devices")
    if devices is None:
        raise ValueError("domain XML has no <devices>")
    for _ in range(count):
        ET.SubElement(devices, "controller", {"type": "pci", "model": _PORT})
    return ET.tostring(root, encoding="unicode")
