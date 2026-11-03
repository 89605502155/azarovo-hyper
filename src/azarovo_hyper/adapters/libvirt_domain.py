"""libvirt implementation of the :class:`~azarovo_hyper.ports.Domain` port."""

from __future__ import annotations

from typing import Any

from azarovo_hyper.adapters.errors import is_libvirt_error, libvirt_errors
from azarovo_hyper.adapters.loader import load_libvirt
from azarovo_hyper.decorators import decorate_public_methods
from azarovo_hyper.domain.state import VMState

_UNDEFINE_FLAGS = (
    "VIR_DOMAIN_UNDEFINE_MANAGED_SAVE",
    "VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA",
    "VIR_DOMAIN_UNDEFINE_NVRAM",
    "VIR_DOMAIN_UNDEFINE_CHECKPOINTS_METADATA",
)
_ADDRESS_SOURCES = (
    "VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT",
    "VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_LEASE",
    "VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_ARP",
)


@decorate_public_methods(libvirt_errors)
class LibvirtDomain:
    """Thin wrapper over ``virDomain`` with the library's error types."""

    def __init__(self, domain: Any, connection: Any) -> None:
        self._dom = domain
        self._conn = connection
        self._lib = load_libvirt()

    @property
    def name(self) -> str:
        return str(self._dom.name())

    @property
    def uuid(self) -> str:
        return str(self._dom.UUIDString())

    def _flags(self, *, live: bool, config: bool) -> int:
        flags = self._lib.VIR_DOMAIN_AFFECT_LIVE if live else 0
        return flags | (self._lib.VIR_DOMAIN_AFFECT_CONFIG if config else 0)

    # ── lifecycle ───────────────────────────────────────────────────────────
    def state(self) -> VMState:
        return VMState.from_code(self._dom.state()[0])

    def start(self) -> None:
        self._dom.create()

    def shutdown(self) -> None:
        self._dom.shutdown()

    def destroy(self) -> None:
        self._dom.destroy()

    def reboot(self) -> None:
        self._dom.reboot(0)

    def reset(self) -> None:
        self._dom.reset(0)

    def suspend(self) -> None:
        self._dom.suspend()

    def resume(self) -> None:
        self._dom.resume()

    def undefine(self) -> None:
        """Undefine with as many cleanup flags as the driver accepts."""
        for count in range(len(_UNDEFINE_FLAGS), 0, -1):
            flags = 0
            for name in _UNDEFINE_FLAGS[:count]:
                flags |= getattr(self._lib, name, 0)
            try:
                self._dom.undefineFlags(flags)
                return
            except Exception as exc:
                if not is_libvirt_error(exc):
                    raise
        self._dom.undefine()

    def xml(self, *, inactive: bool = False) -> str:
        return str(self._dom.XMLDesc(self._lib.VIR_DOMAIN_XML_INACTIVE if inactive else 0))

    def autostart(self) -> bool:
        return bool(self._dom.autostart())

    def set_autostart(self, enabled: bool) -> None:
        self._dom.setAutostart(1 if enabled else 0)

    # ── memory ──────────────────────────────────────────────────────────────
    def max_memory_kib(self) -> int:
        return int(self._dom.maxMemory())

    def set_memory(self, kib: int, *, live: bool, config: bool) -> None:
        self._dom.setMemoryFlags(kib, self._flags(live=live, config=config))

    def set_max_memory(self, kib: int, *, live: bool, config: bool) -> None:
        flags = self._flags(live=live, config=config) | self._lib.VIR_DOMAIN_MEM_MAXIMUM
        self._dom.setMemoryFlags(kib, flags)

    def memory_stats(self) -> dict[str, int]:
        return {str(k): int(v) for k, v in self._dom.memoryStats().items()}

    def set_stats_period(self, seconds: int, *, live: bool, config: bool) -> None:
        self._dom.setMemoryStatsPeriod(seconds, self._flags(live=live, config=config))

    # ── CPU ─────────────────────────────────────────────────────────────────
    def vcpus(self) -> int:
        return int(self._dom.info()[3])

    def set_vcpus(self, count: int, *, live: bool, config: bool) -> None:
        self._dom.setVcpusFlags(count, self._flags(live=live, config=config))

    def cpu_time_ns(self) -> int:
        return int(self._dom.info()[4])

    # ── devices ─────────────────────────────────────────────────────────────
    def attach(self, xml: str, *, live: bool, config: bool) -> None:
        self._dom.attachDeviceFlags(xml, self._flags(live=live, config=config))

    def detach(self, xml: str, *, live: bool, config: bool) -> None:
        self._dom.detachDeviceFlags(xml, self._flags(live=live, config=config))

    def update_device(self, xml: str, *, live: bool, config: bool) -> None:
        self._dom.updateDeviceFlags(xml, self._flags(live=live, config=config))

    def block_stats(self, device: str) -> tuple[int, int, int, int, int]:
        rd_req, rd_bytes, wr_req, wr_bytes, errors = self._dom.blockStats(device)
        return int(rd_req), int(rd_bytes), int(wr_req), int(wr_bytes), int(errors)

    def interface_stats(self, device: str) -> tuple[int, ...]:
        return tuple(int(v) for v in self._dom.interfaceStats(device))

    def addresses(self) -> dict[str, list[str]]:
        """IP addresses per interface, asking the agent, DHCP leases, then ARP."""
        for source in _ADDRESS_SOURCES:
            try:
                reply = self._dom.interfaceAddresses(getattr(self._lib, source, 0))
            except Exception as exc:
                if not is_libvirt_error(exc):
                    raise
                continue
            found = {
                iface: [a["addr"] for a in (info.get("addrs") or [])]
                for iface, info in reply.items()
                if iface != "lo"
            }
            if any(found.values()):
                return found
        return {}

    # ── display and snapshots ───────────────────────────────────────────────
    def screenshot(self, screen: int = 0) -> tuple[str, bytes]:
        stream = self._conn.newStream(0)
        chunks: list[bytes] = []
        try:
            mime = self._dom.screenshot(stream, screen, 0)
            stream.recvAll(lambda _stream, data, sink: sink.append(data), chunks)
            stream.finish()
        except BaseException:
            stream.abort()
            raise
        return str(mime), b"".join(chunks)

    def snapshot_create(self, xml: str) -> None:
        self._dom.snapshotCreateXML(xml, 0)

    def snapshot_names(self) -> list[str]:
        return sorted(str(name) for name in self._dom.snapshotListNames(0))

    def snapshot_revert(self, name: str) -> None:
        self._dom.revertToSnapshot(self._dom.snapshotLookupByName(name, 0), 0)

    def snapshot_delete(self, name: str) -> None:
        self._dom.snapshotLookupByName(name, 0).delete(0)
