from pathlib import Path

import pytest

from azarovo_hyper import ConfigurationError, VMSpec


def test_defaults_are_valid():
    spec = VMSpec()
    assert spec.name.startswith("azarovo-")
    assert spec.memory_mib == 2048
    assert spec.current_memory_mib == 2048
    assert spec.max_memory_mib == 8192
    assert spec.effective_max_vcpus == 8
    assert spec.memory_hotplug
    assert spec.iso_path is None


def test_generated_names_are_unique():
    assert len({VMSpec().name for _ in range(50)}) == 50


def test_paths(tmp_path):
    spec = VMSpec(name="a", iso="~/x.iso")
    assert spec.iso_path == Path("~/x.iso").expanduser()
    assert spec.disk_path(tmp_path) == tmp_path / "a.qcow2"
    assert VMSpec(name="a", images_dir=tmp_path / "i").disk_path(Path("/nope")) == (
        tmp_path / "i" / "a.qcow2"
    )
    assert VMSpec(name="a", disk=tmp_path / "d.img").disk_path(Path("/x")) == tmp_path / "d.img"


def test_with_revalidates():
    spec = VMSpec(name="a")
    assert spec.with_(vcpus=4).vcpus == 4
    with pytest.raises(ConfigurationError):
        spec.with_(vcpus=0)


def test_hotplug_off_when_no_headroom():
    assert not VMSpec(memory="2G", max_memory="2G").memory_hotplug
    assert not VMSpec(memory_slots=0).memory_hotplug


@pytest.mark.parametrize(
    "options",
    [
        {"name": "bad name"},
        {"name": ""},
        {"name": "x" * 65},
        {"title": "two\nlines"},
        {"memory": 0},
        {"memory": "1G", "current_memory": "2G"},
        {"memory": "1G", "min_memory": "2G"},
        {"memory": "4G", "max_memory": "2G"},
        {"memory_slots": -1},
        {"dimm_size": 1},
        {"balloon_period": -1},
        {"disk_size": 0},
        {"vcpus": 0},
        {"vcpus": 4, "max_vcpus": 2},
        {"firmware": "coreboot"},
        {"graphics": "rdp"},
        {"video_heads": 0},
        {"pcie_ports": -1},
        {"extra_devices": "<x/>"},
    ],
)
def test_invalid_specs(options):
    with pytest.raises(ConfigurationError):
        VMSpec(**options)
