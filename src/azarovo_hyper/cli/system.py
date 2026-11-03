"""Everything the CLI asks of the host, behind one object tests can replace."""

from __future__ import annotations

import getpass
import grp
import os
import shutil
import subprocess
from pathlib import Path


class System:
    """The real machine."""

    def os_release(self) -> dict[str, str]:
        try:
            text = Path("/etc/os-release").read_text()
        except OSError:
            return {}
        pairs = (line.split("=", 1) for line in text.splitlines() if "=" in line)
        return {key: value.strip().strip('"') for key, value in pairs}

    def cpu_flags(self) -> set[str]:
        try:
            text = Path("/proc/cpuinfo").read_text()
        except OSError:
            return set()
        return {flag for line in text.splitlines() if line.startswith("flags") for flag in
                line.split(":", 1)[1].split()}  # fmt: skip

    def which(self, program: str) -> str | None:
        return shutil.which(program)

    def accessible(self, path: str) -> bool:
        return os.access(path, os.R_OK | os.W_OK)

    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def is_root(self) -> bool:
        return os.geteuid() == 0

    def user(self) -> str:
        return os.environ.get("SUDO_USER") or getpass.getuser()

    def groups(self) -> set[str]:
        names = {grp.getgrgid(gid).gr_name for gid in os.getgroups()}
        user = self.user()
        names |= {g.gr_name for g in grp.getgrall() if user in g.gr_mem}
        return names

    def run(self, command: list[str]) -> int:
        print("+", " ".join(command), flush=True)
        return subprocess.run(command, check=False).returncode

    def connect(self, uri: str) -> str:
        """Open ``uri`` and return the hypervisor type (raises on failure)."""
        from azarovo_hyper.adapters.loader import load_libvirt

        connection = load_libvirt().open(uri)
        try:
            return str(connection.getType())
        finally:
            connection.close()
