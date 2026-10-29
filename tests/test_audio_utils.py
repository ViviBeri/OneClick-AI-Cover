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

    output = tmp_path / "mix.wav"
    try:
        audio_utils.mix_audio(vocal, instrumental, output)
    except RuntimeError as exc:
        assert "Sample-rate mismatch" in str(exc)
    else:
        raise AssertionError("Expected sample-rate mismatch to fail clearly")

    assert not output.exists(), "A rejected mix must not leave a misleading output file"


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


def test_transcode_fallback_gives_helpful_error_for_undecodable_input(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: None)
    source = tmp_path / "corrupt.wav"
    source.write_bytes(b"this is not a valid audio file")
    destination = tmp_path / "nested" / "output.wav"

    try:
        audio_utils.transcode_to_wav(source, destination)
    except RuntimeError as exc:
        assert "Could not decode this file" in str(exc)
        assert "re-run install.bat" in str(exc).lower()
        assert exc.__cause__ is not None
    else:
        raise AssertionError("Expected undecodable input to produce a helpful error")

    assert not destination.exists()


def test_mix_audio_rejects_empty_vocal_or_instrumental(tmp_path):
    import pytest

    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    sf.write(vocal, [], 22050)
    sf.write(instrumental, [0.1, -0.1], 22050)

    with pytest.raises(RuntimeError, match="Audio file contains no samples"):
        audio_utils.mix_audio(vocal, instrumental, tmp_path / "mix.wav")

    sf.write(vocal, [0.1, -0.1], 22050)
    sf.write(instrumental, [], 22050)

    with pytest.raises(RuntimeError, match="Audio file contains no samples"):
        audio_utils.mix_audio(vocal, instrumental, tmp_path / "mix.wav")


def test_mix_audio_pads_shorter_track_and_applies_gains(tmp_path):
    import numpy as np

    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    output = tmp_path / "mix.wav"
    sr = 22050
    sf.write(vocal, [0.2, 0.4, 0.6], sr, subtype="FLOAT")
    sf.write(instrumental, [0.1], sr, subtype="FLOAT")

    audio_utils.mix_audio(
        vocal,
        instrumental,
        output,
        vocal_gain=0.5,
        instrumental_gain=0.25,
    )

    mixed, out_sr = sf.read(output, dtype="float32")
    expected = np.array([0.125, 0.2, 0.3], dtype="float32")
    assert out_sr == sr
    assert mixed.shape == (3, 2)
    assert np.allclose(mixed[:, 0], expected, atol=1 / 32768)
    assert np.allclose(mixed[:, 1], expected, atol=1 / 32768)

def test_transcode_removes_stale_output_before_failed_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(
        audio_utils,
        "_run",
        lambda command: (_ for _ in ()).throw(RuntimeError("synthetic ffmpeg failure")),
    )
    destination = tmp_path / "output.wav"
    destination.write_bytes(b"stale audio from previous run")

    try:
        audio_utils.transcode_to_wav(tmp_path / "input.mp3", destination)
    except RuntimeError as exc:
        assert "synthetic ffmpeg failure" in str(exc)
    else:
        raise AssertionError("Expected FFmpeg failure to propagate")

    assert not destination.exists()


def test_mp3_export_removes_stale_output_before_failed_ffmpeg(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")
    monkeypatch.setattr(
        audio_utils,
        "_run",
        lambda command: (_ for _ in ()).throw(RuntimeError("synthetic ffmpeg failure")),
    )
    destination = tmp_path / "output.mp3"
    destination.write_bytes(b"stale MP3 from previous run")

    try:
        audio_utils.export_mp3(tmp_path / "input.wav", destination)
    except RuntimeError as exc:
        assert "synthetic ffmpeg failure" in str(exc)
    else:
        raise AssertionError("Expected FFmpeg failure to propagate")

    assert not destination.exists()

def test_resample_removes_stale_destination_before_failed_ffmpeg(monkeypatch, tmp_path):
    import pytest

    source = tmp_path / "converted.wav"
    reference = tmp_path / "instrumental.wav"
    destination = tmp_path / "matched.wav"
    sf.write(source, [0.1, -0.1, 0.2], 48000)
    sf.write(reference, [0.1, -0.1, 0.2], 44100)
    destination.write_bytes(b"stale resampled audio")

    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: "managed-ffmpeg.exe")

    def fail_ffmpeg(command):
        raise RuntimeError("synthetic resampling failure")

    monkeypatch.setattr(audio_utils, "_run", fail_ffmpeg)

    with pytest.raises(RuntimeError, match="synthetic resampling failure"):
        audio_utils.match_sample_rate(source, reference, destination)

    assert not destination.exists()

def test_resample_removes_stale_destination_when_ffmpeg_unavailable(monkeypatch, tmp_path):
    import pytest

    source = tmp_path / "converted.wav"
    reference = tmp_path / "instrumental.wav"
    destination = tmp_path / "matched.wav"
    sf.write(source, [0.1, -0.1, 0.2], 48000)
    sf.write(reference, [0.1, -0.1, 0.2], 44100)
    destination.write_bytes(b"stale resampled audio")
    monkeypatch.setattr(audio_utils, "_ffmpeg_path", lambda: None)

    with pytest.raises(RuntimeError, match="FFmpeg is needed to resample"):
        audio_utils.match_sample_rate(source, reference, destination)

    assert not destination.exists()



def test_mix_audio_removes_stale_output_when_sample_rates_mismatch(tmp_path):
    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    output = tmp_path / "mix.wav"
    sf.write(vocal, [0.1, -0.1], 22050)
    sf.write(instrumental, [0.1, -0.1], 44100)
    output.write_bytes(b"stale mix")

    try:
        audio_utils.mix_audio(vocal, instrumental, output)
    except RuntimeError as exc:
        assert "Sample-rate mismatch" in str(exc)
    else:
        raise AssertionError("Expected sample-rate mismatch to fail clearly")

    assert not output.exists(), "A failed mix must remove any previous output"


def test_mix_audio_removes_stale_output_when_input_is_empty(tmp_path):
    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    output = tmp_path / "mix.wav"
    sf.write(vocal, [], 22050)
    sf.write(instrumental, [0.1, -0.1], 22050)
    output.write_bytes(b"stale mix")

    try:
        audio_utils.mix_audio(vocal, instrumental, output)
    except RuntimeError as exc:
        assert "Audio file contains no samples" in str(exc)
    else:
        raise AssertionError("Expected empty input to fail clearly")

    assert not output.exists(), "A failed mix must remove any previous output"


def test_read_stereo_rejects_non_finite_audio_samples(tmp_path):
    import numpy as np
    import pytest

    source = tmp_path / "invalid.wav"
    sf.write(source, np.array([0.1, np.nan, 0.2], dtype=np.float32), 22050, subtype="FLOAT")

    with pytest.raises(RuntimeError, match="invalid non-finite samples"):
        audio_utils._read_stereo(source)


def test_mix_audio_rejects_negative_gain_and_clears_stale_output(tmp_path):
    import pytest

    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    output = tmp_path / "mix.wav"
    sf.write(vocal, [0.1, -0.1], 22050)
    sf.write(instrumental, [0.1, -0.1], 22050)
    output.write_bytes(b"stale mix")

    with pytest.raises(ValueError, match="cannot be negative"):
        audio_utils.mix_audio(vocal, instrumental, output, vocal_gain=-1.0)

    assert not output.exists()


def test_mix_audio_rejects_non_finite_gain_and_clears_stale_output(tmp_path):
    import math
    import pytest

    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    output = tmp_path / "mix.wav"
    sf.write(vocal, [0.1, -0.1], 22050)
    sf.write(instrumental, [0.1, -0.1], 22050)
    output.write_bytes(b"stale mix")

    with pytest.raises(ValueError, match="finite numbers"):
        audio_utils.mix_audio(vocal, instrumental, output, instrumental_gain=math.nan)

    assert not output.exists()
