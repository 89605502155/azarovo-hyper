import xml.etree.ElementTree as ET

import pytest

from azarovo_hyper.drivers.pcie import add_root_ports, free_root_ports

XML = """<domain><devices>
<controller type='pci' index='0' model='pcie-root'/>
<controller type='pci' index='1' model='pcie-root-port'/>
<controller type='pci' index='2' model='pcie-root-port'/>
<controller type='pci' index='3' model='pcie-root-port'/>
<disk><address type='pci' domain='0x0000' bus='0x01' slot='0x00' function='0x0'/></disk>
<interface><address type='pci' bus='0x03' slot='0x00'/></interface>
</devices></domain>"""


def test_free_ports():
    assert free_root_ports(XML) == [2]


def test_add_ports():
    extended = add_root_ports(XML, 3)
    ports = ET.fromstring(extended).findall("./devices/controller[@model='pcie-root-port']")
    assert len(ports) == 6


def test_add_ports_needs_devices():
    with pytest.raises(ValueError):
        add_root_ports("<domain/>", 1)
