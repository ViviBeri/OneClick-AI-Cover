import numpy as np
import soundfile as sf
from oneclick_cover.audio_utils import mix_audio

def test_mix_writes_audio_and_prevents_clipping(tmp_path):
    vocal = tmp_path / "vocal.wav"
    instrumental = tmp_path / "instrumental.wav"
    output = tmp_path / "mix.wav"
    sr = 22050
    samples = np.full((sr, 2), 0.8, dtype=np.float32)
    sf.write(vocal, samples, sr)
    sf.write(instrumental, samples, sr)
    mix_audio(vocal, instrumental, output, vocal_gain=1.0, instrumental_gain=1.0)
    result, result_sr = sf.read(output, dtype="float32", always_2d=True)
    assert result_sr == sr
    assert result.shape == samples.shape
    assert np.max(np.abs(result)) <= 1.0


def test_match_sample_rate_returns_source_when_rates_equal(tmp_path):
    from oneclick_cover.audio_utils import match_sample_rate
    a, b = tmp_path / "a.wav", tmp_path / "b.wav"
    sf.write(a, np.zeros((4410, 2), dtype=np.float32), 44100)
    sf.write(b, np.zeros((4410, 2), dtype=np.float32), 44100)
    assert match_sample_rate(a, b, tmp_path / "out.wav") == a


def test_match_sample_rate_resamples_48k_vocal_to_44k_instrumental(tmp_path):
    import pytest
    from oneclick_cover.audio_utils import _ffmpeg_path, match_sample_rate
    if not _ffmpeg_path():
        pytest.skip("FFmpeg not available")
    vocal, inst, out = tmp_path / "v.wav", tmp_path / "i.wav", tmp_path / "v44.wav"
    sf.write(vocal, np.full((48000, 2), 0.1, dtype=np.float32), 48000)
    sf.write(inst, np.full((44100, 2), 0.1, dtype=np.float32), 44100)
    result = match_sample_rate(vocal, inst, out)
    assert result == out and sf.info(str(out)).samplerate == 44100
    mix_audio(result, inst, tmp_path / "mix.wav")  # previously raised a sample-rate mismatch

def test_mix_accepts_mono_converted_vocal_at_matching_sample_rate(tmp_path):
    vocal = tmp_path / "mono_vocal.wav"
    instrumental = tmp_path / "stereo_instrumental.wav"
    output = tmp_path / "mix.wav"
    sr = 44100
    sf.write(vocal, np.full(sr, 0.1, dtype=np.float32), sr)
    sf.write(instrumental, np.zeros((sr, 2), dtype=np.float32), sr)

    mix_audio(vocal, instrumental, output)

    result, result_sr = sf.read(output, dtype="float32", always_2d=True)
    assert result_sr == sr
    assert result.shape == (sr, 2)
    assert np.isfinite(result).all()
