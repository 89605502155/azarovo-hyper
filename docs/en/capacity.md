# Host capacity: RAM, CPU and disk without races

Before anything is created or grown, the library checks that the host can
give it and **takes** it in the same atomic step. If not,
`InsufficientResourcesError` is raised and nothing is left behind: no disk
image, no domain definition, no held connection.

```python
from azarovo_hyper import InsufficientResourcesError, hyper

try:
    vm = hyper().kvm(memory="64G", disk_size="2T", vcpus=128).start()
except InsufficientResourcesError as error:
    print(error)  # not enough host resources: memory: requested ...
    for s in error.shortfalls:  # Shortfall(resource, requested, available)
        print(s.resource, s.requested, s.available)
    print(error.resources)  # {'memory', 'disk', 'cpu'}
```

## What is checked

| Operation | RAM | vCPU | Disk |
|---|---|---|---|
| `start()` | the guest's ceiling (`memory` + plugged DIMMs) | `vcpus` (total and per machine) | `disk_size` of a new image |
| `memory.plug()` | the plugged size | | |
| `cpu.set()` | | the increase; never more than host CPUs | |
| `storage.attach(size=...)` | | | the new image |

* **RAM headroom** = what the host has available − `host_memory_reserve` −
  what running guests may still take (their ceiling minus what they already use).
  A guest is counted at its ceiling because the balloon can grow it up to that
  at any moment; that is also why `memory.set()` needs no check.
* **CPU headroom** = host CPUs × `cpu_overcommit` − vCPUs of running guests.
  A single machine never gets more vCPUs than the host has.
* **Disk headroom** = free space on the target file system − `host_disk_reserve`.

## Why there is no race

The naive flow "check, then create" breaks when two callers check at the same
time and both see the same free memory. Here measuring the host, checking the
demand and the hypervisor call that takes the resource (`create`, vCPU or DIMM
hot-plug, disk preallocation) run under one exclusive host-wide lock (`flock`),
so it holds across **threads and processes**. When the lock is released the
hypervisor already reports the resource as used, so the next caller sees it:
nothing is counted twice and there are no reservations to expire. The lock
covers only that single call — booting the guest happens outside it — so
machines still start in parallel.

The kernel is the last line of defence against programs that do not take the
lock:

* disks are created with `disk_preallocation="falloc"`, so the space is
  allocated by the file system at creation time; a full disk fails immediately;
* `memory_prealloc=True` makes QEMU allocate all guest RAM at start;
* such late refusals from QEMU or `qemu-img` are translated into the same
  `InsufficientResourcesError`, and a machine that `start()` had just defined is
  rolled back.

## Policy

```python
from azarovo_hyper import ResourcePolicy, hyper

vm = hyper().kvm(memory_overcommit=1.5, cpu_overcommit=8, host_memory_reserve="2G")
h = hyper(resources=ResourcePolicy(cpu_overcommit=2))  # default for every machine
lab = h.kvm(check_resources=False)  # opt out for one machine
```

| Option | Default | Meaning |
|---|---|---|
| `check_resources` | `True` | switch the checks off |
| `memory_overcommit` | `1.0` | 1.0 never promises more RAM than the host has |
| `cpu_overcommit` | `4.0` | running vCPUs per host CPU |
| `host_memory_reserve` | `"512M"` | RAM always left to the host |
| `host_disk_reserve` | `"1G"` | disk space always left free |
| `disk_preallocation` | `"falloc"` | `off` (thin qcow2), `metadata`, `falloc`, `full` |
| `memory_prealloc` | `False` | allocate all guest RAM at start (KVM) |

The lock file lives in `$XDG_RUNTIME_DIR/azarovo-hyper/` (override with
`AZAROVO_LOCK`). It coordinates programs on the same client machine; guests
started by other tools are still seen through the hypervisor's own numbers.
