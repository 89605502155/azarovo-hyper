from azarovo_hyper import VMState


def test_codes_match_libvirt():
    assert VMState.from_code(1) is VMState.RUNNING
    assert VMState.from_code(5) is VMState.SHUTOFF
    assert VMState.from_code(99) is VMState.NOSTATE


def test_activity():
    assert VMState.RUNNING.is_active
    assert VMState.PAUSED.is_active
    assert not VMState.SHUTOFF.is_active
    assert not VMState.UNDEFINED.is_active
    assert not VMState.UNDEFINED.is_defined
    assert VMState.SHUTOFF.is_defined


def test_str():
    assert str(VMState.RUNNING) == "running"
