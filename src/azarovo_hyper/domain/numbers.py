"""Validated numbers: they refuse impossible values the moment they are built.

``PositiveInt(-2)`` raises :class:`~azarovo_hyper.errors.ConfigurationError`
(also a ``ValueError``), so negative RAM, vCPUs, slots or timeouts never reach
the hypervisor. The classes subclass ``int``/``float`` and behave like them.
"""

from __future__ import annotations

import math
from typing import Any, ClassVar, Self

from azarovo_hyper.errors import ConfigurationError


def _describe(name: str, value: object) -> str:
    return f"{name} must be a number, got {value!r}"


class NonNegativeInt(int):
    """A whole number ``>= 0``. Floats are accepted only if they are whole."""

    minimum: ClassVar[int] = 0

    def __new__(cls, value: Any, name: str = "value") -> Self:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigurationError(_describe(name, value))
        if isinstance(value, float) and (not math.isfinite(value) or not value.is_integer()):
            raise ConfigurationError(f"{name} must be a whole number, got {value!r}")
        if value < cls.minimum:
            raise ConfigurationError(f"{name} must be >= {cls.minimum}, got {value!r}")
        return super().__new__(cls, int(value))


class PositiveInt(NonNegativeInt):
    """A whole number ``>= 1`` (vCPUs, video heads, counts)."""

    minimum: ClassVar[int] = 1


class NonNegativeFloat(float):
    """A finite real number ``>= 0`` (timeouts, delays)."""

    minimum: ClassVar[float] = 0.0

    def __new__(cls, value: Any, name: str = "value") -> Self:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigurationError(_describe(name, value))
        if not math.isfinite(value):
            raise ConfigurationError(f"{name} must be finite, got {value!r}")
        if value < cls.minimum:
            raise ConfigurationError(f"{name} must be >= {cls.minimum:g}, got {value!r}")
        return super().__new__(cls, float(value))


class Ratio(NonNegativeFloat):
    """A finite factor ``>= 1`` (overcommit ratios)."""

    minimum: ClassVar[float] = 1.0


def check(kind: type, value: Any, name: str) -> Any:
    """``kind(value, name)``; ``None`` passes through for optional fields."""
    return None if value is None else kind(value, name)
