import pytest

from azarovo_hyper import HostInfo, MemoryStats


def test_memory_prefers_guest_usable():
    stats = MemoryStats.from_libvirt({"actual": 2048 * 1024, "usable": 512 * 1024, "rss": 1})
    assert stats.guest_reports
    assert stats.free_mib == 512
    assert stats.used_mib == 1536
    assert stats.usage_percent == pytest.approx(75)
    assert stats.raw["actual"] == 2048 * 1024


def test_memory_falls_back_to_unused_then_rss():
    assert MemoryStats.from_libvirt({"actual": 1024, "unused": 256}).free_mib == 0.25
    stats = MemoryStats.from_libvirt({"actual": 2048 * 1024, "rss": 512 * 1024})
    assert not stats.guest_reports
    assert stats.free_mib == 1536


def test_memory_clamps_and_handles_missing():
    assert MemoryStats.from_libvirt({"actual": 1024, "usable": 4096}).free_mib == 1
    assert MemoryStats.from_libvirt({"actual": 1024, "rss": 4096}).free_mib == 0
    empty = MemoryStats.from_libvirt({})
    assert empty.free_mib == 0
    assert empty.usage_percent == 0


def test_host_info():
    host = HostInfo("u", "h", "QEMU", 4, total_mib=1000, free_mib=100, cached_mib=200)
    assert host.available_mib == 300
    assert host.used_mib == 700
    assert host.usage_percent == 70
    assert HostInfo("u", "h", "Q", 1, 0, 0).usage_percent == 0
