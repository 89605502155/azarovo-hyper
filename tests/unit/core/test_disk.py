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
