"""Disks and the CD-ROM: ISO insert/eject, disk hot-plug, I/O counters."""

from __future__ import annotations

from pathlib import Path

from azarovo_hyper.decorators import guarded, requires_running
from azarovo_hyper.domain.sizes import Size, to_mib
from azarovo_hyper.domain.stats import DiskStats
from azarovo_hyper.domain.xml_view import DomainXml
from azarovo_hyper.drivers.base import next_target
from azarovo_hyper.errors import ConfigurationError, UnsupportedOperationError
from azarovo_hyper.vm.session import SessionBound


class StorageController(SessionBound):
    """``vm.storage``"""

    __slots__ = ()

    def _view(self) -> DomainXml:
        return DomainXml(self._session.domain().xml())

    def _live(self) -> bool:
        return self._session.domain().state().is_active

    # ── CD-ROM ──────────────────────────────────────────────────────────────
    @property
    @guarded
    def iso(self) -> Path | None:
        """ISO image currently in the CD-ROM drive."""
        cdrom = self._view().cdrom()
        return None if cdrom is None or not cdrom.source else Path(cdrom.source)

    @guarded
    def insert(self, iso: str | Path) -> None:
        """Put an ISO into the drive (works while the guest runs)."""
        path = Path(iso).expanduser().absolute()
        if not path.is_file():
            raise ConfigurationError(f"ISO image not found: {path}")
        self._swap_media(path)

    @guarded
    def eject(self) -> None:
        """Empty the drive, e.g. after the OS is installed."""
        self._swap_media(None)

    def _swap_media(self, iso: Path | None) -> None:
        session = self._session
        xml = session.driver.cdrom_xml(session.spec, iso)
        session.domain().update_device(str(xml), live=self._live(), config=True)

    # ── disks ───────────────────────────────────────────────────────────────
    @guarded
    def disks(self) -> dict[str, str]:
        """``{target: image path}`` of every disk."""
        return self._view().disks()

    @guarded
    def attach(
        self,
        path: str | Path | None = None,
        *,
        size: Size = "10G",
        bus: str | None = None,
        persist: bool = True,
    ) -> str:
        """Attach a disk (hot-plug when running); returns its target, e.g. ``vdb``.

        Without ``path`` a new image is created next to the main disk and
        removed again by ``delete()``.
        """
        session = self._session
        live = self._live()
        if live and not session.driver.capabilities.disk_hotplug:
            raise UnsupportedOperationError(f"{session.driver.name}: no disk hot-plug")
        bus = bus or session.spec.disk_bus or session.driver.hardware.disk_bus
        target = next_target(bus, self._view().targets())
        fmt = session.spec.disk_format
        created = False
        if path is None:
            image = session.images_dir / f"{session.name}-{target}.{fmt}"
            created = session.disk_tool.create(image, to_mib(size), fmt)
        else:
            image = Path(path).expanduser().absolute()
            fmt = "raw" if image.suffix in (".img", ".raw") else fmt
        xml = session.driver.disk_xml(image, target, bus, fmt)
        try:
            session.domain().attach(str(xml), live=live, config=persist or not live)
        except BaseException:
            if created:
                session.disk_tool.remove(image)
            raise
        if created:
            session.owned_disks.add(image)
        return target

    @guarded
    def detach(self, target: str, *, persist: bool = True, remove_file: bool = False) -> None:
        """Detach a disk by target name; optionally delete its image."""
        session = self._session
        disks = self.disks()
        if target not in disks:
            raise ConfigurationError(f"{session.name}: no disk {target!r}; have {sorted(disks)}")
        image = Path(disks[target])
        if image == session.disk_path:
            raise ConfigurationError(f"{session.name}: refusing to detach the boot disk")
        bus = session.spec.disk_bus or session.driver.hardware.disk_bus
        xml = session.driver.disk_xml(image, target, bus)
        live = self._live()
        session.domain().detach(str(xml), live=live, config=persist or not live)
        if remove_file or image in session.owned_disks:
            session.disk_tool.remove(image)
            session.owned_disks.discard(image)

    @guarded
    @requires_running
    def stats(self) -> dict[str, DiskStats]:
        """Cumulative I/O counters of every disk."""
        domain = self._session.domain()
        result = {}
        for device in self.disks():
            rd_req, rd_bytes, wr_req, wr_bytes, errors = domain.block_stats(device)
            result[device] = DiskStats(device, rd_req, rd_bytes, wr_req, wr_bytes, max(errors, 0))
        return result
