"""Integration tests against libvirt's built-in ``test:///default`` driver.

It runs the real libvirt-python binding and the real XML parser without
KVM, so these tests also run in CI. A keeper connection stays open for the
whole session: the test driver forgets its state when the last connection
closes, while a real libvirtd would not.
"""

from __future__ import annotations

import gc
import shutil
import uuid

import pytest

from azarovo_hyper import Hyper, QemuImg, libvirt_available
from azarovo_hyper.adapters.pool import ConnectionPool
from fakes import TEST_URI

pytestmark = pytest.mark.libvirt

if not libvirt_available():
    pytest.skip("libvirt-python is not installed", allow_module_level=True)
if shutil.which("qemu-img") is None:
    pytest.skip("qemu-img is not installed", allow_module_level=True)


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.libvirt)


@pytest.fixture(scope="session")
def keeper():
    import libvirt

    connection = libvirt.open(TEST_URI)
    yield connection
    connection.close()


@pytest.fixture
def real_pool(keeper):
    pool = ConnectionPool()
    yield pool
    pool.close_all()


@pytest.fixture
def lv(real_pool):
    hyper = Hyper(pool=real_pool, disk_tool=QemuImg())
    yield hyper
    hyper.close()
    gc.collect()


@pytest.fixture
def make(lv, tmp_path):
    created = []

    def factory(**options):
        options.setdefault("images_dir", tmp_path)
        options.setdefault("disk_size", "16M")
        options.setdefault("memory", "512M")
        options.setdefault("min_memory", "128M")
        options.setdefault("max_memory", "2G")
        vm = lv.kvm(f"it-{uuid.uuid4().hex[:8]}", uri=TEST_URI, **options)
        created.append(vm)
        return vm

    yield factory
    for vm in created:
        if not vm.closed:
            vm.delete()
