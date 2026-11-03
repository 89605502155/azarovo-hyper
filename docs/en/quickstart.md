# Quick start

## Prepare the machine (once)

```bash
uv add azarovo-hyper
uv run azarovo-hyper setup     # Ubuntu; asks for the sudo password
```

## Boot a machine

```python
from azarovo_hyper import hyper

kvm1 = (
    hyper()
    .kvm(
        "ubuntu-lab",
        iso="~/Downloads/ubuntu-26.04-desktop-amd64.iso",
        preset="ubuntu",  # 4 GiB, 25 GiB disk, sane balloon limits
    )
    .start()
)

print(kvm1)  # <VirtualMachine 'ubuntu-lab' kvm qemu:///session running>
print(kvm1.display.uri)  # spice://127.0.0.1:5900
kvm1.display.open_viewer()  # window with the installer
```

`hyper().kvm(...)` only builds the object. `start()` creates the qcow2 disk,
defines the domain from the built-in XML and powers it on. Every option has
a default, so `hyper().kvm().start()` is valid too.

## Work with it

```python
kvm1.memory.set("3G")  # balloon the guest down to 3 GiB
kvm1.memory.plug("1G")  # hot-plug a 1 GiB DIMM
kvm1.cpu.set(4)  # hot-plug vCPUs up to 4
print(kvm1.metrics())  # CPU %, balloon statistics, disk counters

kvm1.storage.eject()  # after installation: boot from the disk
kvm1.snapshots.create("installed")
```

## Stop and clean up

```python
kvm1.shutdown()  # ACPI, then power off after 120 s
kvm1.delete()  # undefine and remove the disk it created
```

## A disposable machine

```python
with hyper().kvm(memory="1G", ephemeral=True).start() as tmp:
    tmp.memory.set("768M")
# here the machine, its disk and its connection are gone
```

## Several hypervisors at once

```python
h = hyper()
kvm1 = h.kvm("k1").start()
xen1 = h.xen("x1", iso="~/debian.iso").start()  # needs a Xen host
print(h.list("kvm"), h.host("kvm").free_mib)
```

## Attach to a machine created earlier

```python
vm = hyper().get("ubuntu-lab")  # keeps the machine's own memory/CPU limits
vm.start()
```
