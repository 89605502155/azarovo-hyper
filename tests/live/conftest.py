"""Live tests: real KVM guests through ``qemu:///session``.

Opt-in with ``AZAROVO_LIVE=1`` (needs libvirt, qemu-kvm and access to
/dev/kvm). The guests have no OS: they boot to an empty firmware screen,
which is enough to exercise every hypervisor-side operation.
"""

from __future__ import annotations

import gc
import os
import uuid

import pytest

from azarovo_hyper import Hyper, QemuImg, libvirt_available
from azarovo_hyper.adapters.pool import ConnectionPool

LIVE_URI = os.environ.get("AZAROVO_LIVE_URI", "qemu:///session")

if os.environ.get("AZAROVO_LIVE") != "1":
    pytest.skip("set AZAROVO_LIVE=1 to boot real KVM guests", allow_module_level=True)
if not libvirt_available() or not os.access("/dev/kvm", os.R_OK | os.W_OK):
    pytest.skip("needs libvirt-python and /dev/kvm", allow_module_level=True)


def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.live)


@pytest.fixture
def live_pool():
    pool = ConnectionPool()
    yield pool
    pool.close_all()


@pytest.fixture
def live(live_pool):
    hyper = Hyper(pool=live_pool, disk_tool=QemuImg())
    yield hyper
    hyper.close()
    gc.collect()


@pytest.fixture
def boot(live, tmp_path):
    created = []

    def factory(**options):
        options.setdefault("images_dir", tmp_path)
        options.setdefault("disk_size", "64M")
        options.setdefault("memory", "256M")
        options.setdefault("min_memory", "128M")
        options.setdefault("max_memory", "1G")
        options.setdefault("vcpus", 1)
        options.setdefault("max_vcpus", 4)
        vm = live.kvm(f"live-{uuid.uuid4().hex[:8]}", uri=LIVE_URI, **options)
        created.append(vm)
        return vm

    yield factory
    for vm in created:
        if not vm.closed:
            vm.delete()
