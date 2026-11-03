"""Every way a machine object can go away must give its resources back."""

import gc
import threading
import time

import pytest

from azarovo_hyper import VMClosedError, VMState
from fakes import URI


def test_stop_and_shutdown_release_the_connection(running, hv, fake):
    assert hv.pool.active() == {URI: 1}
    running.stop()
    assert hv.pool.active() == {}
    assert fake.open_connections == 0
    running.start()
    assert hv.pool.active() == {URI: 1}
    running.shutdown(timeout=1)
    assert hv.pool.active() == {}


def test_del_releases_everything(make_vm, hv, fake):
    vm = make_vm("gone").start()
    memory = vm.memory
    del vm
    gc.collect()
    assert hv.pool.active() == {}
    assert fake.open_connections == 0
    assert fake.domains(URI)["gone"].status is VMState.RUNNING
    with pytest.raises(VMClosedError):
        memory.stats()


def test_object_is_collected_without_gc(make_vm, hv):
    vm = make_vm("refcount").start()
    gc.disable()
    try:
        del vm
        assert hv.pool.active() == {}
    finally:
        gc.enable()


def test_close_is_idempotent_and_final(running, hv):
    running.close()
    running.close()
    assert running.closed
    assert running.state is VMState.UNDEFINED
    for call in (running.start, running.stop, running.define, lambda: running.memory.set(1)):
        with pytest.raises(VMClosedError):
            call()
    assert hv.pool.active() == {}


def test_with_block(make_vm, hv, fake):
    with make_vm("ctx").start() as vm:
        assert vm.is_running
    assert vm.closed
    assert fake.domains(URI)["ctx"].status is VMState.RUNNING
    assert hv.pool.active() == {}


def test_ephemeral_machine_is_deleted_on_close_and_gc(make_vm, hv, fake):
    with make_vm("temp1", ephemeral=True).start() as first:
        disk = first.disk_path
    assert "temp1" not in fake.domains(URI)
    assert not disk.exists()
    second = make_vm("temp2", ephemeral=True).start()
    disk = second.disk_path
    del second
    gc.collect()
    assert "temp2" not in fake.domains(URI)
    assert not disk.exists()
    assert hv.pool.active() == {}


def test_ephemeral_cleanup_failure_still_closes(make_vm, hv, monkeypatch, caplog):
    vm = make_vm("fragile", ephemeral=True).start()

    def broken(self):
        from azarovo_hyper import BackendError

        raise BackendError("libvirtd went away")

    monkeypatch.setattr("fakes.domain.FakeDomain.undefine", broken)
    vm.close()
    assert vm.closed
    assert "ephemeral cleanup failed" in caplog.text
    assert hv.pool.active() == {}


def test_close_interrupts_a_waiting_thread(vm):
    vm.define()
    errors = []

    def waiter():
        try:
            vm.wait_for(VMState.RUNNING, timeout=30)
        except VMClosedError as exc:
            errors.append(exc)

    thread = threading.Thread(target=waiter)
    started = time.monotonic()
    thread.start()
    time.sleep(0.1)
    vm.close()
    thread.join(timeout=5)
    assert errors and time.monotonic() - started < 3


def test_hyper_does_not_keep_machines_alive(make_vm, hv):
    make_vm("orphan").start()
    gc.collect()
    assert hv.machines == []
    assert hv.pool.active() == {}


def test_query_of_undefined_machine_holds_nothing(vm, hv):
    assert vm.state is VMState.UNDEFINED
    assert not vm.exists
    assert hv.pool.active() == {}
