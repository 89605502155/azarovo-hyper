"""Read-only queries over a libvirt domain XML document."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

NAMESPACE = "https://github.com/89605502155/azarovo-hyper"

_TO_MIB = {"b": 1 / 1024**2, "bytes": 1 / 1024**2, "kib": 1 / 1024, "k": 1 / 1024}
_TO_MIB |= {"mib": 1, "m": 1, "gib": 1024, "g": 1024, "tib": 1024**2, "t": 1024**2}


def _size_mib(element: ET.Element | None) -> int:
    if element is None or not (element.text or "").strip():
        return 0
    factor = _TO_MIB.get(element.get("unit", "KiB").lower(), 1 / 1024)
    return round(int(element.text or 0) * factor)


@dataclass(frozen=True, slots=True)
class Cdrom:
    target: str
    bus: str
    source: str | None


@dataclass(frozen=True, slots=True)
class Graphics:
    type: str
    listen: str
    port: int

    @property
    def uri(self) -> str | None:
        return None if self.port <= 0 else f"{self.type}://{self.listen}:{self.port}"


class DomainXml:
    """Typed accessors for the parts of the XML the library cares about."""

    def __init__(self, xml: str) -> None:
        self.root = ET.fromstring(xml)

    @property
    def name(self) -> str:
        return self.root.findtext("name", "")

    def disks(self) -> dict[str, str]:
        """``{target: source path}`` of every hard disk."""
        found: dict[str, str] = {}
        for disk in self.root.findall("./devices/disk[@device='disk']"):
            target = disk.find("target")
            source = disk.find("source")
            if target is not None:
                found[target.get("dev", "")] = "" if source is None else source.get("file", "")
        return found

    def targets(self) -> set[str]:
        return {
            t.get("dev", "") for t in self.root.findall("./devices/disk/target") if t.get("dev")
        }

    def cdrom(self) -> Cdrom | None:
        disk = self.root.find("./devices/disk[@device='cdrom']")
        if disk is None:
            return None
        target = disk.find("target")
        source = disk.find("source")
        return Cdrom(
            target="" if target is None else target.get("dev", ""),
            bus="" if target is None else target.get("bus", ""),
            source=None if source is None else source.get("file"),
        )

    def dimms(self) -> list[int]:
        """Sizes (MiB) of hot-plugged DIMM modules, in device order."""
        return [
            _size_mib(mem.find("./target/size"))
            for mem in self.root.findall("./devices/memory[@model='dimm']")
        ]

    def graphics(self) -> list[Graphics]:
        result = []
        for item in self.root.findall("./devices/graphics"):
            listen = item.find("listen")
            address = item.get("listen") or (listen.get("address") if listen is not None else "")
            result.append(
                Graphics(
                    type=item.get("type", ""),
                    listen=address or "127.0.0.1",
                    port=int(item.get("port", "-1")),
                )
            )
        return result

    def interfaces(self) -> list[str]:
        """Host-side device names of network interfaces (``vnet0`` ...)."""
        return [
            t.get("dev", "")
            for t in self.root.findall("./devices/interface/target")
            if t.get("dev")
        ]

    def owns_disk(self) -> bool:
        managed = self.root.find(f"./metadata/{{{NAMESPACE}}}managed")
        return managed is not None and managed.get("owns-disk") == "yes"

    def spec_options(self) -> dict[str, Any]:
        """Options that let an adopted machine keep its own memory and CPU limits."""
        memory = _size_mib(self.root.find("memory")) - sum(self.dimms())
        current = _size_mib(self.root.find("currentMemory")) or memory
        vcpu = self.root.find("vcpu")
        max_vcpus = int((vcpu.text if vcpu is not None else None) or 1)
        current_vcpus = int(vcpu.get("current", max_vcpus)) if vcpu is not None else 1
        options: dict[str, Any] = {
            "memory": memory,
            "current_memory": min(current, memory),
            "min_memory": min(256, current, memory),
            "vcpus": current_vcpus,
            "max_vcpus": max_vcpus,
            "max_memory": memory,
            "memory_slots": 0,
        }
        top = self.root.find("maxMemory")
        if top is not None:
            options["max_memory"] = max(_size_mib(top), memory)
            options["memory_slots"] = int(top.get("slots", "0"))
        return options
