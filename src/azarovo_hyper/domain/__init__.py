"""Pure domain model: specifications, states, sizes and metrics.

Nothing in this package talks to a hypervisor.
"""

from azarovo_hyper.domain.numbers import NonNegativeFloat, NonNegativeInt, PositiveInt, Ratio
from azarovo_hyper.domain.options import VMOptions
from azarovo_hyper.domain.resources import Demand, HostUsage, ResourcePolicy, Shortfall
from azarovo_hyper.domain.sizes import Size, to_mib
from azarovo_hyper.domain.spec import VMSpec
from azarovo_hyper.domain.state import VMState
from azarovo_hyper.domain.stats import (
    DiskStats,
    GuestMetrics,
    HostInfo,
    InterfaceStats,
    MemoryStats,
)

__all__ = [
    "Demand",
    "DiskStats",
    "GuestMetrics",
    "HostInfo",
    "HostUsage",
    "InterfaceStats",
    "MemoryStats",
    "NonNegativeFloat",
    "NonNegativeInt",
    "PositiveInt",
    "Ratio",
    "ResourcePolicy",
    "Shortfall",
    "Size",
    "VMOptions",
    "VMSpec",
    "VMState",
    "to_mib",
]
