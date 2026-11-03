# Concurrency and resources

## Many machines, many threads

```python
from concurrent.futures import ThreadPoolExecutor
from azarovo_hyper import hyper

h = hyper()
machines = [h.kvm(f"node{i}", memory="1G") for i in range(8)]
with ThreadPoolExecutor(8) as pool:
    list(pool.map(lambda vm: vm.start(), machines))
```

* **Each machine has its own re-entrant lock.** Operations on one machine run
  one after another (so `memory.set()` from two threads cannot interleave);
  operations on different machines run in parallel.
* **One connection per URI**, shared by all machines on it. libvirt connections
  are thread-safe and the binding releases the GIL during calls, so threads
  really overlap. The pool only locks its own bookkeeping; opening a slow
  connection (e.g. a remote host) never delays other URIs.
* Waits (`start(wait=True)`, `shutdown()`, `wait_for()`) poll without holding
  any global lock, and `close()` from another thread interrupts them.
* CPU-load samplers are per machine, not global.

The test-suite proves this with a slow fake hypervisor (8 machines start in
less than half of the serial time), with 16-thread lifecycle stress tests on
the real libvirt test driver, with fork/forkserver/spawn process pools and
asyncio, and with parallel real KVM guests.

## Processes

Machine objects can be passed to a `ProcessPoolExecutor` (any start method):
they are pickled by identity, and the worker gets a fresh object bound to the
same guest, with its own connection.

```python
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor


def balloon(vm, size):
    return vm.memory.set(size)


machines = [h.kvm(f"node{i}").start() for i in range(4)]
ctx = mp.get_context("spawn")
with ProcessPoolExecutor(4, mp_context=ctx) as pool:
    print(list(pool.map(balloon, machines, ["1G", "1G", "2G", "2G"])))
```

Forking is safe too. In a forked child every inherited connection is
abandoned, never closed or reused (its destructor would send "close" over the
parent's socket), locks are recreated, and only the process that created an
`ephemeral` machine may delete it. Copies made by pickling are never
ephemeral.

## asyncio

Every call is blocking but releases the GIL, so `asyncio.to_thread` gives
real concurrency and keeps the event loop responsive:

```python
import asyncio


async def main():
    machines = [h.kvm(f"node{i}") for i in range(8)]
    await asyncio.gather(*(asyncio.to_thread(vm.start) for vm in machines))
    samples = await asyncio.gather(*(asyncio.to_thread(vm.metrics) for vm in machines))
    await asyncio.gather(*(asyncio.to_thread(vm.delete) for vm in machines))


asyncio.run(main())
```

`loop.run_in_executor(process_pool, ...)` works the same way. Cancelling a
task does not stop the thread; call `vm.close()` to interrupt a waiting
`start()`, `shutdown()` or `wait_for()`.

## What is released, and when

| Event | Released |
|---|---|
| `stop()` / `shutdown()` | connection lease, viewer windows, CPU-load history |
| reading `vm.state` of a stopped machine | the lease, if no other call is using the machine |
| `close()`, `with` block exit, `del vm`, garbage collection, interpreter exit | everything above; the guest keeps running |
| same, with `ephemeral=True` | everything above **and** the guest: powered off, undefined, its disks removed |
| `delete()` | the guest, its definition (with snapshot metadata, NVRAM, managed save), disks the library created, then `close()` |
| `Hyper.close()` / `with hyper() as h:` | `close()` of every machine created by it |

The connection itself closes as soon as the last lease on its URI is gone:

```python
from azarovo_hyper import default_pool

kvm1 = hyper().kvm().start()
default_pool().active()  # {'qemu:///session': 1}
kvm1.stop()
default_pool().active()  # {}
```

Implementation notes:

* the machine's controllers (`vm.memory`, `vm.cpu`, ...) hold only the
  session, never the machine, so `del kvm1` frees the object immediately by
  reference counting, without waiting for the cycle collector;
* cleanup is a `weakref.finalize` callback: it runs exactly once, from
  `close()`, garbage collection or `atexit`;
* failed operations roll back: a disk created for a domain that libvirt
  rejected, or for a hot-plug that failed, is removed again;
* using a closed object raises `VMClosedError` instead of touching a stale handle.
