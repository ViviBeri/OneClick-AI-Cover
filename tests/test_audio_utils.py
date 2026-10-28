from pathlib import Path

from oneclick_cover import audio_utils


def test_transcode_uses_managed_ffmpeg_when_available(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(audio_utils, "_run", lambda command: commands.append(command))

    source = tmp_path / "input.mp3"
    destination = tmp_path / "output.wav"
    audio_utils.transcode_to_wav(source, destination)

    assert commands == [[
        "managed-ffmpeg.exe", "-y", "-i", str(source), "-vn",
        "-ac", "2", "-ar", "44100", str(destination)
    ]]


def test_mp3_export_uses_managed_ffmpeg(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(audio_utils, "_run", lambda command: commands.append(command))

    source = tmp_path / "input.wav"
    destination = tmp_path / "output.mp3"
    audio_utils.export_mp3(source, destination)

    assert commands == [[
        "managed-ffmpeg.exe", "-y", "-i", str(source),
        "-codec:a", "libmp3lame", "-q:a", "2", str(destination)
    ]]


def test_mp3_export_explains_missing_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: None)

    try:
        audio_utils.export_mp3(tmp_path / "input.wav", tmp_path / "output.mp3")
    except RuntimeError as exc:
        assert "managed FFmpeg helper" in str(exc)
    else:
        raise AssertionError("Expected a helpful error when FFmpeg is unavailable")
