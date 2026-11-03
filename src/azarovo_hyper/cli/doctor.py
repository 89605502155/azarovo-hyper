"""``azarovo-hyper doctor``: is this machine ready to run guests?"""

from __future__ import annotations

from dataclasses import dataclass

from azarovo_hyper.cli.system import System

SETUP = "run: uv run azarovo-hyper setup"


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str
    fix: str = ""
    required: bool = True


def _os(system: System) -> Check:
    info = system.os_release()
    name = info.get("PRETTY_NAME", "unknown Linux")
    ok = info.get("ID") == "ubuntu"
    return Check("operating system", ok, name, "only Ubuntu is tested so far", required=False)


def _cpu(system: System) -> Check:
    flags = system.cpu_flags()
    kind = "Intel VT-x" if "vmx" in flags else "AMD-V" if "svm" in flags else ""
    return Check(
        "CPU virtualization", bool(kind), kind or "no vmx/svm flag",
        "enable VT-x/AMD-V in the BIOS (or nested virtualization in the VM)",
    )  # fmt: skip


def _kvm(system: System) -> Check:
    if not system.exists("/dev/kvm"):
        return Check("/dev/kvm", False, "missing", SETUP)
    ok = system.accessible("/dev/kvm")
    return Check("/dev/kvm", ok, "read/write" if ok else "no access", "log out and in again")


def _program(system: System, name: str, *, required: bool = True) -> Check:
    path = system.which(name)
    return Check(name, path is not None, path or "not found", SETUP, required=required)


def _libvirt(system: System, uri: str, *, required: bool) -> Check:
    try:
        kind = system.connect(uri)
    except Exception as exc:
        first = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
        return Check(uri, False, first, SETUP, required=required)
    return Check(uri, True, f"connected ({kind})", required=required)


def _groups(system: System) -> Check:
    missing = {"libvirt", "kvm"} - system.groups()
    detail = "member" if not missing else f"not in {', '.join(sorted(missing))}"
    return Check("user groups", not missing, detail, SETUP, required=False)


def checks(system: System) -> list[Check]:
    return [
        _os(system),
        _cpu(system),
        _kvm(system),
        _program(system, "qemu-system-x86_64"),
        _program(system, "qemu-img"),
        _libvirt(system, "qemu:///session", required=True),
        _libvirt(system, "qemu:///system", required=False),
        _groups(system),
        _program(system, "virt-viewer", required=False),
    ]


def doctor(system: System | None = None) -> int:
    """Print every check; exit code 1 if a required one fails."""
    results = checks(system or System())
    for c in results:
        mark = "ok  " if c.ok else ("FAIL" if c.required else "warn")
        hint = f"  -> {c.fix}" if not c.ok and c.fix else ""
        print(f"[{mark}] {c.name:<20} {c.detail}{hint}")
    failed = [c for c in results if c.required and not c.ok]
    print("ready to run guests" if not failed else f"{len(failed)} problem(s) to fix")
    return 1 if failed else 0
