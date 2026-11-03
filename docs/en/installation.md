# Installation

## 1. System packages

The library talks to libvirt, so the host needs the hypervisor and the
headers to build the `libvirt-python` binding.

Debian / Ubuntu:

```bash
sudo apt install -y qemu-kvm qemu-utils libvirt-daemon-system libvirt-clients \
                    pkg-config libvirt-dev python3-dev
sudo usermod -aG libvirt,kvm "$USER"    # log in again afterwards
```

Fedora:

```bash
sudo dnf install -y @virtualization qemu-img pkgconf-pkg-config libvirt-devel python3-devel
```

Xen hosts additionally need the Xen hypervisor and `libvirt-daemon-driver-libxl`.

## 2. The library

```bash
pip install "azarovo-hyper[libvirt]"
# or, with uv
uv add "azarovo-hyper[libvirt]"
```

The `libvirt` extra installs `libvirt-python`. Without it the package still
imports (useful for tests and code generation), and the first real
connection raises `BackendUnavailableError` with installation hints.

`virt-viewer` is optional: it is only needed for `vm.display.open_viewer()`.

## 3. Which hypervisor URI is used

| Driver | Default URI | Override |
|---|---|---|
| `kvm` | `qemu:///session` for normal users, `qemu:///system` for root | `uri=` argument or `AZAROVO_KVM_URI` |
| `xen` | `xen:///system` | `uri=` argument or `AZAROVO_XEN_URI` |

`qemu:///session` needs no root and no group membership: every guest runs as
your user and uses user-mode networking. `qemu:///system` gives access to
libvirt networks and bridges.

Remote hosts work the same way: `uri="qemu+ssh://user@host/system"`.

## 4. Where disks go

Unless `disk=` or `images_dir=` is given, images are created in

* `~/.local/share/azarovo-hyper/images` (or `$XDG_DATA_HOME/azarovo-hyper/images`);
* `/var/lib/libvirt/images` when running as root against a system URI.

## 5. Check the installation

```python
from azarovo_hyper import hyper, libvirt_available

print(libvirt_available())  # True
print(hyper().host())  # HostInfo(uri='qemu:///session', cpus=..., ...)
```
