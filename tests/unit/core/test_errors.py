import sys
import types

import pytest

from azarovo_hyper import (
    BackendError,
    ConnectionFailedError,
    DomainNotFoundError,
    HyperError,
    OperationTimeoutError,
    UnsupportedOperationError,
    VMStateError,
)
from azarovo_hyper.adapters.errors import libvirt_errors, translate


class libvirtError(Exception):  # noqa: N801 - mimics the binding's class name
    def __init__(self, code):
        super().__init__(f"code {code}")
        self.code = code

    def get_error_code(self):
        return self.code


@pytest.fixture
def fake_libvirt(monkeypatch):
    module = types.SimpleNamespace(
        VIR_ERR_NO_DOMAIN=42,
        VIR_ERR_OPERATION_INVALID=55,
        VIR_ERR_NO_SUPPORT=3,
        VIR_ERR_OPERATION_TIMEOUT=68,
        VIR_ERR_RPC=39,
    )
    monkeypatch.setitem(sys.modules, "libvirt", module)
    return module


@pytest.mark.parametrize(
    ("code", "error"),
    [
        (42, DomainNotFoundError),
        (55, VMStateError),
        (3, UnsupportedOperationError),
        (68, OperationTimeoutError),
        (39, ConnectionFailedError),
        (1, BackendError),
    ],
)
def test_translate_codes(fake_libvirt, code, error):
    assert type(translate(libvirtError(code))) is error


def test_decorator_only_touches_libvirt_errors(fake_libvirt):
    @libvirt_errors
    def boom(exc):
        raise exc

    with pytest.raises(DomainNotFoundError) as info:
        boom(libvirtError(42))
    assert isinstance(info.value.__cause__, libvirtError)
    with pytest.raises(KeyError):
        boom(KeyError("x"))


def test_translate_without_module(monkeypatch):
    monkeypatch.delitem(sys.modules, "libvirt", raising=False)
    assert type(translate(libvirtError(42))) is BackendError


def test_hierarchy():
    assert issubclass(OperationTimeoutError, TimeoutError)
    for error in (BackendError, DomainNotFoundError, VMStateError):
        assert issubclass(error, HyperError)
