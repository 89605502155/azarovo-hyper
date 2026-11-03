# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.0.2] - 2026-11-03

### Added

- `azarovo-hyper setup` installs and enables QEMU/KVM and libvirt on Ubuntu
  with one command; `azarovo-hyper doctor` checks the machine.
- Native libvirt backend over ctypes: the package has no dependencies and
  nothing to compile. The official binding stays available as
  `azarovo-hyper[libvirt]` with `AZAROVO_LIBVIRT_BACKEND=python`.
- Race-free host capacity checks for RAM, CPU and disk: measuring, checking
  and taking a resource happen under one host-wide lock shared by threads and
  processes; `InsufficientResourcesError` and `ResourcePolicy`.
- Validated number types (`PositiveInt`, `NonNegativeInt`, `NonNegativeFloat`)
  and the `@validated` decorator: negative RAM, vCPUs, sizes or timeouts are
  refused with `ConfigurationError`.
- `disk_preallocation` (default `falloc`) and `memory_prealloc` options.
- Machines can be pickled and passed to `ProcessPoolExecutor`.
- Tests for process pools (fork, forkserver, spawn) and asyncio; integration
  tests run on both libvirt backends.
- `uv.lock` is committed for reproducible development environments.

### Fixed

- Fork safety: a forked child no longer closes or reuses the parent's libvirt
  connection, no longer deadlocks on locks held during the fork, and no longer
  deletes the parent's ephemeral machines.
- `delete()` of an adopted machine reads disk ownership from the domain.
- A start refused by the hypervisor rolls back the definition it created.

### Changed

- Documented platform: Linux, tested on Ubuntu; other systems are planned.

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

[0.0.2]: https://github.com/89605502155/azarovo-hyper/releases/tag/v0.0.2
[0.0.1]: https://github.com/89605502155/azarovo-hyper/releases/tag/v0.0.1
