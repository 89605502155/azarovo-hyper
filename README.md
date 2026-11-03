# azarovo-hyper

[![CI](https://github.com/89605502155/azarovo-hyper/actions/workflows/ci.yml/badge.svg)](https://github.com/89605502155/azarovo-hyper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/89605502155/azarovo-hyper/blob/main/LICENSE)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue)

High-level Python API to create, configure and control **KVM** and **Xen**
virtual machines through libvirt: one line boots a guest, and its attributes
cover everything an adaptive hypervisor controller needs — memory
ballooning, memory and vCPU hot-plug, disk hot-plug, metrics, snapshots,
screenshots.

[Документация на русском](https://github.com/89605502155/azarovo-hyper/blob/main/README.ru.md)

```python
from azarovo_hyper import hyper

kvm1 = hyper().kvm(iso="~/Downloads/ubuntu.iso", preset="ubuntu").start()

kvm1.memory.set("3G")  # balloon
kvm1.memory.plug("1G")  # DIMM hot-plug
kvm1.cpu.set(4)  # vCPU hot-plug
print(kvm1.metrics())  # CPU %, balloon statistics, disk I/O
kvm1.delete()  # domain, disk and connection are gone
```

## Features

* **Defaults for everything** — `hyper().kvm().start()` is a working machine.
* **Two-command setup** — `uv add azarovo-hyper` (pure Python, ctypes over the
  system libvirt) and `azarovo-hyper setup` for the hypervisor itself.
* **Host capacity without races** — RAM, CPU and disk are checked and reserved
  atomically across threads and processes; `InsufficientResourcesError`
  leaves nothing behind; disks are preallocated by the kernel.
* **Built-in, schema-validated XML** for KVM (q35, NUMA cell, `maxMemory`
  slots, spare PCIe ports, virtio balloon with stats, guest agent, SPICE +
  virtio GPU + USB tablet + vdagent) and Xen HVM (libxl, VNC, xen balloon).
* **Memory**: balloon `set/grow/shrink` clamped to your limits, DIMM hot-plug
  on KVM, live memory ceiling on Xen, guest balloon statistics.
* **CPU**: live vCPU hot-plug, per-machine CPU-load sampling.
* **Storage**: live ISO insert/eject, disk hot-plug, I/O counters.
* **Snapshots, screenshots, viewer windows, IP addresses, NIC counters.**
* **Threads, processes and asyncio**: works from `ThreadPoolExecutor`,
  `ProcessPoolExecutor` (machines pickle, forking is safe) and `asyncio.to_thread`.
* **Thread-safe by design**: a lock per machine, one shared connection per URI;
  many hypervisors and machines work in parallel without blocking each other.
* **Deterministic cleanup**: `stop()` releases the connection, `del vm` /
  `close()` / `with` release everything, `ephemeral=True` also deletes the guest.
* Presets for Ubuntu, Fedora, Debian, Alpine, Windows, ReactOS and Redox.
* Clean architecture with pluggable drivers: `@register_driver("name")`.

## Installation

```bash
uv add azarovo-hyper              # no dependencies, nothing to compile
uv run azarovo-hyper setup        # once per machine: QEMU/KVM + libvirt, asks for sudo
uv run azarovo-hyper doctor       # optional: "ready to run guests"
```

> Tested on and built for **Linux, specifically Ubuntu** (22.04, 24.04, 26.04).
> Support for other distributions and operating systems is planned.

Normal users get `qemu:///session` (no root needed); root gets `qemu:///system`.
See [installation](https://github.com/89605502155/azarovo-hyper/blob/main/docs/en/installation.md).

## Usage

```python
from azarovo_hyper import VMState, hyper

h = hyper()
vm = h.kvm(
    "lab1",
    iso="~/isos/debian.iso",
    memory="4G",  # boot memory
    min_memory="1G",  # memory.set() never goes below
    max_memory="16G",  # hot-plug ceiling
    vcpus=2,
    max_vcpus=8,
    network="auto",  # user-mode in session, libvirt 'default' in system
)
vm.start()  # creates the qcow2, defines the domain, boots it

vm.state is VMState.RUNNING  # True
vm.display.uri  # 'spice://127.0.0.1:5900'
vm.display.open_viewer()  # virt-viewer window, closed together with the VM

stats = vm.memory.stats()  # MemoryStats(actual_mib=..., usable_mib=..., rss_mib=...)
vm.memory.set(stats.actual_mib - 512)
vm.cpu.usage()  # load since the previous call, %

vm.storage.eject()  # after the OS is installed
data = vm.storage.attach(size="50G")
vm.snapshots.create("installed")
vm.display.screenshot("screen.png")

vm.shutdown()  # ACPI, then power off after the timeout
vm.delete()
```

Xen works the same way: `hyper().xen("x1", iso=...).start()` on a Xen host.

Throw-away machines:

```python
with hyper().kvm(memory="1G", ephemeral=True).start() as tmp:
    ...
# powered off, undefined, disk removed, connection closed
```

Many machines in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

machines = [h.kvm(f"node{i}") for i in range(8)]
with ThreadPoolExecutor(8) as pool:
    list(pool.map(lambda m: m.start(), machines))
```

## Documentation

| | English | Русский |
|---|---|---|
| Overview | [docs/en](https://github.com/89605502155/azarovo-hyper/blob/main/docs/en/index.md) | [docs/ru](https://github.com/89605502155/azarovo-hyper/blob/main/docs/ru/index.md) |
| Quick start | [quickstart](https://github.com/89605502155/azarovo-hyper/blob/main/docs/en/quickstart.md) | [быстрый старт](https://github.com/89605502155/azarovo-hyper/blob/main/docs/ru/quickstart.md) |
| Memory and CPU | [memory-cpu](https://github.com/89605502155/azarovo-hyper/blob/main/docs/en/memory-cpu.md) | [память и CPU](https://github.com/89605502155/azarovo-hyper/blob/main/docs/ru/memory-cpu.md) |
| All options | [configuration](https://github.com/89605502155/azarovo-hyper/blob/main/docs/en/configuration.md) | [конфигурация](https://github.com/89605502155/azarovo-hyper/blob/main/docs/ru/configuration.md) |
| Host capacity | [capacity](https://github.com/89605502155/azarovo-hyper/blob/main/docs/en/capacity.md) | [ресурсы хоста](https://github.com/89605502155/azarovo-hyper/blob/main/docs/ru/capacity.md) |
| Threads and cleanup | [resources](https://github.com/89605502155/azarovo-hyper/blob/main/docs/en/resources.md) | [ресурсы](https://github.com/89605502155/azarovo-hyper/blob/main/docs/ru/resources.md) |

## Development

```bash
uv sync --locked                 # exact versions from uv.lock
uv run ruff check . && uv run ruff format --check .
uv run pytest                    # unit tests + libvirt test:/// driver
AZAROVO_LIVE=1 uv run pytest     # also boots real KVM guests
```

## License

[MIT](https://github.com/89605502155/azarovo-hyper/blob/main/LICENSE) © 2026 Andrey Ferubko
