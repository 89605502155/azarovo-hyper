"""Disk images through ``qemu-img`` (it works for both KVM and Xen qdisk)."""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from azarovo_hyper.errors import DiskError, InsufficientResourcesError

logger = logging.getLogger(__name__)


class QemuImg:
    """Creates and removes disk images. Existing images are never overwritten."""

    def __init__(self, binary: str = "qemu-img", timeout_s: float = 120.0) -> None:
        self.binary = binary
        self.timeout_s = timeout_s

    def create(
        self, path: Path, size_mib: int, fmt: str = "qcow2", preallocation: str = "off"
    ) -> bool:
        """Create the image; return ``False`` if it already existed.

        ``preallocation="falloc"`` makes the kernel reserve every block now, so a
        full disk fails here instead of inside the running guest.
        """
        if path.exists():
            logger.debug("disk %s already exists, keeping it", path)
            return False
        executable = shutil.which(self.binary)
        if executable is None:
            raise DiskError(f"{self.binary} not found; install qemu-utils (or qemu-img)")
        path.parent.mkdir(parents=True, exist_ok=True)
        command = [executable, "create", "-q", "-f", fmt]
        if preallocation != "off":
            command += ["-o", f"preallocation={preallocation}"]
        command += [str(path), f"{size_mib}M"]
        try:
            subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=self.timeout_s
            )
        except subprocess.CalledProcessError as exc:
            path.unlink(missing_ok=True)
            message = f"qemu-img failed for {path}: {exc.stderr.strip()}"
            if "No space left" in exc.stderr:
                raise InsufficientResourcesError(message) from exc
            raise DiskError(message) from exc
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
