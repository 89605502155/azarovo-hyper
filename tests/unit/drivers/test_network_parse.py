import pytest

from azarovo_hyper import ConfigurationError
from azarovo_hyper.drivers.network import NetworkChoice, interface_xml, parse_network


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("auto", NetworkChoice("user")),
        ("user", NetworkChoice("user")),
        ("none", NetworkChoice("none")),
        ("default", NetworkChoice("network", "default")),
        ("network:lab", NetworkChoice("network", "lab")),
        ("bridge:br0", NetworkChoice("bridge", "br0")),
    ],
)
def test_parse(value, expected):
    assert parse_network(value, "user") == expected


@pytest.mark.parametrize("value", ["", "  ", "bridge:", "wifi:x"])
def test_parse_rejects(value):
    with pytest.raises(ConfigurationError):
        parse_network(value, "user")


def test_interface_xml():
    assert interface_xml(NetworkChoice("none"), "virtio") == ""
    xml = interface_xml(NetworkChoice("bridge", "br'0"), None)
    assert "type='bridge'" in xml
    assert "bridge='br&apos;0'" in xml
    assert "<model" not in xml
