"""``azarovo-hyper setup``: install and enable the hypervisor (Ubuntu)."""

from __future__ import annotations

from azarovo_hyper.cli.doctor import doctor
from azarovo_hyper.cli.system import System

PACKAGES = (
    "qemu-system-x86",
    "qemu-utils",
    "libvirt-daemon-system",
    "libvirt-clients",
    "ovmf",
)
VIEWER = "virt-viewer"


def plan(system: System, *, viewer: bool = True) -> list[list[str]]:
    """The commands ``setup`` runs, in order."""
    sudo = [] if system.is_root() else ["sudo"]
    packages = [*PACKAGES, VIEWER] if viewer else list(PACKAGES)
    apt = [*sudo, "env", "DEBIAN_FRONTEND=noninteractive", "apt-get"]
    return [
        [*apt, "update"],
        [*apt, "install", "-y", *packages],
        [*sudo, "systemctl", "enable", "--now", "libvirtd"],
        [*sudo, "usermod", "-aG", "libvirt,kvm", system.user()],
    ]


def setup(
    system: System | None = None,
    *,
    dry_run: bool = False,
    assume_yes: bool = False,
    viewer: bool = True,
) -> int:
    system = system or System()
    release = system.os_release()
    if release.get("ID") != "ubuntu":
        name = release.get("PRETTY_NAME", "this system")
        print(f"azarovo-hyper setup supports Ubuntu only for now, not {name}.")
        print("Install QEMU/KVM, qemu-img and libvirt with your package manager.")
        return 2
    commands = plan(system, viewer=viewer)
    print("azarovo-hyper will run:")
    for command in commands:
        print("   ", " ".join(command))
    if dry_run:
        return 0
    if not assume_yes and input("Continue? [Y/n] ").strip().lower() not in ("", "y", "yes"):
        print("aborted")
        return 1
    for command in commands:
        if code := system.run(command):
            print(f"command failed with exit code {code}")
            return code
    print("\nDone. Log out and in again (or run `newgrp libvirt`) so the new groups apply.\n")
    return doctor(system)
