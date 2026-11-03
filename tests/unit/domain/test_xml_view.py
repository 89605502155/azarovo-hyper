from azarovo_hyper.domain.xml_view import NAMESPACE, DomainXml

XML = f"""<domain type='kvm'>
  <name>vm</name>
  <metadata><a:managed xmlns:a='{NAMESPACE}' owns-disk='yes'/></metadata>
  <memory unit='KiB'>3145728</memory>
  <currentMemory unit='KiB'>1048576</currentMemory>
  <maxMemory slots='16' unit='KiB'>8388608</maxMemory>
  <vcpu placement='static' current='2'>8</vcpu>
  <devices>
    <disk type='file' device='disk'><source file='/a.qcow2'/><target dev='vda' bus='virtio'/></disk>
    <disk type='file' device='disk'><target dev='vdb' bus='virtio'/></disk>
    <disk type='file' device='cdrom'><source file='/x.iso'/><target dev='sda' bus='sata'/></disk>
    <memory model='dimm'><target><size unit='KiB'>1048576</size><node>0</node></target></memory>
    <interface type='network'><target dev='vnet3'/></interface>
    <graphics type='spice' port='5901' autoport='yes' listen='127.0.0.1'/>
    <graphics type='vnc' port='-1'><listen type='address' address='0.0.0.0'/></graphics>
  </devices>
</domain>"""


def test_queries():
    view = DomainXml(XML)
    assert view.name == "vm"
    assert view.disks() == {"vda": "/a.qcow2", "vdb": ""}
    assert view.targets() == {"vda", "vdb", "sda"}
    cdrom = view.cdrom()
    assert cdrom is not None
    assert (cdrom.target, cdrom.bus, cdrom.source) == ("sda", "sata", "/x.iso")
    assert view.dimms() == [1024]
    assert view.interfaces() == ["vnet3"]
    assert view.owns_disk()
    spice, vnc = view.graphics()
    assert spice.uri == "spice://127.0.0.1:5901"
    assert vnc.uri is None
    assert vnc.listen == "0.0.0.0"


def test_spec_options_subtract_dimms():
    options = DomainXml(XML).spec_options()
    assert options["memory"] == 2048
    assert options["current_memory"] == 1024
    assert options["max_memory"] == 8192
    assert options["memory_slots"] == 16
    assert (options["vcpus"], options["max_vcpus"]) == (2, 8)


def test_minimal_domain():
    view = DomainXml("<domain><name>m</name><memory>1048576</memory><vcpu>1</vcpu></domain>")
    assert view.cdrom() is None
    assert not view.owns_disk()
    assert view.spec_options()["memory_slots"] == 0
