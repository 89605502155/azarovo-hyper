"""Shared fixtures: an in-memory hypervisor wired into a fresh ``Hyper``."""

from __future__ import annotations

import gc
from collections.abc import Iterator
from pathlib import Path

import pytest

from azarovo_hyper import Hyper, VirtualMachine
from azarovo_hyper.adapters.pool import ConnectionPool
from fakes import URI, FakeDiskTool, FakeHypervisor, fake_admission


@pytest.fixture(autouse=True)
def private_capacity_lock(tmp_path_factory, monkeypatch):
    """Never touch the real capacity lock of the user running the tests."""
    path = tmp_path_factory.mktemp("capacity") / "capacity.lock"
    monkeypatch.setenv("AZAROVO_LOCK", str(path))
    return path


@pytest.fixture
def fake() -> FakeHypervisor:
    return FakeHypervisor()


@pytest.fixture
def disks() -> FakeDiskTool:
    return FakeDiskTool()


@pytest.fixture
def pool(fake: FakeHypervisor) -> Iterator[ConnectionPool]:
    pool = ConnectionPool(fake.connect)
    yield pool
    pool.close_all()


@pytest.fixture
def hv(pool: ConnectionPool, disks: FakeDiskTool) -> Iterator[Hyper]:
    hyper = Hyper(pool=pool, disk_tool=disks, admission=fake_admission())
    yield hyper
    hyper.close()
    gc.collect()


@pytest.fixture
def make_vm(hv: Hyper, tmp_path: Path):
    """Factory for small KVM machines on the fake hypervisor."""

    def factory(name: str = "vm1", **options) -> VirtualMachine:
        options.setdefault("images_dir", tmp_path)
        options.setdefault("memory", "1G")
        options.setdefault("max_memory", "4G")
        return hv.kvm(name, uri=URI, **options)

    return factory


@pytest.fixture
def vm(make_vm) -> VirtualMachine:
    return make_vm()


@pytest.fixture
def running(vm: VirtualMachine) -> VirtualMachine:
    return vm.start(timeout=2)
