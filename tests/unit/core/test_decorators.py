import threading
import time

import pytest

from azarovo_hyper import UnsupportedOperationError, VMClosedError, VMState, VMStateError
from azarovo_hyper.decorators import (
    alive,
    chainable,
    decorate_public_methods,
    guarded,
    requires_capability,
    requires_running,
    requires_state,
    retry,
    synchronized,
)


class Caps:
    snapshots = False
    memory = True


class Driver:
    name = "toy"
    capabilities = Caps()


class Session:
    name = "toy-vm"

    def __init__(self):
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.current = VMState.RUNNING
        self.driver = Driver()

    def state(self):
        return self.current


class Thing:
    def __init__(self):
        self._session = Session()
        self.log = []

    @chainable
    @guarded
    def touch(self, value):
        self.log.append(value)

    @alive
    def peek(self):
        return len(self.log)

    @requires_running
    def live_only(self):
        return "ok"

    @requires_state(VMState.SHUTOFF)
    def off_only(self):
        return "off"

    @requires_capability("snapshots")
    def snap(self):
        return "snap"

    @requires_capability("memory")
    def mem(self):
        return "mem"

    @synchronized
    def slow(self, seconds):
        time.sleep(seconds)


def test_chainable_and_alive():
    thing = Thing()
    assert thing.touch(1).touch(2) is thing
    assert thing.peek() == 2
    thing._session.closed.set()
    with pytest.raises(VMClosedError):
        thing.touch(3)
    with pytest.raises(VMClosedError):
        thing.peek()


def test_state_guards():
    thing = Thing()
    assert thing.live_only() == "ok"
    with pytest.raises(VMStateError, match="needs state shutoff"):
        thing.off_only()
    thing._session.current = VMState.SHUTOFF
    assert thing.off_only() == "off"
    with pytest.raises(VMStateError):
        thing.live_only()


def test_capability_guard():
    thing = Thing()
    assert thing.mem() == "mem"
    with pytest.raises(UnsupportedOperationError, match="toy"):
        thing.snap()


def test_synchronized_serialises_one_object_but_not_two():
    one, two = Thing(), Thing()
    start = time.monotonic()
    threads = [threading.Thread(target=t.slow, args=(0.2,)) for t in (one, two)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert time.monotonic() - start < 0.35
    start = time.monotonic()
    threads = [threading.Thread(target=one.slow, args=(0.15,)) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert time.monotonic() - start >= 0.29


def test_retry():
    calls = []

    @retry(times=3, delay=0, on=(ValueError,))
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError
        return "done"

    assert flaky() == "done"
    assert len(calls) == 3

    @retry(times=2, delay=0, on=(ValueError,))
    def broken():
        raise ValueError("always")

    with pytest.raises(ValueError, match="always"):
        broken()
    with pytest.raises(ValueError):
        retry(times=0)


def test_decorate_public_methods():
    def shout(func):
        return lambda *a, **k: str(func(*a, **k)).upper()

    @decorate_public_methods(shout)
    class Voice:
        def hello(self):
            return "hi"

        def _private(self):
            return "quiet"

        value = "attr"

    assert Voice().hello() == "HI"
    assert Voice()._private() == "quiet"
    assert Voice.value == "attr"
