# Architecture and extending

The code follows clean architecture: dependencies point inwards and only the
adapters know about libvirt.

```
azarovo_hyper/
├── domain/     pure model: VMSpec, VMState, sizes, MemoryStats, XML queries
├── ports/      Protocols: Connection, Domain, DiskTool
├── adapters/   libvirt implementation, connection pool, qemu-img
├── config/     embedded XML templates, presets, safe renderer
├── drivers/    KvmDriver, XenDriver and the driver registry
├── vm/         VirtualMachine, its session and controllers
├── decorators.py
└── hyper.py    the hyper() entry point
```

* `domain` imports nothing from the other layers.
* `vm` works only with the `ports` protocols. The test-suite plugs an
  in-memory hypervisor into the same protocols.
* `drivers` turn a `VMSpec` into XML and pick strategies (for example
  DIMM hot-plug on KVM, raising the memory ceiling on Xen).

## Decorators

| Decorator | Purpose |
|---|---|
| `@guarded` | per-machine lock + "object is not closed" check |
| `@synchronized`, `@alive` | the two halves of `@guarded` |
| `@chainable` | return `self` for fluent calls |
| `@requires_state(*states)`, `@requires_running` | state preconditions |
| `@requires_capability("snapshots")` | refuse what the driver cannot do |
| `@retry(times, delay, on)` | retry flaky calls |
| `@decorate_public_methods(deco)` | class decorator, used to translate libvirt errors |
| `@register_driver("name")` | add a hypervisor driver |

## Adding a hypervisor

```python
from azarovo_hyper import hyper, register_driver
from azarovo_hyper.drivers import Capabilities, Hardware, KvmDriver


@register_driver("qemu")  # plain TCG emulation, no KVM
class QemuDriver(KvmDriver):
    domain_type = "qemu"
    capabilities = Capabilities(snapshots=True, screenshot=True, dimm_hotplug=True)

    def builtin_uri(self) -> str:
        return "qemu:///session"


vm = hyper().qemu(memory="512M", cpu_mode="maximum").start()  # appears on hyper()
```

A driver from scratch subclasses `HypervisorDriver` and implements
`builtin_uri`, `auto_network`, `driver_values`, `cdrom_slot`, `plug_memory`
and `unplug_memory`, and sets `template`, `capabilities` and `hardware`.

## Using it inside a control system

`hyper().get(name)` attaches to running guests, `metrics()` gives one
consistent sample per tick, and the memory/CPU controllers apply decisions.
Because each machine has its own lock and the pool shares connections, one
monitoring thread per guest scales without the guests blocking each other.

## Development

```bash
uv sync --locked                 # exact versions from uv.lock; needs libvirt headers
uv run ruff check . && uv run ruff format --check .
uv run pytest                    # unit + libvirt test:/// driver tests
AZAROVO_LIVE=1 uv run pytest     # plus real KVM guests (qemu:///session)
uv run pytest --cov
```
