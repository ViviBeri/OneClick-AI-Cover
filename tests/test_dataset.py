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
