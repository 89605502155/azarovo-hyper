import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from schema import assert_valid_domain

from azarovo_hyper import VMSpec, get_driver
from azarovo_hyper.config import preset, preset_names

DISK = Path("/var/lib/images/vm.qcow2")


def render(**options):
    spec = VMSpec(name="vm", **options)
    return get_driver("kvm").render_domain(
        spec, disk_path=DISK, owns_disk=True, uri="qemu:///session"
    )


def test_defaults_enable_balloon_hotplug_and_display(tmp_path):
    xml = render(iso="/isos/u.iso")
    assert_valid_domain(xml, tmp_path)
    root = ET.fromstring(xml)
    assert root.get("type") == "kvm"
    assert root.find("maxMemory").get("slots") == "16"
    assert root.find("vcpu").get("current") == "2"
    assert root.find("./cpu/numa/cell").get("cpus") == "0-7"
    assert root.find("./devices/memballoon/stats").get("period") == "1"
    assert root.find("./devices/graphics").get("type") == "spice"
    assert root.find("./devices/graphics/image").get("compression") == "off"
    assert root.find("./devices/video/model").get("type") == "virtio"
    assert root.find("./devices/input[@type='tablet']") is not None
    names = {t.get("name") for t in root.findall("./devices/channel/target")}
    assert names == {"com.redhat.spice.0", "org.qemu.guest_agent.0"}
    assert root.find("./devices/interface").get("type") == "user"
    cdrom = root.find("./devices/disk[@device='cdrom']")
    assert cdrom.find("source").get("file") == "/isos/u.iso"
    assert cdrom.find("boot").get("order") == "1"
    assert root.find("./devices/controller[@model='pcie-root']") is not None
    assert root.find("./metadata")[0].get("owns-disk") == "yes"


def test_options_change_the_xml(tmp_path):
    xml = render(
        memory_slots=0,
        graphics="vnc",
        guest_agent=False,
        firmware="efi",
        balloon_autodeflate=True,
        free_page_reporting=True,
        vcpus=1,
        max_vcpus=1,
        title="My <VM> & co",
        extra_devices=("<watchdog model='i6300esb'/>",),
    )
    assert_valid_domain(xml, tmp_path)
    root = ET.fromstring(xml)
    assert root.find("maxMemory") is None
    assert root.find("./os").get("firmware") == "efi"
    assert root.find("./devices/graphics").get("type") == "vnc"
    assert root.find("./devices/channel") is None
    assert root.find("./devices/memballoon").get("autodeflate") == "on"
    assert root.find("./devices/memballoon").get("freePageReporting") == "on"
    assert root.find("./cpu/numa/cell").get("cpus") == "0"
    assert root.findtext("title") == "My <VM> & co"
    assert root.find("./devices/watchdog") is not None
    assert root.find("./devices/disk[@device='cdrom']/source") is None


def test_no_graphics_and_system_network(tmp_path):
    spec = VMSpec(name="vm", graphics="none")
    xml = get_driver("kvm").render_domain(
        spec, disk_path=DISK, owns_disk=False, uri="qemu:///system"
    )
    assert_valid_domain(xml, tmp_path)
    root = ET.fromstring(xml)
    assert root.find("./devices/graphics") is None
    assert root.find("./devices/interface/source").get("network") == "default"


def test_sata_disk_moves_cdrom(tmp_path):
    root = ET.fromstring(render(disk_bus="sata"))
    targets = [t.get("dev") for t in root.findall("./devices/disk/target")]
    assert targets == ["sda", "sdb"]


@pytest.mark.parametrize("name", preset_names())
def test_every_preset_is_valid(name, tmp_path):
    xml = render(**preset(name))
    assert_valid_domain(xml, tmp_path)


def test_legacy_pc_uses_ide(tmp_path):
    root = ET.fromstring(render(**preset("reactos")))
    assert root.find("./os/type").get("machine") == "pc"
    assert root.find("./os/type").get("arch") == "i686"
    assert root.find("./devices/disk[@device='cdrom']/target").get("bus") == "ide"
    assert root.find("./devices/controller[@model='pcie-root']") is None


def test_xml_special_characters_in_paths_are_escaped(tmp_path):
    spec = VMSpec(name="vm", iso="/isos/a&b's.iso")
    xml = get_driver("kvm").render_domain(
        spec, disk_path=Path("/d/<x>.qcow2"), owns_disk=True, uri="qemu:///session"
    )
    root = ET.fromstring(xml)
    assert root.find("./devices/disk[@device='cdrom']/source").get("file") == "/isos/a&b's.iso"
    assert root.find("./devices/disk/source").get("file") == "/d/<x>.qcow2"


def test_custom_template(tmp_path):
    template = tmp_path / "mine.xml"
    template.write_text("<domain type='kvm'><name>${name}</name></domain>")
    assert render(template=template) == "<domain type='kvm'><name>vm</name></domain>"


def test_memory_preallocation(tmp_path):
    xml = render(memory_prealloc=True)
    assert_valid_domain(xml, tmp_path)
    assert ET.fromstring(xml).find("./memoryBacking/allocation").get("mode") == "immediate"
    assert ET.fromstring(render()).find("memoryBacking") is None
