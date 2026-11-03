# Lifecycle

Every changing method returns the machine, so calls chain:
`hyper().kvm().define().start().memory.set("1G")`.

| Method | What it does |
|---|---|
| `define()` | Create the disk (if missing) and define the domain; adopt an existing domain with the same name |
| `start(wait=True, timeout=60)` | `define()` if needed, then power on; resumes a paused guest |
| `shutdown(timeout=120, force=True)` | ACPI power button; after `timeout` pull the plug (`force=False` raises `OperationTimeoutError` instead) |
| `stop()` | Immediate power-off, the disk is kept |
| `restart(timeout=120)` | `shutdown()` + `start()` |
| `reboot()` / `reset()` | Guest-initiated reboot / hardware reset (running guests only) |
| `suspend()` / `resume()` | Pause and continue the vCPUs |
| `delete(remove_disk=None)` | Power off, undefine (with snapshots, NVRAM, managed save), remove disks the library created, close the object |
| `close()` | Release everything the object holds; the guest keeps running |
| `wait_for(*states, timeout=60)` | Block until the machine reaches one of the states |

## State

```python
from azarovo_hyper import VMState

vm.state  # VMState.RUNNING, SHUTOFF, PAUSED, ..., UNDEFINED
vm.is_running  # True / False
vm.exists  # defined on the hypervisor?
vm.uuid, vm.xml  # libvirt UUID and the live domain XML
vm.autostart = True  # start together with libvirtd
```

`VMState` values match libvirt's `virDomainState` numbers.

## Disk ownership

The library remembers (in the domain metadata) whether it created the disk.
`delete()` removes the disk only in that case. Pass `remove_disk=True` or
`False` to decide explicitly. Disks attached with
`vm.storage.attach()` without a path are owned too and removed by `delete()`.

## Adopting existing machines

```python
vm = hyper().get("legacy-vm", hypervisor="kvm", uri="qemu:///system")
```

`get()` reads the domain XML and keeps its memory size, hot-plug ceiling and
vCPU limits, so the controllers clamp values correctly. Defining a machine
whose name already exists (`hyper().kvm("legacy-vm").start()`) also adopts it
instead of redefining it.

## Errors

All exceptions derive from `HyperError`:

| Exception | When |
|---|---|
| `ConfigurationError` (also `ValueError`) | invalid option, size, preset or argument |
| `VMStateError` | operation not allowed in the current state |
| `DomainNotFoundError` | machine or snapshot does not exist |
| `UnsupportedOperationError` | the driver cannot do it (e.g. snapshots on Xen) |
| `OperationTimeoutError` (also `TimeoutError`) | the guest did not reach a state in time |
| `ConnectionFailedError` | the hypervisor is unreachable |
| `VMClosedError` | the object was closed or deleted |
| `DiskError` | `qemu-img` failed |
| `BackendUnavailableError` | `libvirt-python` is not installed |
| `BackendError` | any other libvirt error |
