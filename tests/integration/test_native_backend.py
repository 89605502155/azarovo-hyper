"""The ctypes backend mirrors the official binding exactly."""

import pytest

from azarovo_hyper.adapters import native
from fakes import TEST_URI

libvirt = pytest.importorskip("libvirt")


def test_constants_match_the_official_binding():
    names = [n for n in dir(native) if n.startswith("VIR_")]
    assert len(names) >= 25
    for name in names:
        assert getattr(native, name) == getattr(libvirt, name), name
    assert native.getVersion() == libvirt.getVersion()


def test_same_answers_as_the_official_binding(keeper):
    ours, theirs = native.open(TEST_URI), libvirt.open(TEST_URI)
    try:
        assert ours.getInfo() == theirs.getInfo()
        assert ours.getHostname() == theirs.getHostname()
        a, b = ours.lookupByName("test"), theirs.lookupByName("test")
        assert (a.name(), a.UUIDString(), a.maxMemory()) == (
            b.name(),
            b.UUIDString(),
            b.maxMemory(),
        )
        assert a.XMLDesc(0) == b.XMLDesc(0)
        assert a.state() == b.state() and a.autostart() == b.autostart()
        assert a.interfaceAddresses(0) == b.interfaceAddresses(0)
        # the test driver derives traffic counters from the clock: compare the shape
        assert len(a.interfaceStats("testnet0")) == len(b.interfaceStats("testnet0")) == 8
        assert [d.name() for d in ours.listAllDomains(0)] == [
            d.name() for d in theirs.listAllDomains(0)
        ]
    finally:
        ours.close()
        theirs.close()


def test_errors_carry_libvirt_codes(keeper):
    connection = native.open(TEST_URI)
    with pytest.raises(native.libvirtError) as info:
        connection.lookupByName("no-such-domain")
    assert info.value.get_error_code() == native.VIR_ERR_NO_DOMAIN
    assert info.value.get_error_message() == str(info.value)
    connection.close()
    assert connection.close() == 0 and not connection.isAlive()
    with pytest.raises(native.libvirtError, match="closed"):
        connection.names() if hasattr(connection, "names") else connection.lookupByName("x")


def test_many_objects_are_freed_without_crashing(keeper):
    connection = native.open(TEST_URI)
    for _ in range(2000):
        domain = connection.lookupByName("test")
        domain.XMLDesc(0)
        domain.interfaceAddresses(0)
        connection.listAllDomains(0)
    connection.close()
