from __future__ import annotations

import soundfile as sf
import torch

from oneclick_cover.demucs_audio import save_audio_without_torchcodec


def test_demucs_wav_writer_uses_soundfile_not_torchaudio(monkeypatch, tmp_path):
    import demucs.audio

    def fail_if_called(*args, **kwargs):
        raise AssertionError("torchaudio.save must not be used for Demucs stems")

    monkeypatch.setattr(demucs.audio.ta, "save", fail_if_called)
    destination = tmp_path / "vocals.wav"
    waveform = torch.tensor(
        [[-0.5, 0.0, 0.5], [0.25, -0.25, 0.0]],
        dtype=torch.float32,
    )

    save_audio_without_torchcodec(waveform, destination, 44100)

    audio, sample_rate = sf.read(destination, dtype="float32", always_2d=True)
    assert sample_rate == 44100
    assert audio.shape == (3, 2)
    assert audio.max() > 0.4
    assert audio.min() < -0.4


def test_demucs_wav_writer_supports_float_output(tmp_path):
    destination = tmp_path / "vocals-float.wav"
    waveform = torch.tensor([[0.125, -0.125]], dtype=torch.float32)

    save_audio_without_torchcodec(
        waveform,
        destination,
        48000,
        as_float=True,
    )

    audio, sample_rate = sf.read(destination, dtype="float32", always_2d=True)
    assert sample_rate == 48000
    assert audio.shape == (2, 1)
    assert audio.dtype.name == "float32"
