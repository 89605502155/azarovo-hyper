import builtins

import pytest

from azarovo_hyper import BackendUnavailableError, libvirt_available
from azarovo_hyper.adapters import loader, native


def test_native_backend_is_the_default(monkeypatch):
    monkeypatch.delenv("AZAROVO_LIBVIRT_BACKEND", raising=False)
    assert loader.backend_name() == "native"
    assert loader.load_libvirt() is native


def test_missing_system_libvirt_points_to_setup(monkeypatch):
    monkeypatch.setattr(native, "available", lambda: False)
    with pytest.raises(BackendUnavailableError, match="azarovo-hyper setup"):
        loader.load_libvirt()
    assert not libvirt_available()


def test_python_backend_without_binding(monkeypatch):
    monkeypatch.setenv("AZAROVO_LIBVIRT_BACKEND", "python")
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "libvirt":
            raise ImportError("no libvirt")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(BackendUnavailableError, match=r"azarovo-hyper\[libvirt\]"):
        loader.load_libvirt()


def test_unknown_backend(monkeypatch):
    monkeypatch.setenv("AZAROVO_LIBVIRT_BACKEND", "cffi")
    with pytest.raises(BackendUnavailableError, match="must be one of"):
        loader.load_libvirt()


def test_quiet_handler_logs(caplog):
    with caplog.at_level("DEBUG", logger="azarovo_hyper.adapters.loader"):
        loader._quiet_handler(None, ("err", 1, "message"))
    assert "message" in caplog.text
