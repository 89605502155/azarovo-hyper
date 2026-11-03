# azarovo-hyper documentation

`azarovo-hyper` is a high-level Python library for creating, configuring and
controlling KVM and Xen virtual machines through libvirt. One line boots a
fully configured guest:

```python
from azarovo_hyper import hyper

kvm1 = hyper().kvm(iso="~/Downloads/ubuntu.iso", preset="ubuntu").start()
```

Getting there takes two commands: `uv add azarovo-hyper` and, once per
machine, `uv run azarovo-hyper setup`.

## Contents

| Page | What it covers |
|---|---|
| [Installation](installation.md) | System packages, `pip`/`uv`, permissions, URIs |
| [Quick start](quickstart.md) | The first machine, step by step |
| [Lifecycle](lifecycle.md) | define, start, shutdown, stop, pause, delete, adopt |
| [Memory and CPU](memory-cpu.md) | Ballooning, memory hot-plug, vCPU hot-plug, load |
| [Disks, display, network](devices.md) | ISO, disk hot-plug, snapshots, screenshots, viewer |
| [Configuration](configuration.md) | Every option, presets, built-in XML, custom templates |
| [Host capacity](capacity.md) | RAM/CPU/disk checks without races, `InsufficientResourcesError` |
| [Concurrency and resources](resources.md) | Threads, processes, asyncio, cleanup guarantees |
| [Architecture and extending](architecture.md) | Layers, decorators, adding a hypervisor |

The Russian version lives in [`../ru`](../ru/index.md).

## Supported platforms

* **Tested on and built for Linux, specifically Ubuntu** (22.04, 24.04, 26.04).
  Other distributions and operating systems are planned for future releases.
* KVM through `qemu:///session` or `qemu:///system`, Xen through `xen:///system`.
* Python 3.11, 3.12, 3.13 and 3.14.
