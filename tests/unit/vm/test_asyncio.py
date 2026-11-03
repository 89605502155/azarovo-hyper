"""asyncio: blocking calls go to threads, the event loop stays responsive."""

import asyncio
import itertools
import multiprocessing as mp
import time
from concurrent.futures import ProcessPoolExecutor

import pytest

from azarovo_hyper import Hyper, VMClosedError, VMState
from azarovo_hyper.adapters.pool import ConnectionPool
from fakes import URI, FakeDiskTool, FakeHypervisor, fake_admission
from fakes.workers import fake_lifecycle

DELAY = 0.1


async def heartbeat(ticks: list, stop: asyncio.Event) -> None:
    while not stop.is_set():
        ticks.append(time.monotonic())
        await asyncio.sleep(0.01)


def test_gather_many_machines_without_blocking_the_loop(tmp_path):
    fake = FakeHypervisor(delay=DELAY)
    hyper = Hyper(
        pool=ConnectionPool(fake.connect), disk_tool=FakeDiskTool(), admission=fake_admission()
    )
    machines = [hyper.kvm(f"a{i}", uri=URI, images_dir=tmp_path) for i in range(8)]

    async def main():
        ticks, stop = [], asyncio.Event()
        beat = asyncio.create_task(heartbeat(ticks, stop))
        started = time.monotonic()
        await asyncio.gather(*(asyncio.to_thread(vm.start, timeout=5) for vm in machines))
        await asyncio.gather(*(asyncio.to_thread(vm.memory.set, "512M") for vm in machines))
        samples = await asyncio.gather(*(asyncio.to_thread(vm.metrics) for vm in machines))
        elapsed = time.monotonic() - started
        stop.set()
        await beat
        return elapsed, ticks, samples

    elapsed, ticks, samples = asyncio.run(main())
    assert elapsed < 8 * 4 * DELAY / 2
    assert len(ticks) >= elapsed / 0.01 / 3, "event loop was blocked"
    assert max(b - a for a, b in itertools.pairwise(ticks)) < 0.2
    assert all(s.memory.actual_mib == 512 for s in samples)
    hyper.close()
    assert fake.open_connections == 0


def test_close_interrupts_a_waiting_task(make_vm):
    vm = make_vm("waiting").define()

    async def main():
        waiter = asyncio.create_task(asyncio.to_thread(vm.wait_for, VMState.RUNNING, timeout=30))
        await asyncio.sleep(0.1)
        started = time.monotonic()
        vm.close()
        with pytest.raises(VMClosedError):
            await waiter
        return time.monotonic() - started

    assert asyncio.run(main()) < 2


def test_run_in_process_executor():
    async def main():
        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor(3, mp_context=mp.get_context("spawn")) as pool:
            jobs = [loop.run_in_executor(pool, fake_lifecycle, i) for i in range(6)]
            return await asyncio.gather(*jobs)

    results = asyncio.run(main())
    assert all(r["actual"] == 300 and r["pool"] == {} for r in results)


def test_async_with_and_timeouts(make_vm):
    async def main():
        vm = make_vm("timed")
        await asyncio.wait_for(asyncio.to_thread(vm.start), timeout=5)
        await asyncio.to_thread(vm.delete)
        return vm

    vm = asyncio.run(main())
    assert vm.closed
