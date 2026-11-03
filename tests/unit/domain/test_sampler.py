from azarovo_hyper.domain.sampler import CpuSampler


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_first_sample_is_baseline_then_percentage():
    clock = Clock()
    sampler = CpuSampler(clock)
    assert sampler.sample(0, 2) == 0
    clock.now = 1.0
    assert sampler.sample(1_000_000_000, 2) == 50


def test_counter_reset_and_bad_input():
    clock = Clock()
    sampler = CpuSampler(clock)
    sampler.sample(5_000, 1)
    clock.now = 1
    assert sampler.sample(1_000, 1) == 0
    assert sampler.sample(9_000, 0) == 0
    assert sampler.sample(9_000, 1) == 0


def test_capped_and_reset():
    clock = Clock()
    sampler = CpuSampler(clock)
    sampler.sample(0, 1)
    clock.now = 1
    assert sampler.sample(10**12, 1) == 100
    sampler.reset()
    assert sampler.sample(10**13, 1) == 0
