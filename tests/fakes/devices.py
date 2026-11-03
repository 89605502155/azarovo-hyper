"""Device, statistics and snapshot half of the fake domain."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from azarovo_hyper.errors import BackendError, DomainNotFoundError


def _size_kib(element: ET.Element) -> int:
    size = element.find("./target/size")
    assert size is not None
    factor = {"MiB": 1024, "KiB": 1, "GiB": 1024**2}[size.get("unit", "KiB")]
    return int(size.text or 0) * factor


class FakeDevices:
    """Mixed into ``FakeDomain``; relies on its ``tree`` and state helpers."""

    tree: ET.Element
    max_kib: int
    snaps: list[str]
    calls: list[str]
    _note: Any
    _active: Any

    def attach(self, xml: str, *, live: bool, config: bool) -> None:
        self._note("attach")
        if live:
            self._active("attach")
        element = ET.fromstring(xml)
        if element.tag == "memory":
            self.max_kib += _size_kib(element)
        devices = self.tree.find("devices")
        assert devices is not None
        devices.append(element)

    def detach(self, xml: str, *, live: bool, config: bool) -> None:
        element = ET.fromstring(xml)
        devices = self.tree.find("devices")
        assert devices is not None
        for candidate in list(devices):
            if element.tag == "memory" == candidate.tag:
                if _size_kib(candidate) == _size_kib(element):
                    devices.remove(candidate)
                    self.max_kib -= _size_kib(element)
                    return
            elif element.tag == "disk" == candidate.tag and _target(candidate) == _target(element):
                devices.remove(candidate)
                return
        raise BackendError("device not found")

    def update_device(self, xml: str, *, live: bool, config: bool) -> None:
        element = ET.fromstring(xml)
        devices = self.tree.find("devices")
        assert devices is not None
        for candidate in list(devices):
            if candidate.tag == "disk" and candidate.get("device") == "cdrom":
                index = list(devices).index(candidate)
                devices.remove(candidate)
                devices.insert(index, element)
                return
        raise BackendError("no cdrom")

    def block_stats(self, device: str) -> tuple[int, int, int, int, int]:
        self._active("block_stats")
        return 2, 1024, 1, 512, -1

    def interface_stats(self, device: str) -> tuple[int, ...]:
        self._active("interface_stats")
        return 10, 1, 0, 0, 20, 2, 0, 0

    def addresses(self) -> dict[str, list[str]]:
        self._active("addresses")
        return {"eth0": ["10.0.2.15"]}

    def screenshot(self, screen: int = 0) -> tuple[str, bytes]:
        self._active("screenshot")
        return "image/png", b"\x89PNG-fake"

    def snapshot_create(self, xml: str) -> None:
        self.snaps.append(ET.fromstring(xml).findtext("name") or "")

    def snapshot_names(self) -> list[str]:
        return sorted(self.snaps)

    def snapshot_revert(self, name: str) -> None:
        if name not in self.snaps:
            raise DomainNotFoundError(name)
        self.calls.append(f"revert={name}")

    def snapshot_delete(self, name: str) -> None:
        if name not in self.snaps:
            raise DomainNotFoundError(name)
        self.snaps.remove(name)


def _target(element: ET.Element) -> str | None:
    target = element.find("target")
    return None if target is None else target.get("dev")
