import pytest

from azarovo_hyper import ConfigurationError, UnsupportedOperationError


def test_iso_insert_and_eject(make_vm, tmp_path):
    iso = tmp_path / "os.iso"
    iso.write_text("iso")
    vm = make_vm("cd", iso=iso).start()
    assert vm.storage.iso == iso
    vm.storage.eject()
    assert vm.storage.iso is None
    vm.storage.insert(iso)
    assert vm.storage.iso == iso
    with pytest.raises(ConfigurationError, match="not found"):
        vm.storage.insert(tmp_path / "missing.iso")


def test_disk_hotplug_and_cleanup(running, disks):
    target = running.storage.attach(size="1G")
    assert target == "vdb"
    image = running._session.images_dir / "vm1-vdb.qcow2"
    assert running.storage.disks()["vdb"] == str(image)
    assert running.storage.attach(size="1G") == "vdc"
    running.storage.detach("vdb")
    assert not image.exists()
    assert "vdb" not in running.storage.disks()
    third = running._session.images_dir / "vm1-vdc.qcow2"
    running.delete()
    assert not third.exists()


def test_attach_existing_image(running, tmp_path):
    raw = tmp_path / "data.img"
    raw.write_text("x")
    target = running.storage.attach(raw)
    assert target == "vdb"
    running.storage.detach(target)
    assert raw.exists()
    running.storage.attach(raw)
    running.storage.detach("vdb", remove_file=True)
    assert not raw.exists()


def test_attach_failure_removes_new_image(running, monkeypatch):
    def broken(*_a, **_k):
        raise RuntimeError("no slots")

    monkeypatch.setattr("fakes.domain.FakeDomain.attach", broken)
    with pytest.raises(RuntimeError):
        running.storage.attach()
    assert not (running._session.images_dir / "vm1-vdb.qcow2").exists()


def test_detach_guards(running):
    with pytest.raises(ConfigurationError, match="no disk"):
        running.storage.detach("vdz")
    with pytest.raises(ConfigurationError, match="boot disk"):
        running.storage.detach("vda")


def test_stats(running):
    stats = running.storage.stats()
    assert stats["vda"].total_bytes == 1536
    assert stats["vda"].errors == 0


def test_hotplug_capability(running, monkeypatch):
    caps = type(running.driver.capabilities)(disk_hotplug=False)
    monkeypatch.setattr(type(running.driver), "capabilities", caps)
    with pytest.raises(UnsupportedOperationError):
        running.storage.attach()


@pytest.mark.parametrize("size", [0, -1, "-10G"])
def test_negative_disk_size_is_refused(running, size):
    with pytest.raises(ConfigurationError):
        running.storage.attach(size=size)
    assert set(running.storage.disks()) == {"vda"}
