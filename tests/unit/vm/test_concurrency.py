"""Many machines at once: they must run in parallel and never corrupt shared state."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

from azarovo_hyper import Hyper, VMState
from azarovo_hyper.adapters.pool import ConnectionPool
from fakes import URI, FakeDiskTool, FakeHypervisor, fake_admission

DELAY = 0.1


def slow_hyper():
    fake = FakeHypervisor(delay=DELAY)
    return fake, Hyper(
        pool=ConnectionPool(fake.connect), disk_tool=FakeDiskTool(), admission=fake_admission()
    )


def test_machines_start_in_parallel(tmp_path):
    fake, hyper = slow_hyper()
    machines = [hyper.kvm(f"p{i}", uri=URI, images_dir=tmp_path) for i in range(8)]
    started = time.monotonic()
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda vm: vm.start(timeout=5), machines))
    elapsed = time.monotonic() - started
    serial = 8 * 3 * DELAY
    assert elapsed < serial / 2, f"{elapsed:.2f}s - machines blocked each other"
    assert fake.max_parallel >= 4
    assert all(vm.state is VMState.RUNNING for vm in machines)
    assert hyper.pool.active() == {URI: 8}
    hyper.close()
    assert fake.open_connections == 0


def test_operations_on_one_machine_are_serialised(tmp_path):
    fake, hyper = slow_hyper()
    vm = hyper.kvm("one", uri=URI, images_dir=tmp_path, memory="1G").start()
    fake.max_parallel = 0
    with ThreadPoolExecutor(4) as pool:
        sizes = list(pool.map(vm.memory.set, ["300M", "400M", "500M", "600M"]))
    assert sizes == [300, 400, 500, 600]
    assert fake.max_parallel == 1
    assert vm.memory.current_mib in (300, 400, 500, 600)
    hyper.close()


def test_slow_operation_on_one_machine_does_not_block_another(tmp_path):
    fake, hyper = slow_hyper()
    busy = hyper.kvm("busy", uri=URI, images_dir=tmp_path).start()
    free = hyper.kvm("free", uri=URI, images_dir=tmp_path).start()
    fake.guest_obeys_acpi = False
    thread = threading.Thread(target=lambda: busy.shutdown(timeout=1.0))
    thread.start()
    time.sleep(0.05)
    started = time.monotonic()
    free.memory.set("512M")
    assert free.state is VMState.RUNNING
    assert time.monotonic() - started < 0.6
    thread.join()
    hyper.close()


def test_slow_uri_does_not_block_other_uris():
    def connector(uri):
        if uri == "slow:///":
            time.sleep(0.5)
        return fake.connect(uri)

    fake = FakeHypervisor()
    pool = ConnectionPool(connector)
    thread = threading.Thread(target=lambda: pool.acquire("slow:///").release())
    thread.start()
    time.sleep(0.05)
    started = time.monotonic()
    pool.acquire("fast:///").release()
    assert time.monotonic() - started < 0.2
    thread.join()
    assert pool.active() == {}


def test_full_lifecycle_stress(tmp_path):
    fake = FakeHypervisor(delay=0.002)
    hyper = Hyper(
        pool=ConnectionPool(fake.connect), disk_tool=FakeDiskTool(), admission=fake_admission()
    )
    barrier = threading.Barrier(16)
    errors = []

    def worker(index):
        try:
            barrier.wait()
            uri = URI if index % 2 else "fake:///xen"
            make = hyper.kvm if index % 2 else hyper.xen
            vm = make(f"s{index}", uri=uri, images_dir=tmp_path, memory="1G").start()
            for _ in range(5):
                vm.memory.set("700M")
                vm.cpu.plug()
                vm.cpu.unplug()
                vm.metrics()
            vm.memory.plug("128M")
            vm.stop().start()
            vm.delete()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []
    assert fake.domains(URI) == {} and fake.domains("fake:///xen") == {}
    assert hyper.pool.active() == {}
    assert fake.open_connections == 0
    assert list(tmp_path.iterdir()) == []
