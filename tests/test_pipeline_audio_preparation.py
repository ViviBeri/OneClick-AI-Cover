from pathlib import Path

import numpy as np
import soundfile as sf

from oneclick_cover.pipeline import prepare_demucs_input


def _write_wav(path: Path, *, sample_rate: int, channels: int) -> Path:
    audio = np.zeros((sample_rate // 2, channels), dtype=np.float32)
    sf.write(str(path), audio, sample_rate, subtype="PCM_16")
    return path


def test_reuses_stereo_44100_wav_without_transcoding(tmp_path):
    source = _write_wav(tmp_path / "source.wav", sample_rate=44100, channels=2)
    destination = tmp_path / "workspace" / "input.wav"

    def unexpected_transcode(*args):
        raise AssertionError("Compatible WAV input must not be transcoded")

    result = prepare_demucs_input(source, destination, unexpected_transcode)

    assert result == source
    assert not destination.exists()


def test_transcodes_mono_wav_to_preserve_demucs_input_contract(tmp_path):
    source = _write_wav(tmp_path / "mono.wav", sample_rate=44100, channels=1)
    destination = tmp_path / "workspace" / "input.wav"
    calls = []

    def fake_transcode(input_path, output_path):
        calls.append((input_path, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"converted")

    result = prepare_demucs_input(source, destination, fake_transcode)

    assert result == destination
    assert calls == [(source, destination)]
    assert destination.read_bytes() == b"converted"


def test_transcodes_stereo_wav_with_noncanonical_sample_rate(tmp_path):
    source = _write_wav(tmp_path / "48k.wav", sample_rate=48000, channels=2)
    destination = tmp_path / "workspace" / "input.wav"
    calls = []

    def fake_transcode(input_path, output_path):
        calls.append(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"converted")

    result = prepare_demucs_input(source, destination, fake_transcode)

    assert result == destination
    assert calls == [source]


def test_transcodes_non_wav_input_even_when_audio_layout_matches(tmp_path):
    source = tmp_path / "song.flac"
    source.write_bytes(b"not decoded by the preparation helper")
    destination = tmp_path / "workspace" / "input.wav"
    calls = []

    def fake_transcode(input_path, output_path):
        calls.append(input_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"converted")

    result = prepare_demucs_input(source, destination, fake_transcode)

    assert result == destination
    assert calls == [source]
