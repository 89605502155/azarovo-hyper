import pytest

from azarovo_hyper import DomainNotFoundError, UnsupportedOperationError, VMState, VMStateError
from fakes import TEST_URI


def test_full_lifecycle_with_real_binding(make, lv, real_pool, keeper):
    vm = make(iso=None).start()
    assert vm.state is VMState.RUNNING
    assert vm.disk_path.read_bytes()[:4] == b"QFI\xfb"
    assert vm.name in lv.list(uri=TEST_URI)
    assert vm.memory.set("300M") == 300
    assert vm.memory.stats().actual_mib == 300
    assert vm.cpu.set(4) == 4
    assert vm.cpu.count == 4
    vm.cpu.usage()
    assert vm.storage.stats()["vda"].read_bytes >= 0
    assert vm.display.screenshot()[:4]
    vm.suspend()
    assert vm.state is VMState.PAUSED
    vm.resume().reboot().reset()
    vm.shutdown(timeout=5)
    assert vm.state is VMState.SHUTOFF
    assert real_pool.active() == {}
    vm.start()
    disk = vm.disk_path
    vm.delete()
    assert not disk.exists()
    assert vm.name not in [d.name() for d in keeper.listAllDomains()]
    assert real_pool.active() == {}


def test_snapshots_and_delete_with_snapshots(make):
    vm = make().start()
    vm.snapshots.create("one")
    vm.snapshots.create("two")
    assert vm.snapshots.names() == ["one", "two"]
    vm.snapshots.revert("one")
    vm.snapshots.delete("two")
    with pytest.raises(DomainNotFoundError):
        vm.snapshots.revert("two")
    vm.stop()
    vm.delete()


def test_live_cdrom_change(make, tmp_path):
    iso = tmp_path / "boot.iso"
    iso.write_bytes(b"\0" * 2048)
    vm = make(iso=iso).start()
    assert vm.storage.iso == iso
    try:
        vm.storage.eject()
    except UnsupportedOperationError:
        pytest.skip("this libvirt test driver has no virDomainUpdateDeviceFlags")
    assert vm.storage.iso is None


def test_live_disk_attach(make):
    vm = make().start()
    target = vm.storage.attach(size="8M", persist=False)
    assert target in vm.storage.disks()


def test_errors_are_translated(make, lv):
    vm = make()
    with pytest.raises(DomainNotFoundError):
        lv.get("no-such-domain", uri=TEST_URI)
    vm.define()
    with pytest.raises(VMStateError):
        vm.memory.set("200M")
    vm.start()
    with pytest.raises(UnsupportedOperationError):
        vm.memory.plug()


def test_adopt_existing_domain(make, lv):
    original = make(vcpus=1, max_vcpus=3).define()
    adopted = lv.get(original.name, uri=TEST_URI)
    assert adopted.spec.max_vcpus == 3
    assert adopted._session.owns_disk
    assert adopted.disk_path == original.disk_path
    adopted.close()


def test_host_and_network(make, lv):
    host = lv.host(uri=TEST_URI)
    assert host.hypervisor == "TEST" and host.cpus > 0
    vm = make(network="network:default").start()
    assert vm.network.interfaces()
    assert vm.network.stats()
    assert vm.network.addresses()
