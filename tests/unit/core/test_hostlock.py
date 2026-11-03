"""The host lock turns check-then-act into one step across threads and processes."""

import multiprocessing as mp
import threading
import time

import pytest

from azarovo_hyper.resources import HostLock, default_lock
from azarovo_hyper.resources.lock import default_path

CAPACITY = 3


def take_one(lock_path, counter_path) -> bool:
    """Read the counter, think, then write it: wrong without the lock."""
    with HostLock(lock_path).held():
        taken = int(counter_path.read_text() or 0)
        time.sleep(0.01)
        if taken >= CAPACITY:
            return False
        counter_path.write_text(str(taken + 1))
        return True


@pytest.fixture
def paths(tmp_path):
    counter = tmp_path / "taken"
    counter.write_text("0")
    return tmp_path / "capacity.lock", counter


def test_threads_never_overbook(paths):
    barrier, granted = threading.Barrier(12), []

    def worker():
        barrier.wait()
        granted.append(take_one(*paths))

    threads = [threading.Thread(target=worker) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert granted.count(True) == CAPACITY


def contend(lock_path, counter_path, barrier, results):
    barrier.wait(timeout=30)
    results.put(take_one(lock_path, counter_path))


@pytest.mark.parametrize("method", ["fork", "spawn"])
def test_processes_never_overbook(paths, method):
    ctx = mp.get_context(method)
    barrier, results = ctx.Barrier(8), ctx.Queue()
    procs = [ctx.Process(target=contend, args=(*paths, barrier, results)) for _ in range(8)]
    for p in procs:
        p.start()
    granted = [results.get(timeout=60) for _ in procs]
    for p in procs:
        p.join(timeout=30)
    assert granted.count(True) == CAPACITY


def test_lock_is_released_on_error(paths):
    lock = HostLock(paths[0])
    with pytest.raises(RuntimeError), lock.held():
        raise RuntimeError("boom")
    with lock.held():
        pass


def test_default_lock_follows_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("AZAROVO_LOCK", str(tmp_path / "a.lock"))
    first = default_lock()
    assert first.path == tmp_path / "a.lock" and default_lock() is first
    monkeypatch.delenv("AZAROVO_LOCK")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    assert default_path() == tmp_path / "azarovo-hyper" / "capacity.lock"
    assert default_lock() is not first
