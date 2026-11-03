"""Validation of rendered XML against libvirt's own RelaxNG schema."""

import shutil
import subprocess
from pathlib import Path

import pytest

VALIDATOR = shutil.which("virt-xml-validate")


def assert_valid_domain(xml: str, tmp_path: Path) -> None:
    if VALIDATOR is None:
        pytest.skip("virt-xml-validate is not installed")
    path = tmp_path / "domain.xml"
    path.write_text(xml)
    result = subprocess.run([VALIDATOR, str(path), "domain"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
