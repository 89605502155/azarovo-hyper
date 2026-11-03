# azarovo-hyper documentation

`azarovo-hyper` is a high-level Python library for creating, configuring and
controlling KVM and Xen virtual machines through libvirt. One line boots a
fully configured guest:

```python
from azarovo_hyper import hyper

kvm1 = hyper().kvm(iso="~/Downloads/ubuntu.iso", preset="ubuntu").start()
```

## Contents

| Page | What it covers |
|---|---|
| [Installation](installation.md) | System packages, `pip`/`uv`, permissions, URIs |
| [Quick start](quickstart.md) | The first machine, step by step |
| [Lifecycle](lifecycle.md) | define, start, shutdown, stop, pause, delete, adopt |
| [Memory and CPU](memory-cpu.md) | Ballooning, memory hot-plug, vCPU hot-plug, load |
| [Disks, display, network](devices.md) | ISO, disk hot-plug, snapshots, screenshots, viewer |
| [Configuration](configuration.md) | Every option, presets, built-in XML, custom templates |
| [Concurrency and resources](resources.md) | Threads, connection pool, cleanup guarantees |
| [Architecture and extending](architecture.md) | Layers, decorators, adding a hypervisor |

The Russian version lives in [`../ru`](../ru/index.md).

## Supported platforms

* Linux hosts with libvirt (KVM through `qemu:///session` or `qemu:///system`,
  Xen through `xen:///system`);
* Python 3.11, 3.12, 3.13 and 3.14.
