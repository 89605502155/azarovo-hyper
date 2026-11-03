"""Human-friendly sizes: ``2048``, ``"2G"``, ``"512M"``, ``"1.5GiB"``.

Plain integers are mebibytes. Strings use binary multiples, so ``"1G"`` is
1024 MiB, matching how libvirt and qemu-img interpret ``G``.
"""

from __future__ import annotations

import math
import re

from azarovo_hyper.errors import ConfigurationError

Size = int | float | str

_MIB_PER_UNIT = {
    "": 1,
    "M": 1,
    "MB": 1,
    "MIB": 1,
    "G": 1024,
    "GB": 1024,
    "GIB": 1024,
    "T": 1024**2,
    "TB": 1024**2,
    "TIB": 1024**2,
}
_PATTERN = re.compile(r"\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*")


def to_mib(value: Size) -> int:
    """Convert a size to whole mebibytes (fractions are rounded up)."""
    if isinstance(value, bool):
        raise ConfigurationError(f"size must be a number or a string, got {value!r}")
    if isinstance(value, int | float):
        number, unit = float(value), ""
    elif isinstance(value, str):
        match = _PATTERN.fullmatch(value)
        if match is None:
            raise ConfigurationError(f"cannot parse size {value!r}; use e.g. 2048, '2G', '512M'")
        number, unit = float(match.group(1)), match.group(2).upper()
    else:
        raise ConfigurationError(f"size must be a number or a string, got {value!r}")
    if unit not in _MIB_PER_UNIT:
        raise ConfigurationError(f"unknown size unit {unit!r} in {value!r}; use M, G or T")
    if number < 0 or math.isnan(number) or math.isinf(number):
        raise ConfigurationError(f"size must be a finite non-negative number, got {value!r}")
    return math.ceil(number * _MIB_PER_UNIT[unit])


def kib_to_mib(kib: float) -> float:
    return kib / 1024


def mib_to_kib(mib: float) -> int:
    return int(mib * 1024)
