import pytest

from azarovo_hyper import ConfigurationError, to_mib
from azarovo_hyper.domain.sizes import kib_to_mib, mib_to_kib


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2048, 2048),
        (0, 0),
        (1.5, 2),
        ("512", 512),
        ("512M", 512),
        ("512mb", 512),
        ("2G", 2048),
        ("2 GiB", 2048),
        ("1.5G", 1536),
        ("1T", 1024**2),
        ("  4g ", 4096),
    ],
)
def test_to_mib_accepts_human_sizes(value, expected):
    assert to_mib(value) == expected


@pytest.mark.parametrize(
    "value", ["", "abc", "2X", "-1G", "1..2G", True, None, [], -5, float("nan")]
)
def test_to_mib_rejects_garbage(value):
    with pytest.raises(ConfigurationError):
        to_mib(value)


def test_conversions():
    assert kib_to_mib(2048) == 2
    assert mib_to_kib(2) == 2048
