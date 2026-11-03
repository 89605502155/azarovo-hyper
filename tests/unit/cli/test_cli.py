"""setup/doctor against a scripted host."""

import pytest

from azarovo_hyper.cli import main
from azarovo_hyper.cli.doctor import doctor
from azarovo_hyper.cli.setup import PACKAGES, plan, setup
from azarovo_hyper.cli.system import System


class FakeSystem(System):
    def __init__(self, *, distro="ubuntu", root=False, kvm=True, fail_at=None):
        self.distro, self.root, self.kvm, self.fail_at = distro, root, kvm, fail_at
        self.ran = []

    def os_release(self):
        return {"ID": self.distro, "PRETTY_NAME": f"{self.distro} test"}

    def cpu_flags(self):
        return {"vmx", "sse"}

    def which(self, program):
        return f"/usr/bin/{program}"

    def exists(self, path):
        return self.kvm

    def accessible(self, path):
        return self.kvm

    def is_root(self):
        return self.root

    def user(self):
        return "alice"

    def groups(self):
        return {"alice", "libvirt", "kvm"}

    def run(self, command):
        self.ran.append(command)
        return 1 if self.fail_at is not None and len(self.ran) == self.fail_at else 0

    def connect(self, uri):
        if not self.kvm:
            raise RuntimeError("Failed to connect socket\nmore")
        return "QEMU"


def test_plan_uses_sudo_only_when_needed():
    user_plan = plan(FakeSystem())
    assert all(c[0] == "sudo" for c in user_plan)
    assert set(PACKAGES) <= set(user_plan[1])
    assert "virt-viewer" in user_plan[1]
    root_plan = plan(FakeSystem(root=True), viewer=False)
    assert all(c[0] != "sudo" for c in root_plan)
    assert "virt-viewer" not in root_plan[1]
    assert root_plan[-1][-1] == "alice"


def test_setup_runs_everything_then_doctor(capsys):
    system = FakeSystem()
    assert setup(system, assume_yes=True) == 0
    assert len(system.ran) == 4
    assert "ready to run guests" in capsys.readouterr().out


def test_setup_dry_run_and_refusals(monkeypatch, capsys):
    system = FakeSystem()
    assert setup(system, dry_run=True) == 0 and system.ran == []
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    assert setup(system) == 1 and system.ran == []
    assert setup(FakeSystem(distro="fedora"), assume_yes=True) == 2
    assert "Ubuntu only" in capsys.readouterr().out
    failing = FakeSystem(fail_at=2)
    assert setup(failing, assume_yes=True) == 1
    assert len(failing.ran) == 2


def test_doctor_reports_problems(capsys):
    assert doctor(FakeSystem()) == 0
    assert doctor(FakeSystem(kvm=False)) == 1
    out = capsys.readouterr().out
    assert "[FAIL] /dev/kvm" in out and "azarovo-hyper setup" in out
    assert "Failed to connect socket" in out and "more" not in out


def test_real_system_probes():
    system = System()
    assert isinstance(system.os_release(), dict)
    assert isinstance(system.cpu_flags(), set)
    assert system.user()
    assert isinstance(system.groups(), set)
    assert system.run(["true"]) == 0


def test_entry_point(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "azarovo-hyper 0.0.2" in capsys.readouterr().out
    assert main(["setup", "--dry-run"]) in (0, 2)
