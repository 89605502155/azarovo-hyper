"""Test doubles for the backend ports."""

from azarovo_hyper.resources import Admission
from fakes.connection import FakeConnection, FakeDiskTool, FakeHypervisor
from fakes.domain import FakeDomain

URI = "fake:///session"
TEST_URI = "test:///default"


def fake_admission(free_mib: float = 10**7) -> Admission:
    """Fake disk images take no space, so pretend the file system has ``free_mib``."""
    return Admission(free_space=lambda _path: free_mib)


__all__ = [
    "TEST_URI",
    "URI",
    "FakeConnection",
    "FakeDiskTool",
    "FakeDomain",
    "FakeHypervisor",
    "fake_admission",
]
