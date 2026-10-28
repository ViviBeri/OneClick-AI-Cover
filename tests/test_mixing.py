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
