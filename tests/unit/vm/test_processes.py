"""Process pools: each worker drives its own machines; objects survive pickling."""

import multiprocessing as mp
import pickle
import time
from concurrent.futures import ProcessPoolExecutor
from functools import partial

import pytest

from fakes.workers import fake_lifecycle

METHODS = ["fork", "forkserver", "spawn"]


@pytest.mark.parametrize("method", METHODS)
def test_process_pool_lifecycles(method):
    with ProcessPoolExecutor(4, mp_context=mp.get_context(method)) as pool:
        results = list(pool.map(fake_lifecycle, range(8)))
    assert len({r["pid"] for r in results}) > 1
    for r in results:
        assert (r["vcpus"], r["actual"]) == (3, 300)
        assert r["connections"] == 0 and r["pool"] == {}


def test_processes_run_in_parallel():
    delay = 0.1
    work = partial(fake_lifecycle, delay=delay)
    with ProcessPoolExecutor(4, mp_context=mp.get_context("fork")) as pool:
        list(pool.map(work, range(4)))
        started = time.monotonic()
        list(pool.map(work, range(4)))
        elapsed = time.monotonic() - started
    one_machine = 9 * delay
    assert elapsed < 4 * one_machine / 2, f"{elapsed:.2f}s - processes ran one by one"


def test_machine_pickles_by_identity(make_vm):
    vm = make_vm("pick", ephemeral=True, vcpus=3)
    copy = pickle.loads(pickle.dumps(vm))
    assert copy is not vm
    assert (copy.name, copy.uri, copy.hypervisor) == (vm.name, vm.uri, "kvm")
    assert copy.spec.vcpus == 3
    assert copy.spec.ephemeral is False and vm.spec.ephemeral is True
    assert copy._session is not vm._session
    copy.close()
    assert not vm.closed
