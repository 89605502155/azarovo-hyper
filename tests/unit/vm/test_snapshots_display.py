import pytest

from azarovo_hyper import ConfigurationError, DomainNotFoundError, UnsupportedOperationError


def test_snapshots(running):
    name = running.snapshots.create()
    assert name.startswith("snap-")
    running.snapshots.create("clean", description="before test")
    assert "clean" in running.snapshots
    assert len(running.snapshots) == 2
    assert sorted(running.snapshots) == sorted([name, "clean"])
    with pytest.raises(ConfigurationError, match="already exists"):
        running.snapshots.create("clean")
    running.snapshots.revert("clean")
    running.snapshots.delete("clean")
    with pytest.raises(DomainNotFoundError):
        running.snapshots.revert("clean")


def test_xen_has_no_snapshots_or_screenshots(hv, tmp_path):
    xen = hv.xen("xs", uri="fake:///xen", images_dir=tmp_path).start()
    with pytest.raises(UnsupportedOperationError):
        xen.snapshots.create()
    with pytest.raises(UnsupportedOperationError):
        xen.display.screenshot()


def test_screenshot(running, tmp_path):
    data = running.display.screenshot(tmp_path / "shots" / "screen")
    assert data.startswith(b"\x89PNG")
    assert (tmp_path / "shots" / "screen.png").read_bytes() == data
    running.display.screenshot(tmp_path / "keep.bin")
    assert (tmp_path / "keep.bin").exists()


def test_display_uri(running, fake):
    assert running.display.uri is None
    graphics = fake.domains(running.uri)[running.name].tree.find("./devices/graphics")
    graphics.set("port", "5905")
    assert running.display.uri == "spice://127.0.0.1:5905"


def test_viewer_lifecycle(running, monkeypatch, tmp_path):
    script = tmp_path / "viewer"
    script.write_text("#!/bin/sh\nsleep 30\n")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{tmp_path}:/usr/bin:/bin")
    process = running.display.open_viewer(binary="viewer")
    assert process.poll() is None
    running.stop()
    assert process.poll() is not None
    running.start()
    second = running.display.open_viewer(binary="viewer")
    running.display.close_viewers()
    assert second.poll() is not None
    with pytest.raises(UnsupportedOperationError):
        running.display.open_viewer(binary="definitely-missing-viewer")
