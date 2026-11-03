import pytest

from azarovo_hyper import ConfigurationError, VMStateError


def test_vcpu_hotplug(running):
    assert running.cpu.count == 2
    assert running.cpu.maximum == 8
    assert running.cpu.set(4) == 4
    assert running.cpu.plug() == 5
    assert running.cpu.unplug(2) == 3
    with pytest.raises(ConfigurationError):
        running.cpu.set(9)
    with pytest.raises(ConfigurationError):
        running.cpu.set(0)


def test_vcpus_on_stopped_machine(vm):
    assert vm.cpu.count == 2
    vm.define()
    vm.cpu.set(3)
    assert vm.cpu.count == 3


def test_usage(running):
    assert running.cpu.usage() == 0
    assert running.cpu.time_ns() > 0
    assert 0 <= running.cpu.usage() <= 100


def test_usage_needs_running(vm):
    vm.define()
    with pytest.raises(VMStateError):
        vm.cpu.usage()


def test_xen_vcpus(hv, tmp_path):
    xen = hv.xen("xc", uri="fake:///xen", images_dir=tmp_path, max_vcpus=4).start()
    assert xen.cpu.set(4) == 4
