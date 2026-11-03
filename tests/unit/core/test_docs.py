"""The documentation must only show code that exists and parses."""

import ast
import re
from pathlib import Path

import pytest

import azarovo_hyper
from azarovo_hyper import GuestMetrics, Hyper, MemoryStats, VirtualMachine
from azarovo_hyper.vm import (
    CpuController,
    DisplayController,
    MemoryController,
    NetworkController,
    SnapshotController,
    StorageController,
)

ROOT = Path(__file__).resolve().parents[3]
DOCS = sorted([ROOT / "README.md", ROOT / "README.ru.md", *ROOT.glob("docs/*/*.md")])
CONTROLLERS = {
    "memory": MemoryController,
    "cpu": CpuController,
    "storage": StorageController,
    "snapshots": SnapshotController,
    "display": DisplayController,
    "network": NetworkController,
}
MACHINE = re.compile(r"(?<![/\w.])(?:vm|kvm1|xen1|tmp)\.(\w+)(?:\.(\w+))?")
FACTORY = re.compile(r"\b(?:h|hyper\(\))\.(\w+)\(")
IMPORT = re.compile(r"from azarovo_hyper import ([\w, ]+)")


def python_blocks(path: Path) -> list[str]:
    return re.findall(r"```python\n(.*?)```", path.read_text(), flags=re.S)


@pytest.mark.parametrize("path", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_code_blocks_parse(path):
    for block in python_blocks(path):
        ast.parse(block)


@pytest.mark.parametrize("path", DOCS, ids=lambda p: str(p.relative_to(ROOT)))
def test_documented_api_exists(path):
    text = "\n".join(python_blocks(path))
    for attr, sub in MACHINE.findall(text):
        assert attr in CONTROLLERS or hasattr(VirtualMachine, attr), f"{path.name}: vm.{attr}"
        if sub and attr in CONTROLLERS:
            assert hasattr(CONTROLLERS[attr], sub), f"{path.name}: vm.{attr}.{sub}"
    for name in FACTORY.findall(text):
        assert hasattr(Hyper, name) or name == "qemu", f"{path.name}: hyper().{name}"
    for names in IMPORT.findall(text):
        for name in (n.strip() for n in names.split(",")):
            assert hasattr(azarovo_hyper, name), f"{path.name}: import {name}"


def test_documented_stats_fields_exist():
    for field in ("actual_mib", "usable_mib", "unused_mib", "rss_mib", "free_mib", "raw"):
        assert hasattr(MemoryStats, field)
    for field in ("state", "cpu_percent", "vcpus", "memory", "disks"):
        assert field in GuestMetrics.__dataclass_fields__


def test_license_is_the_mit_text():
    text = (ROOT / "LICENSE").read_text()
    assert text.startswith("MIT License\n\nCopyright (c) 2026 Andrey Ferubko\n")
    assert "Permission is hereby granted, free of charge" in text
    assert 'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND' in text
