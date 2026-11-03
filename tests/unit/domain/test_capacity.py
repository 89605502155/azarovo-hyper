import pytest

from azarovo_hyper import ConfigurationError, HostUsage, ResourcePolicy
from azarovo_hyper.domain.resources import Demand, Shortfall, shortfalls

USAGE = HostUsage(
    "h", total_mib=8192, available_mib=6000, cpus=4, guest_vcpus=6, guest_unbacked_mib=1000
)


DEFAULT = ResourcePolicy()


def check(demand, policy=DEFAULT, free=None, usage=USAGE):
    return shortfalls(demand, policy=policy, usage=usage, free_disk_mib=free)


def test_memory_headroom_counts_reserve_and_guest_ceilings():
    assert check(Demand(memory_mib=4488)) == []
    assert [s.resource for s in check(Demand(memory_mib=4489))] == ["memory"]
    assert check(Demand(memory_mib=9000), ResourcePolicy(memory_overcommit=2)) == []


def test_cpu_limits():
    assert check(Demand(vcpus=10, vm_vcpus=4)) == []
    assert check(Demand(vcpus=11)) != []
    over = check(Demand(vm_vcpus=5))
    assert over == [Shortfall("cpu", 5, 4)]


def test_disk_headroom():
    assert check(Demand(disk_mib=1000), free=2024, usage=None) == []
    assert check(Demand(disk_mib=1001), free=2024, usage=None) != []
    assert check(Demand(disk_mib=1), free=None, usage=None) == []


def test_demand_algebra_and_text():
    total = Demand(1, 2, 3, 4) + Demand(10, 20, 30, 1)
    assert total == Demand(11, 22, 33, 4)
    assert not Demand()
    assert str(Shortfall("memory", 100, -5)) == "memory: requested 100 MiB, available 0 MiB"
    assert str(Shortfall("cpu", 9, 4)) == "cpu: requested 9, available 4"


@pytest.mark.parametrize(
    "options",
    [{"memory_overcommit": 0.5}, {"cpu_overcommit": 0}, {"host_memory_reserve": "x"}],
)
def test_bad_policy(options):
    with pytest.raises(ConfigurationError):
        ResourcePolicy(**options)
