import shutil

import pytest

from azarovo_hyper import DiskError, QemuImg

needs_qemu_img = pytest.mark.skipif(shutil.which("qemu-img") is None, reason="no qemu-img")


@needs_qemu_img
def test_create_keep_and_remove(tmp_path):
    tool = QemuImg()
    path = tmp_path / "sub" / "a.qcow2"
    assert tool.create(path, 16)
    assert path.read_bytes()[:4] == b"QFI\xfb"
    assert not tool.create(path, 16)
    assert tool.remove(path)
    assert not tool.remove(path)


@needs_qemu_img
def test_bad_format(tmp_path):
    with pytest.raises(DiskError, match="qemu-img failed"):
        QemuImg().create(tmp_path / "a.img", 16, fmt="nonsense")


def test_missing_binary(tmp_path):
    with pytest.raises(DiskError, match="not found"):
        QemuImg(binary="no-such-qemu-img").create(tmp_path / "a.qcow2", 1)


def test_remove_error(tmp_path):
    folder = tmp_path / "dir.qcow2"
    folder.mkdir()
    with pytest.raises(DiskError):
        QemuImg().remove(folder)


@needs_qemu_img
def test_falloc_reserves_blocks_now(tmp_path):
    path = tmp_path / "full.qcow2"
    QemuImg().create(path, 64, preallocation="falloc")
    assert path.stat().st_blocks * 512 >= 64 * 1024 * 1024
    thin = tmp_path / "thin.qcow2"
    QemuImg().create(thin, 64)
    assert thin.stat().st_blocks * 512 < 8 * 1024 * 1024


def test_full_disk_is_reported_as_insufficient_resources(tmp_path):
    from azarovo_hyper import InsufficientResourcesError

    script = tmp_path / "qemu-img"
    script.write_text("#!/bin/sh\ntouch \"$7\"\necho 'No space left on device' >&2\nexit 1\n")
    script.chmod(0o755)
    target = tmp_path / "a.qcow2"
    with pytest.raises(InsufficientResourcesError):
        QemuImg(binary=str(script)).create(target, 1024, preallocation="falloc")
    assert not target.exists()
