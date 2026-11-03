# Memory and CPU

Sizes are accepted as MiB integers (`2048`) or strings (`"2G"`, `"512M"`,
`"1.5GiB"`). Results are returned in MiB.

## Three memory numbers

| Option | Meaning | Default |
|---|---|---|
| `memory` | boot memory, also the starting balloon ceiling | `"2G"` |
| `current_memory` | balloon size at boot | = `memory` |
| `min_memory` | lowest value `memory.set()` will ever request | `"256M"` |
| `max_memory` | hot-plug ceiling (`<maxMemory>` on KVM) | `"8G"` |
| `memory_slots` | DIMM slots for hot-plug (KVM) | `16` |
| `dimm_size` | default size of one `memory.plug()` | `"128M"` |
| `balloon_period` | seconds between guest balloon statistics | `1` |

## Ballooning

```python
vm.memory.set("1536M")  # clamped to [min_memory, maximum_mib]
vm.memory.grow("256M")  # current + 256 MiB
vm.memory.shrink("256M")
vm.memory.set("2G", persist=True)  # also write it to the configuration

vm.memory.current_mib  # balloon size right now
vm.memory.maximum_mib  # boot memory + hot-plugged memory
vm.memory.set_stats_period(5)  # refresh guest statistics every 5 s
```

`stats()` returns `MemoryStats`:

```python
s = vm.memory.stats()
s.actual_mib  # balloon size
s.usable_mib  # MemAvailable inside the guest (needs the virtio-balloon driver)
s.unused_mib  # MemFree inside the guest
s.rss_mib  # memory the guest occupies on the host
s.free_mib  # usable -> unused -> actual - rss, whichever is known
s.used_mib, s.usage_percent
s.guest_reports  # False until the guest driver sends statistics
s.raw  # every field libvirt returned
```

`balloon_autodeflate=True` lets the guest deflate the balloon on OOM;
`free_page_reporting=True` returns freed guest pages to the host. Both are
off by default, so measurements stay reproducible.

## Memory hot-plug

```python
vm.memory.plug()  # one dimm_size module
vm.memory.plug("1G")  # returns the new maximum, MiB
vm.memory.dimms()  # [128, 1024]
vm.memory.unplug()  # removes the last module (guest must release it)
vm.memory.unplug("1G")
```

* **KVM** hot-plugs `pc-dimm` modules on NUMA node 0. The domain is defined with
  `<maxMemory slots=...>` and a NUMA cell, which QEMU requires for hot-plug.
* **Xen** has no DIMM devices: `plug()` raises the live memory ceiling and the
  xen balloon grows the guest inside it.

Plugging beyond `max_memory` raises `ConfigurationError`; when all slots are
used, `VMStateError`. Set `max_memory` equal to `memory` (or
`memory_slots=0`) to define a machine without hot-plug.

## vCPUs

```python
vm.cpu.count  # vCPUs right now
vm.cpu.maximum  # max_vcpus (default: max(vcpus, 8))
vm.cpu.set(4)  # live hot-plug; on a stopped guest: configuration
vm.cpu.plug(), vm.cpu.unplug()
vm.cpu.time_ns()  # CPU time since start
vm.cpu.usage()  # load since the previous call, 0..100 %
```

`usage()` is computed from the increase of libvirt's cumulative `cpu_time`
between two calls, divided by elapsed time and the vCPU count. The first call
after a start, reset or snapshot revert returns `0.0`. Each machine has its own
sampler, so monitoring threads never mix up machines.

## One metrics sample

```python
m = vm.metrics()  # GuestMetrics
m.state, m.cpu_percent, m.vcpus
m.memory  # MemoryStats or None when the guest is off
m.disks["vda"].read_bytes
```

The sample is taken under the machine lock, so its values are consistent with
each other. An adaptive controller typically calls `metrics()` on a timer and
reacts with `memory.set()` / `memory.plug()` / `cpu.set()`.
