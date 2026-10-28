from pathlib import Path
import pytest
from oneclick_cover.dataset import safe_dataset_name, prepare_recordings


def test_dataset_name_removes_path_components():
    assert safe_dataset_name("../My Voice!") == "My_Voice"


def test_dataset_name_rejects_empty_name():
    with pytest.raises(ValueError, match="dataset name"):
        safe_dataset_name("!!!")


def test_preparation_requires_recordings(tmp_path):
    with pytest.raises(ValueError, match="Upload at least one"):
        prepare_recordings([], "MyVoice", tmp_path)


def test_preparation_rejects_missing_recording_before_conversion(monkeypatch, tmp_path):
    monkeypatch.setattr("oneclick_cover.dataset.shutil.which", lambda _: "ffmpeg")
    with pytest.raises(ValueError, match="Recording not found"):
        prepare_recordings([tmp_path / "missing.wav"], "MyVoice", tmp_path / "datasets")


def test_ffmpeg_path_uses_system_ffmpeg(monkeypatch):
    from oneclick_cover import dataset

    monkeypatch.setattr(dataset.shutil, "which", lambda name: "/tools/ffmpeg.exe" if name == "ffmpeg" else None)
    assert dataset._ffmpeg_path() == "/tools/ffmpeg.exe"


def test_preparation_reports_missing_ffmpeg(monkeypatch, tmp_path):
    from oneclick_cover import dataset

    monkeypatch.setattr(dataset, "_ffmpeg_path", lambda: None)
    with pytest.raises(RuntimeError, match="FFmpeg is unavailable"):
        prepare_recordings([tmp_path / "voice.wav"], "MyVoice", tmp_path / "datasets")


def test_ffmpeg_path_uses_bundled_helper(monkeypatch):
    import sys
    from types import SimpleNamespace
    from oneclick_cover import dataset

    monkeypatch.setattr(dataset.shutil, "which", lambda _: None)
    monkeypatch.setitem(sys.modules, "imageio_ffmpeg", SimpleNamespace(get_ffmpeg_exe=lambda: "/managed/ffmpeg.exe"))
    assert dataset._ffmpeg_path() == "/managed/ffmpeg.exe"
