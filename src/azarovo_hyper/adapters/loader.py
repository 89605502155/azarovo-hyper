"""Choice of the libvirt backend.

* ``native`` (default): ctypes over the system ``libvirt.so.0``; nothing to
  compile, so ``uv add azarovo-hyper`` is all a project needs;
* ``python``: the official ``libvirt-python`` binding
  (``uv add "azarovo-hyper[libvirt]"``).

Select with ``AZAROVO_LIBVIRT_BACKEND``. Both expose the same API, so the
adapters do not care which one is active.
"""

from __future__ import annotations

import logging
import os
import threading
from types import ModuleType

from azarovo_hyper.errors import BackendUnavailableError

BACKEND_ENV = "AZAROVO_LIBVIRT_BACKEND"
BACKENDS = ("native", "python")

SETUP_HINT = (
    "libvirt is not installed on this machine (libvirt.so.0 was not found).\n"
    "Install the hypervisor with one command:\n"
    "  uv run azarovo-hyper setup        # or: python -m azarovo_hyper setup\n"
    "and check the result with:\n"
    "  uv run azarovo-hyper doctor"
)
BINDING_HINT = (
    "AZAROVO_LIBVIRT_BACKEND=python needs the official binding:\n"
    '  uv add "azarovo-hyper[libvirt]"   # builds libvirt-python, needs libvirt-dev\n'
    "Unset the variable to use the built-in native backend instead."
)

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_quieted: set[str] = set()


def _quiet_handler(_context: object, error: object) -> None:
    """Send libvirt's own error printing to the log instead of stderr."""
    logger.debug("libvirt: %s", error)


def backend_name() -> str:
    name = os.environ.get(BACKEND_ENV, "native").strip().lower() or "native"
    if name not in BACKENDS:
        raise BackendUnavailableError(f"{BACKEND_ENV} must be one of {BACKENDS}, got {name!r}")
    return name


def _import(name: str) -> ModuleType:
    if name == "python":
        try:
            import libvirt
        except ImportError as exc:
            raise BackendUnavailableError(BINDING_HINT) from exc
        return libvirt
    from azarovo_hyper.adapters import native

    if not native.available():
        raise BackendUnavailableError(SETUP_HINT)
    return native


def load_libvirt() -> ModuleType:
    """The active libvirt backend module (raises :class:`BackendUnavailableError`)."""
    name = backend_name()
    module = _import(name)
    with _lock:
        if name not in _quieted:
            module.registerErrorHandler(_quiet_handler, None)
            _quieted.add(name)
    return module


def libvirt_available() -> bool:
    try:
        load_libvirt()
    except BackendUnavailableError:
        return False
    return True
