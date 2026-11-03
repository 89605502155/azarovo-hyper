"""Remote display: connection URI, screenshots and a viewer window."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from azarovo_hyper.decorators import guarded, requires_capability, requires_running
from azarovo_hyper.domain.xml_view import DomainXml, Graphics
from azarovo_hyper.errors import UnsupportedOperationError
from azarovo_hyper.vm.session import SessionBound

_EXTENSIONS = {"image/png": ".png", "image/x-portable-pixmap": ".ppm"}


class DisplayController(SessionBound):
    """``vm.display``"""

    __slots__ = ()

    @guarded
    def graphics(self) -> list[Graphics]:
        return DomainXml(self._session.domain().xml()).graphics()

    @property
    @guarded
    def uri(self) -> str | None:
        """``spice://127.0.0.1:5900`` style address of a running guest."""
        for item in self.graphics():
            if item.uri:
                return item.uri
        return None

    @guarded
    @requires_running
    @requires_capability("screenshot")
    def screenshot(self, path: str | Path | None = None, *, screen: int = 0) -> bytes:
        """Grab the screen; with ``path`` also save it (extension follows the format)."""
        mime, data = self._session.domain().screenshot(screen)
        if path is not None:
            target = Path(path).expanduser()
            if not target.suffix:
                target = target.with_suffix(_EXTENSIONS.get(mime, ".img"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return data

    @guarded
    @requires_running
    def open_viewer(self, *, binary: str = "virt-viewer") -> subprocess.Popen[bytes]:
        """Open a viewer window; it is closed with the machine (stop/close/delete)."""
        executable = shutil.which(binary)
        if executable is None:
            raise UnsupportedOperationError(f"{binary} is not installed")
        session = self._session
        process = subprocess.Popen(
            [executable, "--connect", session.uri, "--wait", session.name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        session.viewers.append(process)
        return process

    @guarded
    def close_viewers(self) -> None:
        self._session.close_viewers()
