# Installation

> **Platform.** azarovo-hyper is tested on and built for **Linux, specifically
> Ubuntu** (22.04, 24.04, 26.04). Support for other distributions and
> operating systems is planned for future releases.

## Two commands

```bash
uv add azarovo-hyper              # or: pip install azarovo-hyper
uv run azarovo-hyper setup        # once per machine; asks for your sudo password
```

1. `uv add` installs the library. It has **no dependencies** and nothing is
   compiled: the built-in backend talks to the system `libvirt.so.0` directly
   through `ctypes`, so no `libvirt-dev`, `pkg-config`, `python3-dev` or C
   compiler is needed.
2. `azarovo-hyper setup` installs the hypervisor itself — `qemu-system-x86`,
   `qemu-utils`, `libvirt-daemon-system`, `libvirt-clients`, `ovmf` and
   `virt-viewer` — enables libvirtd and adds you to the `libvirt` and `kvm`
   groups. It prints every command first and asks before running them;
   `--dry-run` only prints, `--yes` skips the question, `--no-viewer` skips
   `virt-viewer`. Log out and in once afterwards so the groups apply.

System packages cannot be installed by `uv add` itself: Python packages are
not allowed to run `sudo` during installation, which is why this one step is
an explicit command.

## Check the machine

```bash
uv run azarovo-hyper doctor
```

```
[ok  ] operating system     Ubuntu 26.04.1 LTS
[ok  ] CPU virtualization   Intel VT-x
[ok  ] /dev/kvm             read/write
[ok  ] qemu:///session      connected (QEMU)
ready to run guests
```

Every failed line tells what to do. `python -m azarovo_hyper doctor` works too.

## libvirt backends

| `AZAROVO_LIBVIRT_BACKEND` | Backend | Install |
|---|---|---|
| `native` (default) | ctypes over `libvirt.so.0` | nothing extra |
| `python` | official `libvirt-python` | `uv add "azarovo-hyper[libvirt]"` (compiles; needs `libvirt-dev`) |

Both expose the same API and the test-suite runs on both.

## Which hypervisor URI is used

| Driver | Default URI | Override |
|---|---|---|
| `kvm` | `qemu:///session` for normal users, `qemu:///system` for root | `uri=` argument or `AZAROVO_KVM_URI` |
| `xen` | `xen:///system` | `uri=` argument or `AZAROVO_XEN_URI` |

`qemu:///session` needs no root: every guest runs as your user and uses
user-mode networking. `qemu:///system` gives access to libvirt networks and
bridges. Remote hosts: `uri="qemu+ssh://user@host/system"`.

## Where disks go

Unless `disk=` or `images_dir=` is given, images are created in
`~/.local/share/azarovo-hyper/images` (or `$XDG_DATA_HOME/azarovo-hyper/images`),
and in `/var/lib/libvirt/images` when running as root against a system URI.

## Reproducible development setup

```bash
git clone https://github.com/89605502155/azarovo-hyper && cd azarovo-hyper
uv sync --locked                 # exact versions from the committed uv.lock
```
