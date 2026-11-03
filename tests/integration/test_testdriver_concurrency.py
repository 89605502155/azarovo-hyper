"""Parallel work through one shared real libvirt connection."""

import threading
from concurrent.futures import ThreadPoolExecutor

from azarovo_hyper import VMState
from fakes import TEST_URI


def test_parallel_machines_share_one_connection(make, real_pool):
    machines = [make() for _ in range(12)]
    with ThreadPoolExecutor(12) as pool:
        list(pool.map(lambda vm: vm.start(timeout=10), machines))
    assert all(vm.state is VMState.RUNNING for vm in machines)
    assert real_pool.active() == {TEST_URI: 12}

    def churn(vm):
        for size in ("200M", "300M", "400M"):
            vm.memory.set(size)
            vm.cpu.set(3)
            vm.metrics()
        vm.shutdown(timeout=5)
        return vm.state

    with ThreadPoolExecutor(12) as pool:
        states = list(pool.map(churn, machines))
    assert states == [VMState.SHUTOFF] * 12
    assert real_pool.active() == {}


def test_parallel_create_and_delete(make, real_pool, keeper):
    errors = []
    barrier = threading.Barrier(10)

    def worker():
        try:
            barrier.wait()
            vm = make().start(timeout=10)
            vm.memory.set("256M")
            vm.delete()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert real_pool.active() == {}
    assert not [d for d in keeper.listAllDomains() if d.name().startswith("it-")]
