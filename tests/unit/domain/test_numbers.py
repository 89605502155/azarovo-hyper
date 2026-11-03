"""Negative or nonsensical numbers are refused where they enter the library."""

import math

import pytest

from azarovo_hyper import (
    ConfigurationError,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    ResourcePolicy,
    VMSpec,
    validated,
)
from azarovo_hyper.domain.numbers import Ratio

BAD = [-1, -0.5, True, "3", None, [], math.nan, math.inf]


@pytest.mark.parametrize("value", [*BAD, 1.5])
def test_non_negative_int_refuses(value):
    with pytest.raises(ConfigurationError):
        NonNegativeInt(value, "slots")


def test_valid_numbers_behave_like_builtins():
    assert NonNegativeInt(0) == 0 and NonNegativeInt(4.0) == 4
    assert PositiveInt(3) + 1 == 4 and isinstance(PositiveInt(3), int)
    assert NonNegativeFloat(0) == 0.0 and NonNegativeFloat(2) * 2 == 4.0
    assert Ratio(1) == 1.0
    with pytest.raises(ConfigurationError, match="vcpus must be >= 1, got 0"):
        PositiveInt(0, "vcpus")
    with pytest.raises(ConfigurationError, match=">= 1"):
        Ratio(0.9, "memory_overcommit")
    with pytest.raises(ValueError):
        NonNegativeFloat(-0.1, "timeout")
    with pytest.raises(ConfigurationError, match="finite"):
        NonNegativeFloat(math.inf, "timeout")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("vcpus", -2),
        ("max_vcpus", -8),
        ("memory_slots", -1),
        ("balloon_period", -5),
        ("pcie_ports", -4),
        ("video_heads", -1),
        ("vcpus", 2.5),
        ("memory", "-2G"),
        ("memory", -2048),
        ("current_memory", "-1G"),
        ("min_memory", -1),
        ("max_memory", "-8G"),
        ("dimm_size", -128),
        ("disk_size", "-20G"),
    ],
)
def test_spec_refuses_negative_numbers(field, value):
    with pytest.raises(ConfigurationError, match=field):
        VMSpec(**{field: value})


def test_spec_stores_validated_types():
    spec = VMSpec(vcpus=3, memory_slots=0)
    assert type(spec.vcpus) is PositiveInt and type(spec.memory_slots) is NonNegativeInt


@pytest.mark.parametrize(
    "options",
    [
        {"memory_overcommit": -1},
        {"cpu_overcommit": -4},
        {"host_memory_reserve": "-1G"},
        {"host_disk_reserve": -1},
    ],
)
def test_policy_refuses_negative_numbers(options):
    with pytest.raises(ConfigurationError, match=next(iter(options))):
        ResourcePolicy(**options)


def test_validated_decorator():
    @validated(count=PositiveInt, timeout=NonNegativeFloat)
    def act(count, *, timeout=1.0, label=None):
        return count, timeout

    assert act(2, timeout=0) == (2, 0.0)
    with pytest.raises(ConfigurationError, match="count"):
        act(-1)
    with pytest.raises(ConfigurationError, match="timeout"):
        act(1, timeout=-3)
    with pytest.raises(TypeError, match="no parameters"):
        validated(missing=PositiveInt)(act)
