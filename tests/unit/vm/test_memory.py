import pytest

from azarovo_hyper import ConfigurationError, UnsupportedOperationError, VMStateError


def test_balloon_set_is_clamped(running):
    assert running.memory.set("512M") == 512
    assert running.memory.current_mib == 512
    assert running.memory.set("64M") == running.memory.minimum_mib == 256
    assert running.memory.set("16G") == 1024
    assert running.memory.grow("128M") == 1024
    assert running.memory.shrink("256M") == 768


def test_memory_needs_running_machine(vm):
    vm.define()
    assert vm.memory.current_mib == 1024
    with pytest.raises(VMStateError):
        vm.memory.set("512M")
    with pytest.raises(VMStateError):
        vm.memory.stats()


def test_stats(running):
    stats = running.memory.stats()
    assert stats.actual_mib == 1024
    assert stats.free_mib == 100


def test_dimm_plug_and_unplug(running):
    assert running.memory.maximum_mib == 1024
    assert running.memory.plug() == 1152
    assert running.memory.plug("512M") == 1664
    assert running.memory.dimms() == [128, 512]
    assert running.memory.set("1600M") == 1600
    assert running.memory.unplug() == 1152
    with pytest.raises(ConfigurationError, match="no 256 MiB"):
        running.memory.unplug("256M")
    running.memory.unplug("128M")
    with pytest.raises(VMStateError, match="no hot-plugged"):
        running.memory.unplug()


def test_plug_limits(make_vm):
    vm = make_vm("lim", max_memory="1280M", memory_slots=2).start()
    with pytest.raises(ConfigurationError):
        vm.memory.plug(0)
    with pytest.raises(ConfigurationError, match="exceeds max_memory"):
        vm.memory.plug("1G")
    vm.memory.plug("64M")
    vm.memory.plug("64M")
    with pytest.raises(VMStateError, match="slots used"):
        vm.memory.plug("64M")


def test_hotplug_disabled(make_vm):
    vm = make_vm("nohp", max_memory="1G").start()
    with pytest.raises(UnsupportedOperationError, match="hot-plug is off"):
        vm.memory.plug()


def test_xen_raises_maximum_live(hv, tmp_path):
    xen = hv.xen("x", uri="fake:///xen", memory="1G", images_dir=tmp_path).start()
    assert xen.memory.plug("512M") == 1536
    assert xen.memory.unplug("256M") == 1280
    with pytest.raises(ConfigurationError, match="below boot memory"):
        xen.memory.unplug("1G")


def test_stats_period(running, vm):
    running.memory.set_stats_period(5)
    with pytest.raises(ConfigurationError):
        running.memory.set_stats_period(-1)


@pytest.mark.parametrize("size", [-512, "-512M", "-1G"])
def test_negative_memory_is_refused(running, size):
    for call in (running.memory.set, running.memory.plug, running.memory.grow):
        with pytest.raises(ConfigurationError):
            call(size)
    with pytest.raises(ConfigurationError, match="seconds"):
        running.memory.set_stats_period(-1)
    assert running.memory.current_mib == 1024
