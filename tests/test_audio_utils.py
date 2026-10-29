from pathlib import Path

import soundfile as sf

from oneclick_cover import audio_utils


def test_transcode_uses_managed_ffmpeg_when_available(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(audio_utils, "_run", lambda command: (commands.append(command), Path(command[-1]).write_bytes(b"output"))[0])

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
    monkeypatch.setattr(audio_utils, "_run", lambda command: (commands.append(command), Path(command[-1]).write_bytes(b"output"))[0])

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



def test_transcode_creates_destination_directory_before_ffmpeg(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(audio_utils, "_run", lambda command: (commands.append(command), Path(command[-1]).write_bytes(b"output"))[0])

    source = tmp_path / "input.mp3"
    destination = tmp_path / "nested" / "folder" / "output.wav"
    audio_utils.transcode_to_wav(source, destination)

    assert destination.parent.is_dir()
    assert commands and commands[0][-1] == str(destination)


def test_export_mp3_creates_destination_directory(monkeypatch, tmp_path):
    commands = []
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(audio_utils, "_run", lambda command: (commands.append(command), Path(command[-1]).write_bytes(b"output"))[0])

    destination = tmp_path / "nested" / "output.mp3"
    audio_utils.export_mp3(tmp_path / "input.wav", destination)

    assert destination.parent.is_dir()
    assert commands and commands[0][-1] == str(destination)


def test_mix_audio_normalizes_peak_and_writes_pcm16(tmp_path):
    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    output = tmp_path / "nested" / "mix.wav"
    sr = 22050
    sf.write(vocal, [0.8, -0.8, 0.5], sr)
    sf.write(instrumental, [0.8, -0.8], sr)

    audio_utils.mix_audio(vocal, instrumental, output, vocal_gain=1.0, instrumental_gain=1.0)

    mixed, out_sr = sf.read(output, dtype="float32")
    assert out_sr == sr
    assert len(mixed) == 3
    assert float(abs(mixed).max()) <= 0.991
    assert sf.info(output).subtype == "PCM_16"


def test_mix_audio_rejects_sample_rate_mismatch(tmp_path):
    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    sf.write(vocal, [0.1, 0.2], 22050)
    sf.write(instrumental, [0.1, 0.2], 44100)

    try:
        audio_utils.mix_audio(vocal, instrumental, tmp_path / "mix.wav")
    except RuntimeError as exc:
        assert "Sample-rate mismatch" in str(exc)
    else:
        raise AssertionError("Expected sample-rate mismatch to fail clearly")


def test_transcode_fallback_reads_wav_without_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: None)
    source = tmp_path / "input.wav"
    destination = tmp_path / "nested" / "output.wav"
    sf.write(source, [0.1, -0.1, 0.2], 16000)

    audio_utils.transcode_to_wav(source, destination)

    converted, sr = sf.read(destination)
    assert sr == 16000
    assert len(converted) == 3


def test_run_reports_command_failure_details(monkeypatch):
    class Result:
        returncode = 1
        stderr = "synthetic ffmpeg failure"
        stdout = ""

    monkeypatch.setattr(audio_utils.subprocess, "run", lambda *args, **kwargs: Result())
    try:
        audio_utils._run(["ffmpeg", "-i", "input.mp3", "output.wav"])
    except RuntimeError as exc:
        assert "Command failed (1)" in str(exc)
        assert "synthetic ffmpeg failure" in str(exc)
    else:
        raise AssertionError("Expected command failure to raise RuntimeError")



def test_transcode_rejects_success_without_output(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(audio_utils, "_run", lambda command: None)

    destination = tmp_path / "output.wav"
    try:
        audio_utils.transcode_to_wav(tmp_path / "input.mp3", destination)
    except RuntimeError as exc:
        assert "without creating a non-empty output file" in str(exc)
    else:
        raise AssertionError("Expected conversion to reject a missing output")


def test_mp3_export_rejects_empty_output(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(audio_utils, "_run", lambda command: Path(command[-1]).touch())

    destination = tmp_path / "output.mp3"
    try:
        audio_utils.export_mp3(tmp_path / "input.wav", destination)
    except RuntimeError as exc:
        assert "without creating a non-empty output file" in str(exc)
    else:
        raise AssertionError("Expected MP3 export to reject an empty output")


def test_mix_audio_rejects_missing_output_after_write(tmp_path, monkeypatch):
    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    sf.write(vocal, [0.1, -0.1], 22050)
    sf.write(instrumental, [0.1, -0.1], 22050)
    monkeypatch.setattr(audio_utils.sf, "write", lambda *args, **kwargs: None)

    try:
        audio_utils.mix_audio(vocal, instrumental, tmp_path / "mix.wav")
    except RuntimeError as exc:
        assert "Audio mix completed without creating a non-empty output file" in str(exc)
    else:
        raise AssertionError("Expected mixing to reject a missing output")
