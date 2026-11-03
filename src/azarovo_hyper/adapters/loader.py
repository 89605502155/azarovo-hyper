"""Lazy import of the ``libvirt`` binding.

The package imports and its unit tests run without libvirt; the binding is only
needed once a real connection is opened.
"""

from __future__ import annotations

import logging
import threading
from types import ModuleType

from azarovo_hyper.errors import BackendUnavailableError

INSTALL_HINT = (
    "The libvirt Python binding is not installed. Install it with:\n"
    "  sudo apt install -y pkg-config libvirt-dev python3-dev   # Debian/Ubuntu\n"
    "  sudo dnf install -y pkgconf-pkg-config libvirt-devel python3-devel   # Fedora\n"
    '  pip install "azarovo-hyper[libvirt]"'
)

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_handler_installed = False


def _quiet_handler(_context: object, error: object) -> None:
    """Send libvirt's own error printing to the log instead of stderr."""
    logger.debug("libvirt: %s", error)


def load_libvirt() -> ModuleType:
    """Return the ``libvirt`` module or raise :class:`BackendUnavailableError`."""
    global _handler_installed
    try:
        import libvirt
    except ImportError as exc:
        raise BackendUnavailableError(INSTALL_HINT) from exc
    with _lock:
        if not _handler_installed:
            libvirt.registerErrorHandler(_quiet_handler, None)
            _handler_installed = True
    return libvirt


def libvirt_available() -> bool:
    try:
        load_libvirt()
    except BackendUnavailableError:
        return False
    return True
