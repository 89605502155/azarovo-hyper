import pytest

from azarovo_hyper import ConfigurationError, KvmDriver, driver_names, get_driver, register_driver
from azarovo_hyper.drivers import registry


def test_builtin_drivers():
    assert {"kvm", "xen"} <= set(driver_names())
    assert get_driver("KVM") is get_driver("kvm")
    assert isinstance(get_driver("kvm"), KvmDriver)


def test_unknown_driver():
    with pytest.raises(ConfigurationError, match="available"):
        get_driver("vmware")


def test_register_new_driver_and_conflict():
    @register_driver("toy")
    class Toy(KvmDriver):
        pass

    try:
        assert get_driver("toy").name == "toy"
        register_driver("toy")(Toy)
        with pytest.raises(ConfigurationError):

            @register_driver("toy")
            class Other(KvmDriver):
                pass
    finally:
        registry._drivers.pop("toy", None)
        registry._instances.pop("toy", None)
        KvmDriver.name = "kvm"


def test_uri_from_environment(monkeypatch):
    monkeypatch.setenv("AZAROVO_KVM_URI", "qemu+ssh://lab/system")
    assert get_driver("kvm").default_uri() == "qemu+ssh://lab/system"


def test_default_images_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    path = get_driver("kvm").default_images_dir("qemu:///session")
    assert path == tmp_path / "azarovo-hyper" / "images"
