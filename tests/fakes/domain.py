"""In-memory implementation of the ``Domain`` port."""

from __future__ import annotations

import threading
import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING

from azarovo_hyper.domain.state import VMState
from azarovo_hyper.errors import (
    BackendError,
    DomainNotFoundError,
    InsufficientResourcesError,
    VMStateError,
)
from fakes.devices import FakeDevices

if TYPE_CHECKING:
    from fakes.connection import FakeHypervisor


class FakeDomain(FakeDevices):
    def __init__(self, hypervisor: FakeHypervisor, uri: str, xml: str) -> None:
        self.hv = hypervisor
        self.uri = uri
        self.tree = ET.fromstring(xml)
        self.status = VMState.SHUTOFF
        self.memory_kib = int(self.tree.findtext("currentMemory") or 0) * 1024
        self.max_kib = int(self.tree.findtext("memory") or 0) * 1024
        vcpu = self.tree.find("vcpu")
        self.max_vcpus = int(vcpu.text or 1) if vcpu is not None else 1
        self.current_vcpus = int(vcpu.get("current", self.max_vcpus)) if vcpu is not None else 1
        self.cpu_time = 0
        self.auto = False
        self.snaps: list[str] = []
        self.calls: list[str] = []
        self.lock = threading.Lock()

    # helpers
    def _check(self) -> None:
        if self.hv.domains(self.uri).get(self.name) is not self:
            raise DomainNotFoundError(f"no domain {self.name}")

    def _active(self, op: str) -> None:
        self._check()
        if not self.status.is_active:
            raise VMStateError(f"{op}: domain is not running")

    def _note(self, op: str) -> None:
        self.calls.append(op)
        self.hv.busy(op)

    @property
    def name(self) -> str:
        return self.tree.findtext("name") or ""

    @property
    def uuid(self) -> str:
        return f"uuid-{self.name}"

    def state(self) -> VMState:
        self._check()
        return self.status

    def start(self) -> None:
        self._note("start")
        self._check()
        if self.status.is_active:
            raise VMStateError("already running")
        if self.hv.reject_start:
            raise InsufficientResourcesError("qemu: cannot set up guest memory")
        self.status = VMState.RUNNING

    def shutdown(self) -> None:
        self._note("shutdown")
        self._active("shutdown")
        if self.hv.guest_obeys_acpi:
            self.status = VMState.SHUTOFF

    def destroy(self) -> None:
        self._note("destroy")
        self._active("destroy")
        self.status = VMState.SHUTOFF

    def reboot(self) -> None:
        self._active("reboot")
        self.calls.append("reboot")

    def reset(self) -> None:
        self._active("reset")
        self.calls.append("reset")

    def suspend(self) -> None:
        self._active("suspend")
        self.status = VMState.PAUSED

    def resume(self) -> None:
        self._active("resume")
        self.status = VMState.RUNNING

    def undefine(self) -> None:
        self._note("undefine")
        self._check()
        del self.hv.domains(self.uri)[self.name]

    def xml(self, *, inactive: bool = False) -> str:
        self._check()
        return ET.tostring(self.tree, encoding="unicode")

    def autostart(self) -> bool:
        return self.auto

    def set_autostart(self, enabled: bool) -> None:
        self.auto = enabled

    def max_memory_kib(self) -> int:
        self._check()
        return self.max_kib

    def set_memory(self, kib: int, *, live: bool, config: bool) -> None:
        self._note("set_memory")
        if live:
            self._active("set_memory")
        if kib > self.max_kib:
            raise BackendError("cannot set memory higher than max memory")
        self.memory_kib = kib

    def set_max_memory(self, kib: int, *, live: bool, config: bool) -> None:
        self._check()
        self.max_kib = kib

    def memory_stats(self) -> dict[str, int]:
        self._check()
        if not self.status.is_active:
            return {}
        return {"actual": self.memory_kib, "rss": self.memory_kib // 4, "usable": 100 * 1024}

    def set_stats_period(self, seconds: int, *, live: bool, config: bool) -> None:
        self.calls.append(f"period={seconds}")

    def vcpus(self) -> int:
        self._check()
        return self.current_vcpus

    def set_vcpus(self, count: int, *, live: bool, config: bool) -> None:
        if live:
            self._active("set_vcpus")
        self.current_vcpus = count

    def cpu_time_ns(self) -> int:
        self._active("cpu_time")
        self.cpu_time += 50_000_000
        return self.cpu_time
