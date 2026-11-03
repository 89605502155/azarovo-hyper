# Disks, display, network and snapshots

## CD-ROM

Every machine has a CD-ROM drive (empty if `iso` is not set), so media can be
changed while the guest runs:

```python
vm.storage.iso  # Path of the inserted ISO or None
vm.storage.eject()  # e.g. after installing the OS
vm.storage.insert("~/virtio-win.iso")
```

The CD-ROM boots first; with an empty tray the firmware falls through to the
disk, so ejecting the installer is all that is needed after installation.

## Disks

```python
vm.storage.disks()  # {"vda": "/.../vm.qcow2"}
target = vm.storage.attach(size="20G")  # new qcow2 next to the main disk
vm.storage.attach("/data/scratch.img")  # existing image (raw for .img/.raw)
vm.storage.attach(size="5G", bus="sata", persist=False)
vm.storage.detach(target)  # images created by attach() are deleted
vm.storage.detach("vdc", remove_file=True)
vm.storage.stats()["vda"].written_bytes
```

KVM machines use the q35 chipset with `pcie_ports` (default 4) empty PCIe root
ports reserved right after definition, so live disk hot-plug always has a free
slot. The boot disk cannot be detached.

## Snapshots (KVM)

```python
vm.snapshots.create("clean", description="fresh install")
vm.snapshots.create()  # name: snap-YYYYmmdd-HHMMSS
vm.snapshots.names()  # ["clean", ...]
"clean" in vm.snapshots, len(vm.snapshots)
vm.snapshots.revert("clean")
vm.snapshots.delete("clean")
```

Snapshots of a running qcow2 guest include its memory. Xen (libxl) has no
snapshots, the call raises `UnsupportedOperationError`.

## Display

```python
vm.display.uri  # "spice://127.0.0.1:5900" (or vnc://)
vm.display.graphics()  # every <graphics> element: type, listen, port
vm.display.screenshot("shot")  # bytes; saved as shot.png / shot.ppm
viewer = vm.display.open_viewer()  # virt-viewer window (subprocess.Popen)
vm.display.close_viewers()
```

Viewer windows belong to the machine object: `stop()`, `shutdown()`,
`close()` and `delete()` terminate them.

The built-in KVM display is tuned for a sharp, responsive picture: SPICE with
lossless images, a virtio GPU (auto-resize with `spice-vdagent`), a USB tablet
for an absolute pointer, the vdagent channel for clipboard sharing and two USB
redirection channels. Xen guests get VNC with a VGA card and a USB tablet.
Use `graphics="vnc"` or `graphics="none"` and `listen="0.0.0.0"` to change it.

## Network

| `network=` | Meaning |
|---|---|
| `"auto"` (default) | KVM session: `user`; KVM system: `network:default`; Xen: `bridge:xenbr0` |
| `"user"` | QEMU user-mode networking, no privileges needed |
| `"default"` / `"network:NAME"` | libvirt virtual network |
| `"bridge:br0"` | host bridge |
| `"none"` | no network card |

```python
vm.network.interfaces()  # host-side devices: ["vnet0"]
vm.network.addresses()  # {"enp1s0": ["192.168.122.40"]} (agent / DHCP / ARP)
vm.network.stats()["vnet0"].rx_bytes
```

`nic_model` selects the card (`virtio` on KVM; `e1000`, `rtl8139`, ...).
