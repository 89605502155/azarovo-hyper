import pytest

from azarovo_hyper import ConfigurationError, DomainNotFoundError, Hyper, VMSpec, hyper
from fakes import URI


def test_factory_creates_nothing_until_start(hv, fake, disks):
    vm = hv.kvm("lazy", uri=URI)
    assert vm.state.name == "UNDEFINED"
    assert hv.pool.active() == {}
    assert disks.created == []
    assert hv.machines == [vm]


def test_hyper_shortcut_and_options():
    assert isinstance(hyper(), Hyper)
    with pytest.raises(ConfigurationError, match="unknown options"):
        Hyper().kvm(memroy="1G")
    with pytest.raises(ConfigurationError):
        Hyper(pool=object(), connector=lambda uri: None)


def test_preset_and_overrides(hv):
    vm = hv.kvm("p", uri=URI, preset="ubuntu", memory="6G")
    assert vm.spec.memory_mib == 6144
    assert vm.spec.min_memory_mib == 1536


def test_spec_object_and_driver_defaults(hv):
    vm = hv.kvm(uri=URI, spec=VMSpec(name="s"), vcpus=3)
    assert (vm.name, vm.spec.vcpus, vm.spec.video, vm.hypervisor) == ("s", 3, "virtio", "kvm")
    xen = hv.xen("x", uri="fake:///xen")
    assert (xen.spec.video, xen.spec.disk_bus) == ("vga", "xen")


def test_generic_machine_and_getattr(hv):
    assert hv.machine("xen", "g", uri=URI).hypervisor == "xen"
    with pytest.raises(AttributeError):
        _ = hv.vmware
    with pytest.raises(AttributeError):
        _ = hv._private


def test_list_host_and_get(hv, make_vm):
    vm = make_vm("existing", vcpus=1, max_vcpus=4, memory="512M", min_memory="128M").define()
    assert hv.list(uri=URI) == ["existing"]
    assert hv.host(uri=URI).hostname == "fakehost"
    again = hv.get("existing", uri=URI)
    assert again.spec.max_vcpus == 4
    assert again.spec.memory_mib == 512
    assert again.disk_path == vm.disk_path
    assert again._session.owns_disk
    with pytest.raises(DomainNotFoundError):
        hv.get("missing", uri=URI)


def test_close_closes_every_machine(hv, make_vm):
    a, b = make_vm("a").start(timeout=1), make_vm("b").start(timeout=1)
    hv.close()
    assert a.closed and b.closed
    assert hv.machines == []
    assert hv.pool.active() == {}


def test_context_manager(pool, disks):
    with Hyper(pool=pool, disk_tool=disks) as h:
        vm = h.kvm("ctx", uri=URI)
    assert vm.closed
