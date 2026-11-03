# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.0.1] - 2026-11-03

### Added

- `hyper()` entry point with `kvm()`, `xen()`, `machine()`, `get()`, `list()`
  and `host()`.
- `VirtualMachine` with lifecycle (define, start, shutdown, stop, restart,
  reboot, reset, suspend, resume, delete, close) and chaining.
- Memory controller: balloon `set/grow/shrink`, DIMM hot-plug (KVM), live
  memory ceiling (Xen), balloon statistics and stats period.
- CPU controller: vCPU hot-plug and per-machine load sampling.
- Storage: live ISO insert/eject, disk hot-plug, I/O counters.
- Snapshots, screenshots, viewer windows, IP addresses, NIC counters.
- Built-in KVM and Xen XML templates validated against the libvirt schema.
- Presets: linux, ubuntu, fedora, debian, alpine, windows, reactos, redox.
- Thread-safe reference-counted connection pool and per-machine locks.
- Deterministic resource cleanup and `ephemeral` machines.
- Driver registry with `@register_driver` for new hypervisors.
- Documentation in English and Russian.

[0.0.1]: https://github.com/89605502155/azarovo-hyper/releases/tag/v0.0.1
