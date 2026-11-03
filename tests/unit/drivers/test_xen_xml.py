import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from schema import assert_valid_domain

from azarovo_hyper import ConfigurationError, VMSpec, get_driver


def render(**options):
    return get_driver("xen").render_domain(
        VMSpec(name="xvm", **options),
        disk_path=Path("/x.qcow2"),
        owns_disk=True,
        uri="xen:///system",
    )


def test_xen_defaults(tmp_path):
    xml = render(iso="/a.iso")
    assert_valid_domain(xml, tmp_path)
    root = ET.fromstring(xml)
    assert root.get("type") == "xen"
    assert root.find("./os/type").get("machine") == "xenfv"
    assert [b.get("dev") for b in root.findall("./os/boot")] == ["cdrom", "hd"]
    assert root.find("./devices/disk/target").get("dev") == "xvda"
    assert root.find("./devices/disk[@device='cdrom']/target").get("dev") == "hdc"
    assert root.find("./devices/disk[@device='cdrom']/boot") is None
    assert root.find("./devices/memballoon").get("model") == "xen"
    assert root.find("./devices/graphics").get("type") == "vnc"
    assert root.find("./devices/video/model").get("type") == "vga"
    assert root.find("./devices/interface/source").get("bridge") == "xenbr0"
    assert root.find("maxMemory") is None
    assert root.find("vcpu").get("current") == "2"


def test_xen_without_graphics(tmp_path):
    xml = render(graphics="none", network="none")
    assert_valid_domain(xml, tmp_path)
    root = ET.fromstring(xml)
    assert root.find("./devices/graphics") is None
    assert root.find("./devices/interface") is None


def test_xen_rejects_spice():
    with pytest.raises(ConfigurationError):
        render(graphics="spice")


def test_xen_capabilities():
    caps = get_driver("xen").capabilities
    assert caps.live_max_memory and not caps.dimm_hotplug
    assert not caps.snapshots and not caps.screenshot
    assert get_driver("xen").default_uri() == "xen:///system"
