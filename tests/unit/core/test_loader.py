import builtins

import pytest

from azarovo_hyper import BackendUnavailableError, libvirt_available
from azarovo_hyper.adapters import loader


def test_missing_binding(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "libvirt":
            raise ImportError("no libvirt")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(BackendUnavailableError, match="pip install"):
        loader.load_libvirt()
    assert not libvirt_available()


def test_quiet_handler_logs(caplog):
    with caplog.at_level("DEBUG", logger="azarovo_hyper.adapters.loader"):
        loader._quiet_handler(None, ("err", 1, "message"))
    assert "message" in caplog.text
