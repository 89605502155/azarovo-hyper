"""Command line: ``azarovo-hyper setup`` and ``azarovo-hyper doctor``."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from azarovo_hyper.cli.doctor import doctor
from azarovo_hyper.cli.setup import setup
from azarovo_hyper.version import __version__


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="azarovo-hyper", description="Prepare this machine for azarovo-hyper."
    )
    root.add_argument("--version", action="version", version=f"azarovo-hyper {__version__}")
    commands = root.add_subparsers(dest="command", required=True)
    install = commands.add_parser("setup", help="install QEMU/KVM and libvirt (Ubuntu, sudo)")
    install.add_argument("-y", "--yes", action="store_true", help="do not ask for confirmation")
    install.add_argument("--dry-run", action="store_true", help="only print the commands")
    install.add_argument("--no-viewer", action="store_true", help="skip virt-viewer")
    commands.add_parser("doctor", help="check that guests can run on this machine")
    return root


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "setup":
        return setup(dry_run=args.dry_run, assume_yes=args.yes, viewer=not args.no_viewer)
    return doctor()
