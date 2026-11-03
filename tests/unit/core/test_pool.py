import threading

import pytest

from azarovo_hyper import ConnectionFailedError
from azarovo_hyper.adapters.pool import ConnectionPool, default_pool
from fakes import FakeHypervisor


def test_one_connection_per_uri_refcounted():
    fake = FakeHypervisor()
    pool = ConnectionPool(fake.connect)
    a, b = pool.acquire("u1"), pool.acquire("u1")
    c = pool.acquire("u2")
    assert a.connection is b.connection
    assert pool.active() == {"u1": 2, "u2": 1}
    a.release()
    a.release()
    assert pool.refcount("u1") == 1
    b.release()
    c.release()
    assert pool.active() == {}
    assert fake.open_connections == 0
    assert fake.opened == fake.closed


def test_released_lease_refuses_use():
    pool = ConnectionPool(FakeHypervisor().connect)
    lease = pool.acquire("u")
    lease.release()
    assert lease.released
    with pytest.raises(ConnectionFailedError):
        _ = lease.connection


def test_context_manager():
    fake = FakeHypervisor()
    pool = ConnectionPool(fake.connect)
    with pool.acquire("u") as connection:
        assert connection.names() == []
    assert fake.open_connections == 0


def test_failed_open_does_not_leak_a_reference():
    fake = FakeHypervisor()
    fake.fail_connect = True
    pool = ConnectionPool(fake.connect)
    with pytest.raises(ConnectionFailedError):
        pool.acquire("u")
    assert pool.active() == {}


def test_dead_connection_is_reopened():
    fake = FakeHypervisor()
    pool = ConnectionPool(fake.connect)
    first = pool.acquire("u")
    first.connection.alive = False
    second = pool.acquire("u")
    assert fake.opened["u"] == 2
    assert first.connection is second.connection
    pool.close_all()
    assert fake.open_connections == 0


def test_parallel_acquire_release_is_consistent():
    fake = FakeHypervisor()
    pool = ConnectionPool(fake.connect)
    barrier = threading.Barrier(16)

    def worker(index):
        barrier.wait()
        for _ in range(200):
            pool.acquire(f"u{index % 4}").release()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert pool.active() == {}
    assert fake.open_connections == 0


def test_default_pool_is_a_singleton():
    assert default_pool() is default_pool()
