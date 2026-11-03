"""Process pools and asyncio with the real libvirt binding."""

import asyncio
import multiprocessing as mp
import sys
from concurrent.futures import ProcessPoolExecutor

import pytest

from fakes.workers import lifecycle_on_testdriver


@pytest.mark.parametrize("method", ["fork", "forkserver", "spawn"])
def test_process_pool_with_real_binding(method, make):
    parent_vm = make().start()
    with ProcessPoolExecutor(3, mp_context=mp.get_context(method)) as pool:
        results = list(pool.map(lifecycle_on_testdriver, range(6)))
    for r in results:
        assert (r["vcpus"], r["actual"]) == (3, 300)
        assert r["left"] == [] and r["pool"] == {} and r["files"] == []
    assert parent_vm.memory.set("256M") == 256
    assert parent_vm.is_running


def test_forked_child_keeps_parent_connection_usable(make, real_pool):
    vm = make(ephemeral=True).start()

    def child():
        vm.memory.set("200M")
        vm.close()
        sys.exit(0)

    process = mp.get_context("fork").Process(target=child)
    process.start()
    process.join(timeout=30)
    assert process.exitcode == 0
    assert vm.is_running
    assert vm.memory.set("300M") == 300
    assert real_pool.active() == {vm.uri: 1}


def test_asyncio_with_real_binding(make):
    machines = [make() for _ in range(6)]

    async def main():
        await asyncio.gather(*(asyncio.to_thread(vm.start) for vm in machines))
        sizes = await asyncio.gather(*(asyncio.to_thread(vm.memory.set, "200M") for vm in machines))
        await asyncio.gather(*(asyncio.to_thread(vm.delete) for vm in machines))
        return sizes

    assert asyncio.run(main()) == [200] * 6
    assert all(vm.closed for vm in machines)
