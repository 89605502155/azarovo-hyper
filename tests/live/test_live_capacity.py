"""Real host limits: refusals leave nothing behind, races never overcommit RAM."""

import multiprocessing as mp
import threading

import pytest
from live_helpers import qemu_processes

from azarovo_hyper import InsufficientResourcesError, ResourcePolicy, VMState
from azarovo_hyper.domain.resources import memory_headroom
from fakes.workers import contend_live

RACERS = 6


def headroom_share(live, uri: str, parts: float) -> int:
    with live.pool.acquire(uri) as connection:
        usage = connection.usage()
    return int(memory_headroom(usage, ResourcePolicy()) / parts)


@pytest.mark.parametrize(
    ("options", "resource"),
    [
        ({"memory": "1T", "max_memory": "1T"}, "memory"),
        ({"vcpus": 4096, "max_vcpus": 4096}, "cpu"),
        ({"disk_size": "100T"}, "disk"),
    ],
)
def test_host_limits_are_enforced(boot, live, options, resource, tmp_path):
    vm = boot(**options)
    with pytest.raises(InsufficientResourcesError) as info:
        vm.start()
    assert resource in info.value.resources
    assert vm.name not in live.list(uri=vm.uri)
    assert list(tmp_path.iterdir()) == []
    assert live.pool.active() == {}


def test_disks_are_really_reserved(boot):
    vm = boot(disk_size="64M").define()
    assert vm.disk_path.stat().st_blocks * 512 >= 64 * 1024 * 1024


def test_threads_racing_for_memory(boot, live):
    uri = boot().uri
    size = headroom_share(live, uri, 3.5)
    machines = [boot(memory=size, max_memory=size, disk_size="32M") for _ in range(RACERS)]
    barrier, outcome = threading.Barrier(RACERS), []

    def go(vm):
        barrier.wait()
        try:
            vm.start(timeout=60)
            outcome.append("started")
        except InsufficientResourcesError:
            outcome.append("refused")

    threads = [threading.Thread(target=go, args=(vm,)) for vm in machines]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    running = [vm for vm in machines if vm.state is VMState.RUNNING]
    assert 2 <= outcome.count("started") <= 3, outcome
    assert len(running) == outcome.count("started")
    for vm in machines:
        if vm not in running:
            assert not vm.exists and not vm.disk_path.exists()


def test_processes_racing_for_memory(boot, live, tmp_path):
    uri = boot().uri
    size = headroom_share(live, uri, 3.5)
    ctx = mp.get_context("spawn")
    barrier, results = ctx.Barrier(RACERS), ctx.Queue()
    procs = [
        ctx.Process(target=contend_live, args=(uri, size, str(tmp_path), barrier, results))
        for _ in range(RACERS)
    ]
    for p in procs:
        p.start()
    outcome = [results.get(timeout=180) for _ in procs]
    for p in procs:
        p.join(timeout=180)
    assert 2 <= outcome.count("started") <= 3, outcome
    assert not [p for p in procs if p.exitcode != 0]
    assert "cap-" not in qemu_processes()
    assert list(tmp_path.glob("*.qcow2")) == []
