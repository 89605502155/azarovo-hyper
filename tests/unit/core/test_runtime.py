"""Fork safety: a child must never close, reuse or delete what belongs to its parent."""

import multiprocessing as mp
import subprocess
import sys
import threading
import time

import pytest

from azarovo_hyper.runtime import terminate
from fakes import URI

FORK = mp.get_context("fork")


def run_in_fork(target) -> int:
    process = FORK.Process(target=target)
    process.start()
    process.join(timeout=20)
    assert process.exitcode is not None, "child hung (inherited lock?)"
    return process.exitcode


def test_child_does_not_touch_parent_connections(hv, make_vm, fake):
    vm = make_vm("parent").start()
    lease_before = hv.pool.active()

    def child():
        assert hv.pool.active() == {}
        assert vm._session._lease is None
        vm.memory.set("512M")
        vm.close()
        sys.exit(0 if hv.pool.active() == {} else 3)

    assert run_in_fork(child) == 0
    assert hv.pool.active() == lease_before
    assert all(not c.is_closed for c in fake.connections)
    assert vm.memory.set("600M") == 600


def test_child_never_deletes_parent_ephemeral_machine(make_vm, fake):
    vm = make_vm("eph", ephemeral=True).start()

    def child():
        vm.close()
        alive = "eph" in fake.domains(URI) and vm.disk_path.exists()
        sys.exit(0 if alive else 4)

    assert run_in_fork(child) == 0
    assert vm.is_running and vm.disk_path.exists()
    vm.close()
    assert "eph" not in fake.domains(URI)


def test_lock_held_during_fork_does_not_deadlock_child(make_vm):
    vm = make_vm("locked").start()
    holding = threading.Event()

    def hold():
        with vm._session.lock:
            holding.set()
            time.sleep(1.0)

    thread = threading.Thread(target=hold)
    thread.start()
    holding.wait()

    def child():
        vm.memory.set("400M")
        sys.exit(0)

    with pytest.warns(DeprecationWarning) if sys.version_info >= (3, 12) else _nothing():
        assert run_in_fork(child) == 0
    thread.join()


class _nothing:  # noqa: N801 - tiny context manager
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_terminate_stops_stubborn_processes():
    quick = subprocess.Popen(["sleep", "30"])
    stubborn = subprocess.Popen(["sh", "-c", "trap '' TERM; sleep 30"])
    time.sleep(0.2)
    done = subprocess.Popen(["true"])
    done.wait()
    terminate([quick, stubborn, done], timeout=0.5)
    assert quick.poll() is not None and stubborn.poll() is not None
