"""Guest networking: interfaces, addresses and traffic counters."""

from __future__ import annotations

from azarovo_hyper.decorators import guarded, requires_running
from azarovo_hyper.domain.stats import InterfaceStats
from azarovo_hyper.domain.xml_view import DomainXml
from azarovo_hyper.vm.session import SessionBound


class NetworkController(SessionBound):
    """``vm.network``"""

    __slots__ = ()

    @guarded
    def interfaces(self) -> list[str]:
        """Host-side device names (``vnet0`` ...) of a running guest."""
        return DomainXml(self._session.domain().xml()).interfaces()

    @guarded
    @requires_running
    def addresses(self) -> dict[str, list[str]]:
        """Guest IP addresses (needs the guest agent or a DHCP lease)."""
        return self._session.domain().addresses()

    @guarded
    @requires_running
    def stats(self) -> dict[str, InterfaceStats]:
        domain = self._session.domain()
        result = {}
        for device in self.interfaces():
            rx_bytes, rx_packets, *_rx, tx_bytes, tx_packets = domain.interface_stats(device)[:6]
            result[device] = InterfaceStats(device, rx_bytes, rx_packets, tx_bytes, tx_packets)
        return result
