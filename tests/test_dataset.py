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



def test_reusing_dataset_name_removes_stale_generated_recordings(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from oneclick_cover import dataset

    source = tmp_path / "voice.wav"
    source.write_bytes(b"input")
    target = tmp_path / "datasets" / "MyVoice"
    target.mkdir(parents=True)
    stale = target / "recording_009.wav"
    stale.write_bytes(b"stale")
    user_file = target / "notes.txt"
    user_file.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(dataset, "_ffmpeg_path", lambda: "/tools/ffmpeg.exe")

    def fake_run(command, **kwargs):
        Path(command[-1]).write_bytes(b"converted wav")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(dataset.subprocess, "run", fake_run)
    result_dir, count = prepare_recordings([source], "MyVoice", tmp_path / "datasets")

    assert result_dir == target
    assert count == 1
    assert sorted(p.name for p in target.glob("recording_*.wav")) == ["recording_001.wav"]
    assert user_file.read_text(encoding="utf-8") == "keep"


def test_failed_replacement_preserves_existing_dataset(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from oneclick_cover import dataset

    source = tmp_path / "new_voice.wav"
    source.write_bytes(b"input")
    target = tmp_path / "datasets" / "MyVoice"
    target.mkdir(parents=True)
    previous = target / "recording_001.wav"
    previous.write_bytes(b"previous good recording")
    notes = target / "notes.txt"
    notes.write_text("keep", encoding="utf-8")

    monkeypatch.setattr(dataset, "_ffmpeg_path", lambda: "/tools/ffmpeg.exe")
    monkeypatch.setattr(
        dataset.subprocess,
        "run",
        lambda command, **kwargs: SimpleNamespace(
            returncode=1, stderr="fixture conversion failed", stdout=""
        ),
    )

    with pytest.raises(RuntimeError, match="fixture conversion failed"):
        prepare_recordings([source], "MyVoice", tmp_path / "datasets")

    assert previous.read_bytes() == b"previous good recording"
    assert notes.read_text(encoding="utf-8") == "keep"
    assert not list(target.glob(".preparing-*"))


def test_preparation_rejects_unsupported_recording_before_conversion(monkeypatch, tmp_path):
    from oneclick_cover import dataset

    source = tmp_path / "voice.txt"
    source.write_text("not audio", encoding="utf-8")
    monkeypatch.setattr(dataset, "_ffmpeg_path", lambda: "/tools/ffmpeg.exe")
    monkeypatch.setattr(dataset.subprocess, "run", lambda *args, **kwargs: pytest.fail("conversion must not run"))

    with pytest.raises(ValueError, match="Unsupported recording format"):
        prepare_recordings([source], "MyVoice", tmp_path / "datasets")


def test_preparation_rejects_empty_recording_before_conversion(monkeypatch, tmp_path):
    from oneclick_cover import dataset

    source = tmp_path / "voice.wav"
    source.touch()
    monkeypatch.setattr(dataset, "_ffmpeg_path", lambda: "/tools/ffmpeg.exe")
    monkeypatch.setattr(dataset.subprocess, "run", lambda *args, **kwargs: pytest.fail("conversion must not run"))

    with pytest.raises(ValueError, match="Recording is empty"):
        prepare_recordings([source], "MyVoice", tmp_path / "datasets")


def test_preparation_rejects_success_without_nonempty_output(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from oneclick_cover import dataset

    source = tmp_path / "voice.wav"
    source.write_bytes(b"input")
    target = tmp_path / "datasets" / "MyVoice"
    target.mkdir(parents=True)
    previous = target / "recording_001.wav"
    previous.write_bytes(b"previous good recording")

    monkeypatch.setattr(dataset, "_ffmpeg_path", lambda: "/tools/ffmpeg.exe")
    monkeypatch.setattr(
        dataset.subprocess,
        "run",
        lambda command, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    with pytest.raises(RuntimeError, match="Could not convert voice.wav"):
        prepare_recordings([source], "MyVoice", tmp_path / "datasets")

    assert previous.read_bytes() == b"previous good recording"
    assert not list(target.glob(".preparing-*"))
