"""Test doubles for the backend ports."""

from fakes.connection import FakeConnection, FakeDiskTool, FakeHypervisor
from fakes.domain import FakeDomain

URI = "fake:///session"
TEST_URI = "test:///default"

__all__ = ["TEST_URI", "URI", "FakeConnection", "FakeDiskTool", "FakeDomain", "FakeHypervisor"]
