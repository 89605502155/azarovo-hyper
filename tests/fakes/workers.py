"""Functions run inside child processes (importable by spawn/forkserver)."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from azarovo_hyper import Hyper, QemuImg, ResourcePolicy, VirtualMachine
from azarovo_hyper.adapters.pool import ConnectionPool
from azarovo_hyper.resources import Admission
from fakes.connection import FakeDiskTool, FakeHypervisor

URI = "fake:///session"
TEST_URI = "test:///default"


def _workout(vm: VirtualMachine) -> dict:
    vm.start(timeout=10)
    vm.memory.set("300M")
    vm.cpu.set(3)
    sample = vm.metrics()
    return {"pid": os.getpid(), "vcpus": sample.vcpus, "actual": sample.memory.actual_mib}


def fake_lifecycle(index: int, delay: float = 0.0) -> dict:
    """A full machine lifecycle on a private in-memory hypervisor."""
    fake = FakeHypervisor(delay=delay)
    images = Path(tempfile.mkdtemp(prefix="azarovo-proc-"))
    admission = Admission(free_space=lambda _path: 10**7)
    hyper = Hyper(pool=ConnectionPool(fake.connect), disk_tool=FakeDiskTool(), admission=admission)
    with hyper:
        vm = hyper.kvm(f"proc{index}", uri=URI, images_dir=images, memory="1G")
        result = _workout(vm)
        vm.memory.plug()
        vm.delete()
        pool_left = hyper.pool.active()
    images.rmdir()
    return {**result, "connections": fake.open_connections, "pool": pool_left}


def lifecycle_on_testdriver(index: int) -> dict:
    """The same through the real libvirt binding (each process has its own test driver)."""
    import libvirt

    keeper = libvirt.open(TEST_URI)
    images = Path(tempfile.mkdtemp(prefix="azarovo-proc-"))
    try:
        pool = ConnectionPool()
        policy = ResourcePolicy(memory_overcommit=16)
        hyper = Hyper(pool=pool, disk_tool=QemuImg(), resources=policy)
        name = f"proc{index}-{uuid.uuid4().hex[:6]}"
        vm = hyper.kvm(name, uri=TEST_URI, images_dir=images, disk_size="8M", memory="512M")
        result = _workout(vm)
        vm.delete()
        result["left"] = [d.name() for d in keeper.listAllDomains() if d.name() == name]
        result["pool"] = pool.active()
        result["files"] = sorted(p.name for p in images.iterdir())
        return result
    finally:
        keeper.close()
        images.rmdir()


def control_pickled(vm: VirtualMachine, size: str) -> dict:
    """Receive a machine object from the parent and drive the same guest."""
    applied = vm.memory.set(size)
    return {"pid": os.getpid(), "applied": applied, "state": str(vm.state)}


def boot_live(index: int, uri: str) -> dict:
    """Boot, drive and delete a real KVM guest from a child process."""
    images = Path(tempfile.mkdtemp(prefix="azarovo-live-"))
    try:
        with Hyper() as hyper:
            vm = hyper.kvm(
                f"plive{index}-{uuid.uuid4().hex[:6]}",
                uri=uri,
                images_dir=images,
                disk_size="32M",
                memory="256M",
                min_memory="128M",
                max_memory="1G",
                vcpus=1,
            )
            try:
                result = _workout(vm)
                vm.memory.plug("128M")
                result["maximum"] = vm.memory.maximum_mib
                result["name"] = vm.name
            finally:
                vm.delete(remove_disk=True)
            result["files"] = sorted(p.name for p in images.iterdir())
            return result
    finally:
        for leftover in images.iterdir():
            leftover.unlink()
        images.rmdir()


def contend_live(uri: str, size_mib: int, images: str, barrier, results) -> None:
    """Try to start a guest of ``size_mib``; hold it until every process has tried."""
    from azarovo_hyper import InsufficientResourcesError

    vm = Hyper().kvm(
        f"cap-{uuid.uuid4().hex[:6]}",
        uri=uri,
        images_dir=images,
        disk_size="32M",
        memory=size_mib,
        max_memory=size_mib,
        min_memory="128M",
        vcpus=1,
    )
    try:
        vm.start(timeout=60)
        results.put("started")
    except InsufficientResourcesError:
        results.put("refused")
    barrier.wait(timeout=120)
    if vm.exists:
        vm.delete()
