import time

from live_helpers import qemu_processes

from azarovo_hyper import VMState


def test_everything_on_a_real_guest(boot, live, live_pool, tmp_path):
    vm = boot().start(timeout=60)
    assert vm.state is VMState.RUNNING
    assert vm.display.uri.startswith("spice://127.0.0.1:")

    assert vm.memory.set("200M") == 200
    assert vm.memory.plug("128M") == 384
    assert vm.memory.dimms() == [128]
    assert vm.cpu.set(3) == 3
    assert vm.cpu.count == 3
    vm.cpu.usage()
    time.sleep(0.3)
    assert 0 <= vm.cpu.usage() <= 100

    target = vm.storage.attach(size="32M")
    assert target == "vdb"
    assert set(vm.storage.stats()) == {"vda", "vdb"}
    vm.storage.detach(target)

    assert vm.display.screenshot(tmp_path / "screen")
    assert vm.snapshots.create("clean") == "clean"
    sample = vm.metrics()
    assert sample.memory.actual_mib > 0 and sample.vcpus == 3

    vm.stop()
    assert vm.state is VMState.SHUTOFF
    assert live_pool.active() == {}
    vm.start(timeout=60)
    vm.delete()
    assert live_pool.active() == {}
    assert vm.name not in live.list(uri=vm.uri)
    assert list(tmp_path.glob("*.qcow2")) == []
    assert vm.name not in qemu_processes()


def test_ephemeral_guest_leaves_nothing_behind(boot, live_pool):
    with boot(ephemeral=True).start(timeout=60) as vm:
        name = vm.name
        disk = vm.disk_path
        assert vm.name in qemu_processes()
    assert not disk.exists()
    assert name not in qemu_processes()
    assert live_pool.active() == {}


def test_shutdown_of_guest_without_os_falls_back_to_power_off(boot):
    vm = boot().start(timeout=60)
    started = time.monotonic()
    vm.shutdown(timeout=2)
    assert vm.state is VMState.SHUTOFF
    assert time.monotonic() - started < 15
