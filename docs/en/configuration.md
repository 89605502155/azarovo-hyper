# Configuration

All options are keyword arguments of `hyper().kvm()` / `hyper().xen()` and
fields of the frozen dataclass `VMSpec`. Options left as `None` take the
driver default shown in the last columns.

| Option | Default | KVM default | Xen default |
|---|---|---|---|
| `name` | `azarovo-<random>` | | |
| `title` | `""` | | |
| `iso` | `None` | | |
| `disk` | `<images_dir>/<name>.<format>` | | |
| `disk_size` | `"20G"` | | |
| `disk_format` | `"qcow2"` | | |
| `disk_preallocation` | `"falloc"` (see [capacity](capacity.md)) | | |
| `disk_bus` | `None` | `virtio` | `xen` |
| `images_dir` | see [installation](installation.md) | | |
| `memory`, `current_memory`, `min_memory`, `max_memory` | `2G`, `=memory`, `256M`, `8G` | | |
| `memory_slots`, `dimm_size` | `16`, `128M` | | |
| `balloon_period`, `balloon_autodeflate`, `free_page_reporting` | `1`, `False`, `False` | | |
| `memory_prealloc` | `False` | | |
| `resources` and its flat options (`check_resources`, `memory_overcommit`, `cpu_overcommit`, `host_memory_reserve`, `host_disk_reserve`) | `ResourcePolicy()` | | |
| `vcpus`, `max_vcpus` | `2`, `max(vcpus, 8)` | | |
| `cpu_mode` | `"host-passthrough"` | | |
| `arch` | `"x86_64"` | | |
| `machine` | `None` | `q35` | `xenfv` |
| `firmware` | `"bios"` (`"efi"`) | | |
| `clock` | `"utc"` (`"localtime"` for Windows) | | |
| `network`, `nic_model` | `"auto"`, `None` | `virtio` | hypervisor default |
| `graphics` | `None` | `spice` | `vnc` |
| `listen` | `"127.0.0.1"` | | |
| `video`, `video_heads` | `None`, `1` | `virtio` | `vga` |
| `usb_model` | `None` | `qemu-xhci` | |
| `pcie_ports` | `4` | | |
| `guest_agent` | `True` | | |
| `autostart`, `ephemeral` | `False`, `False` | | |
| `template` | `None` (built-in) | `kvm.xml` | `xen.xml` |
| `extra_devices` | `()` | | |

```python
from azarovo_hyper import VMSpec, hyper

spec = VMSpec(name="bench", memory="4G", vcpus=4)
vm = hyper().kvm(spec=spec.with_(vcpus=6))
vm.spec  # the spec with driver defaults filled in
```

## Presets

`preset=` supplies defaults for a guest system; explicit options win.

| Preset | Highlights |
|---|---|
| `linux` | plain defaults |
| `ubuntu` | 4 GiB (2 GiB at boot), min 1.5 GiB, 25 GiB disk |
| `fedora` | 4 GiB (2148 MiB at boot), min 1850 MiB, 25 GiB disk |
| `debian` | 2 GiB, min 512 MiB, 20 GiB disk |
| `alpine` | 512 MiB, 1 vCPU, 4 GiB disk |
| `windows` | 4 GiB, 64 GiB SATA disk, e1000e, QXL, UEFI, local clock |
| `reactos` | i686, i440fx, IDE, VGA/VNC, rtl8139, OHCI tablet, local clock |
| `redox` | i440fx, IDE, VGA/VNC, e1000, xHCI |

```python
from azarovo_hyper import preset_names

preset_names()  # ['alpine', 'debian', 'fedora', 'linux', 'reactos', 'redox', 'ubuntu', 'windows']
```

## Built-in XML

The XML is embedded in the package (`azarovo_hyper/config/templates`):
`kvm.xml`, `xen.xml` and device fragments (`disk`, `cdrom`, `interface`,
`spice`, `vnc`, `agent`, `dimm`, `snapshot`). Every rendered variant is
checked against libvirt's RelaxNG schema in the test-suite. The KVM domain
contains what the adaptive controller needs:

* `<maxMemory slots>` + NUMA cell: DIMM hot-plug;
* `<vcpu current=...>` below the maximum: vCPU hot-plug;
* virtio balloon with `<stats period>`: live resizing and guest statistics;
* spare PCIe root ports: disk hot-plug;
* qemu-guest-agent channel: clean shutdown and IP addresses;
* SPICE/virtio display stack described in [devices](devices.md).

## Custom templates and devices

```python
vm = hyper().kvm(extra_devices=("<watchdog model='i6300esb' action='reset'/>",))
vm = hyper().kvm(template="~/my-domain.xml")  # same $placeholders as kvm.xml
```

Values are XML-escaped before substitution, so paths and titles may contain
quotes or `&`.

## Environment variables

| Variable | Effect |
|---|---|
| `AZAROVO_KVM_URI`, `AZAROVO_XEN_URI` | default URI of the driver |
| `XDG_DATA_HOME` | base of the default images directory |
