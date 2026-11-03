"""Disk images through ``qemu-img`` (it works for both KVM and Xen qdisk)."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from azarovo_hyper.errors import DiskError

logger = logging.getLogger(__name__)


class QemuImg:
    """Creates and removes disk images. Existing images are never overwritten."""

    def __init__(self, binary: str = "qemu-img", timeout_s: float = 120.0) -> None:
        self.binary = binary
        self.timeout_s = timeout_s

    def create(self, path: Path, size_mib: int, fmt: str = "qcow2") -> bool:
        """Create the image; return ``False`` if it already existed."""
        if path.exists():
            logger.debug("disk %s already exists, keeping it", path)
            return False
        executable = shutil.which(self.binary)
        if executable is None:
            raise DiskError(f"{self.binary} not found; install qemu-utils (or qemu-img)")
        path.parent.mkdir(parents=True, exist_ok=True)
        command = [executable, "create", "-q", "-f", fmt, str(path), f"{size_mib}M"]
        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=self.timeout_s
            )
        except subprocess.CalledProcessError as exc:
            raise DiskError(f"qemu-img failed for {path}: {exc.stderr.strip()}") from exc
        except subprocess.TimeoutExpired as exc:
            raise DiskError(f"qemu-img timed out creating {path}") from exc
        logger.info("created %s disk %s (%d MiB)", fmt, path, size_mib)
        return True

    def remove(self, path: Path) -> bool:
        """Delete the image; return ``False`` if there was nothing to delete."""
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise DiskError(f"cannot remove {path}: {exc}") from exc
        logger.info("removed disk %s", path)
        return True
