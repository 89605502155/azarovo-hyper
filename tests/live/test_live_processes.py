"""Real KVM guests driven from forked children, process pools and asyncio."""

import asyncio
import itertools
import multiprocessing as mp
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from live_helpers import qemu_processes

from azarovo_hyper import VMState
from fakes.workers import boot_live, control_pickled


def test_forked_child_cannot_break_or_delete_parent_guest(boot, live_pool):
    vm = boot(ephemeral=True).start(timeout=60)

    def child():
        vm.memory.set("200M")
        vm.close()
        sys.exit(0)

    process = mp.get_context("fork").Process(target=child)
    process.start()
    process.join(timeout=60)
    assert process.exitcode == 0
    assert vm.state is VMState.RUNNING
    assert vm.disk_path.exists()
    assert vm.memory.set("220M") == 220
    vm.close()
    assert vm.name not in qemu_processes()
    assert live_pool.active() == {}


def test_pickled_guests_controlled_from_process_pool(boot):
    machines = [boot().start(timeout=60) for _ in range(3)]
    sizes = ["150M", "170M", "190M"]
    with ProcessPoolExecutor(3, mp_context=mp.get_context("spawn")) as pool:
        results = list(pool.map(control_pickled, machines, sizes))
    assert [r["applied"] for r in results] == [150, 170, 190]
    assert all(r["state"] == "running" for r in results)
    assert len({r["pid"] for r in results}) > 1
    # the parent's own objects keep working after the children used the guests
    assert [vm.memory.set("200M") for vm in machines] == [200, 200, 200]
    assert all(vm.state is VMState.RUNNING for vm in machines)


def test_each_process_boots_its_own_guest(boot):
    uri = boot().uri
    with ProcessPoolExecutor(4, mp_context=mp.get_context("spawn")) as pool:
        results = list(pool.map(partial(boot_live, uri=uri), range(4)))
    assert len({r["pid"] for r in results}) > 1
    for r in results:
        # no OS means no balloon driver: the guest keeps its boot size
        assert (r["vcpus"], r["actual"], r["maximum"], r["files"]) == (3, 256, 384, [])
    running = qemu_processes()
    assert not any(r["name"] in running for r in results)


def test_asyncio_drives_real_guests(boot, live_pool):
    machines = [boot() for _ in range(4)]

    async def main():
        ticks = []

        async def beat():
            while len(ticks) < 10_000:
                ticks.append(time.monotonic())
                await asyncio.sleep(0.01)

        heartbeat = asyncio.create_task(beat())
        await asyncio.gather(*(asyncio.to_thread(vm.start, timeout=60) for vm in machines))
        await asyncio.gather(*(asyncio.to_thread(vm.memory.plug, "128M") for vm in machines))
        samples = await asyncio.gather(*(asyncio.to_thread(vm.metrics) for vm in machines))
        await asyncio.gather(*(asyncio.to_thread(vm.delete) for vm in machines))
        heartbeat.cancel()
        return samples, ticks

    samples, ticks = asyncio.run(main())
    assert all(s.state is VMState.RUNNING and s.memory.actual_mib > 0 for s in samples)
    gaps = [b - a for a, b in itertools.pairwise(ticks)]
    assert max(gaps) < 0.5, "event loop was blocked by a hypervisor call"
    assert live_pool.active() == {}
