import pytest

from azarovo_hyper import OperationTimeoutError, VMState, VMStateError


def test_start_defines_disk_and_domain(vm, fake, disks):
    assert vm.start(timeout=1) is vm
    assert vm.state is VMState.RUNNING
    assert vm.is_running and vm.exists
    assert disks.created == [vm.disk_path]
    domain = fake.domains(vm.uri)[vm.name]
    assert "<maxMemory" in vm.xml
    assert len(domain.tree.findall("./devices/controller[@model='pcie-root-port']")) == 4
    assert vm.uuid == f"uuid-{vm.name}"


def test_start_is_idempotent_and_resumes(running, fake):
    running.start()
    assert fake.domains(running.uri)[running.name].calls.count("start") == 1
    running.suspend()
    assert running.state is VMState.PAUSED
    running.start()
    assert running.state is VMState.RUNNING
    running.suspend().resume().resume()
    assert running.state is VMState.RUNNING


def test_define_adopts_existing_domain(make_vm, disks):
    make_vm("same").define()
    other = make_vm("same")
    other.define()
    assert len(disks.created) == 1
    assert other._session.owns_disk


def test_define_rolls_back_disk_on_failure(vm, disks, monkeypatch, fake):
    def broken(*_a, **_k):
        raise RuntimeError("bad xml")

    monkeypatch.setattr("fakes.connection.FakeConnection.define", broken)
    with pytest.raises(RuntimeError):
        vm.define()
    assert disks.removed == [vm.disk_path]
    assert not vm.disk_path.exists()


def test_shutdown_clean_and_forced(make_vm, fake):
    clean = make_vm("clean").start()
    assert clean.shutdown(timeout=1) is clean
    assert clean.state is VMState.SHUTOFF
    fake.guest_obeys_acpi = False
    stubborn = make_vm("stubborn").start()
    stubborn.shutdown(timeout=0.3)
    assert stubborn.state is VMState.SHUTOFF
    assert "destroy" in fake.domains(stubborn.uri)["stubborn"].calls
    stubborn.start()
    with pytest.raises(OperationTimeoutError):
        stubborn.shutdown(timeout=0.2, force=False)


def test_shutdown_of_stopped_or_undefined_machine(vm):
    vm.shutdown()
    vm.stop()
    vm.define().shutdown().stop()
    assert vm.state is VMState.SHUTOFF


def test_restart_reboot_reset(running, fake):
    calls = fake.domains(running.uri)[running.name].calls
    running.reboot().reset()
    assert calls[-2:] == ["reboot", "reset"]
    running.restart(timeout=1)
    assert running.is_running
    running.stop()
    with pytest.raises(VMStateError, match="needs state running"):
        running.reboot()


def test_wait_for_timeout(vm):
    vm.define()
    with pytest.raises(OperationTimeoutError):
        vm.wait_for(VMState.RUNNING, timeout=0.1)
    assert vm.wait_for(VMState.SHUTOFF) is vm


def test_autostart(make_vm):
    vm = make_vm("auto", autostart=True).define()
    assert vm.autostart
    vm.autostart = False
    assert not vm.autostart


def test_delete_removes_everything(running, fake, disks, hv):
    disk = running.disk_path
    running.delete()
    assert running.closed
    assert running.state is VMState.UNDEFINED
    assert running.name not in fake.domains(running.uri)
    assert not disk.exists()
    assert hv.pool.active() == {}


def test_delete_keeps_foreign_disk(make_vm, tmp_path):
    disk = tmp_path / "mine.qcow2"
    disk.write_text("data")
    vm = make_vm("foreign", disk=disk).start()
    assert not vm._session.owns_disk
    vm.delete()
    assert disk.exists()
    vm2 = make_vm("forced", disk=disk).start()
    vm2.delete(remove_disk=True)
    assert not disk.exists()


def test_repr(vm):
    assert "vm1" in repr(vm) and "undefined" in repr(vm)
