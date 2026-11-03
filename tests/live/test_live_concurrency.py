"""Several real guests at once: they must not wait for each other."""

import time
from concurrent.futures import ThreadPoolExecutor

from live_helpers import qemu_processes

from azarovo_hyper import VMState

COUNT = 4


def test_parallel_guests(boot, live_pool):
    machines = [boot() for _ in range(COUNT)]
    started = time.monotonic()
    with ThreadPoolExecutor(COUNT) as pool:
        list(pool.map(lambda vm: vm.start(timeout=120), machines))
    parallel = time.monotonic() - started
    assert all(vm.state is VMState.RUNNING for vm in machines)
    assert live_pool.active() == {machines[0].uri: COUNT}

    def work(vm):
        vm.memory.set("180M")
        vm.memory.plug("128M")
        vm.cpu.set(2)
        for _ in range(3):
            vm.metrics()
        return vm.memory.maximum_mib

    with ThreadPoolExecutor(COUNT) as pool:
        assert list(pool.map(work, machines)) == [384.0] * COUNT

    with ThreadPoolExecutor(COUNT) as pool:
        list(pool.map(lambda vm: vm.delete(), machines))
    assert live_pool.active() == {}
    running = qemu_processes()
    assert not any(vm.name in running for vm in machines)
    print(f"{COUNT} guests started in parallel in {parallel:.2f}s")
