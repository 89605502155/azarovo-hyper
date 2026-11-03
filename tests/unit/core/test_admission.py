"""RAM, CPU and disk are checked and reserved without races; failures leave nothing."""

import threading

import pytest

from azarovo_hyper import Hyper, InsufficientResourcesError, ResourcePolicy, VMState
from azarovo_hyper.adapters.pool import ConnectionPool
from fakes import URI, FakeDiskTool, FakeHypervisor, fake_admission


@pytest.fixture
def small(tmp_path):
    """A 4 GiB, 4-CPU host with 3 GiB of free disk."""
    fake = FakeHypervisor(total_mib=4096, cpus=4, delay=0.02)
    disks = FakeDiskTool()
    hyper = Hyper(
        pool=ConnectionPool(fake.connect), disk_tool=disks, admission=fake_admission(3072 + 1024)
    )

    def make(name, **options):
        options.setdefault("images_dir", tmp_path)
        options.setdefault("memory", "1G")
        options.setdefault("max_memory", "4G")
        options.setdefault("disk_size", "256M")
        return hyper.kvm(name, uri=URI, **options)

    yield fake, disks, hyper, make
    hyper.close()


def assert_nothing_left(fake, disks, vm, hyper):
    assert vm.name not in fake.domains(URI)
    assert not vm.disk_path.exists()
    assert hyper.pool.active() == {}


def test_too_much_memory_is_refused_before_anything_exists(small):
    fake, disks, hyper, make = small
    vm = make("big", memory="8G", max_memory="8G")
    with pytest.raises(InsufficientResourcesError) as info:
        vm.start()
    assert info.value.resources == {"memory"}
    assert disks.created == []
    assert_nothing_left(fake, disks, vm, hyper)


def test_more_vcpus_than_the_host_has(small):
    _fake, _disks, _hyper, make = small
    vm = make("wide", vcpus=5, max_vcpus=8)
    with pytest.raises(InsufficientResourcesError) as info:
        vm.start()
    assert "cpu" in info.value.resources
    running = make("ok", vcpus=2, max_vcpus=8).start()
    with pytest.raises(InsufficientResourcesError):
        running.cpu.set(5)
    assert running.cpu.count == 2
    assert running.cpu.set(4) == 4


def test_disk_space(small):
    fake, disks, hyper, make = small
    vm = make("huge-disk", disk_size="4G")
    with pytest.raises(InsufficientResourcesError) as info:
        vm.start()
    assert info.value.resources == {"disk"}
    assert_nothing_left(fake, disks, vm, hyper)
    ok = make("fits").start()
    with pytest.raises(InsufficientResourcesError):
        ok.storage.attach(size="3584M")
    assert set(ok.storage.disks()) == {"vda"}
    assert ok.storage.attach(size="1G") == "vdb"


def test_hot_plug_is_checked_but_ballooning_inside_the_ceiling_is_free(small):
    _fake, _disks, _hyper, make = small
    vm = make("grow", memory="1G", current_memory="1G", max_memory="4G").start()
    make("other", memory="2G", max_memory="2G").start()
    with pytest.raises(InsufficientResourcesError):
        vm.memory.plug("1G")
    assert vm.memory.dimms() == []
    assert vm.memory.plug("256M") == 1280
    assert vm.memory.set("1280M") == 1280, "growing inside the ceiling needs no check"


def test_concurrent_starts_never_overcommit(small):
    fake, _disks, _hyper, make = small
    machines = [make(f"race{i}") for i in range(10)]
    barrier = threading.Barrier(10)
    outcome = {}

    def go(vm):
        barrier.wait()
        try:
            vm.start(timeout=5)
            outcome[vm.name] = "started"
        except InsufficientResourcesError:
            outcome[vm.name] = "refused"

    threads = [threading.Thread(target=go, args=(vm,)) for vm in machines]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert list(outcome.values()).count("started") == 3
    running = [vm for vm in machines if vm.state is VMState.RUNNING]
    assert len(running) == 3
    for vm in machines:
        if outcome[vm.name] == "refused":
            assert vm.name not in fake.domains(URI) and not vm.disk_path.exists()


def test_hypervisor_refusal_at_the_last_moment_rolls_back(small):
    fake, disks, hyper, make = small
    fake.reject_start = True
    vm = make("late")
    with pytest.raises(InsufficientResourcesError):
        vm.start()
    assert_nothing_left(fake, disks, vm, hyper)
    fake.reject_start = False
    vm.define()
    fake.reject_start = True
    with pytest.raises(InsufficientResourcesError):
        vm.start()
    assert vm.name in fake.domains(URI), "an existing definition is kept"


def test_policy_options(small):
    _fake, _disks, _hyper, make = small
    vm = make("lax", memory="8G", max_memory="8G", check_resources=False)
    assert vm.start().is_running
    assert make("x", memory_overcommit=3).spec.resources.memory_overcommit == 3
    strict = Hyper(resources=ResourcePolicy(cpu_overcommit=1.5))
    assert strict.kvm("y", uri=URI).spec.resources.cpu_overcommit == 1.5
