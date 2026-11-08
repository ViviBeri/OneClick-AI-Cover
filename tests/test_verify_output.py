import numpy as np
import pytest
import soundfile as sf

from oneclick_cover.verify_output import verify_cover_audio


def _tone(path, seconds=2.0, rate=44100, amplitude=0.2):
    t = np.linspace(0, seconds, int(rate * seconds), endpoint=False)
    wave = (amplitude * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
    sf.write(str(path), np.stack([wave, wave], axis=1), rate)
    return path


def test_accepts_audible_cover_of_expected_length(tmp_path):
    result = verify_cover_audio(_tone(tmp_path / "ok.wav"), expected_duration=2.0)
    assert result["sample_rate"] == 44100
    assert result["channels"] == 2
    assert result["rms"] > 0.1


def test_rejects_silence(tmp_path):
    with pytest.raises(RuntimeError, match="silent"):
        verify_cover_audio(_tone(tmp_path / "quiet.wav", amplitude=0.0), expected_duration=2.0)


def test_rejects_wrong_length(tmp_path):
    with pytest.raises(RuntimeError, match="input clip"):
        verify_cover_audio(_tone(tmp_path / "short.wav", seconds=1.0), expected_duration=2.0)


def test_rejects_missing_or_empty_file(tmp_path):
    with pytest.raises(RuntimeError, match="missing or empty"):
        verify_cover_audio(tmp_path / "nope.wav", expected_duration=2.0)


def test_rejects_non_finite_audio(tmp_path):
    path = tmp_path / "nan.wav"
    sf.write(path, np.full(4410, np.nan, dtype=np.float32), 44100, subtype="FLOAT")
    with pytest.raises(RuntimeError, match="non-finite"):
        verify_cover_audio(path, expected_duration=0.1)
