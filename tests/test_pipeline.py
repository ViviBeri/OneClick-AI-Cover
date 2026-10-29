from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

import app


def _prepare_fake_pipeline(monkeypatch, tmp_path):
    output_dir = tmp_path / "outputs"
    voice_dir = tmp_path / "voices"
    output_dir.mkdir()
    voice_dir.mkdir()
    source = tmp_path / "input.wav"
    source.write_bytes(b"fixture input")
    model = voice_dir / "test-model.pth"
    model.write_bytes(b"x" * 2048)

    monkeypatch.setattr(app, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(app, "VOICE_DIR", voice_dir)
    monkeypatch.setattr(app, "validate_audio_file", lambda path: None)
    monkeypatch.setattr(app, "validate_voice_model", lambda path: None)

    def write_audio(path, rate=44100, channels=2):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        audio = np.full((rate // 2, channels), 0.05, dtype=np.float32)
        sf.write(str(path), audio, rate)
        return path

    def fake_transcode(source_path, destination):
        write_audio(destination)
    
    def fake_separate(input_wav, job_dir):
        return write_audio(job_dir / "vocals.wav"), write_audio(job_dir / "instrumental.wav")

    def fake_convert(input_vocal, output_vocal, model_path, pitch=0):
        write_audio(output_vocal)

    monkeypatch.setattr(app, "transcode_to_wav", fake_transcode)
    monkeypatch.setattr(app, "separate_vocals", fake_separate)
    monkeypatch.setattr(app, "convert_voice", fake_convert)
    return source, model


def test_generate_runs_pipeline_and_produces_readable_wav(monkeypatch, tmp_path):
    source, model = _prepare_fake_pipeline(monkeypatch, tmp_path)

    output, status = app.generate(
        str(source), model.name, 0, 1.0, 0.85, "WAV"
    )

    output_path = Path(output)
    assert output_path.is_file() and output_path.stat().st_size > 0
    audio, sample_rate = sf.read(str(output_path), dtype="float32", always_2d=True)
    assert sample_rate == 44100
    assert audio.shape == (22050, 2)
    assert "Saved:" in status


def test_generate_exports_mp3_when_requested(monkeypatch, tmp_path):
    from oneclick_cover.audio_utils import _ffmpeg_path

    if not _ffmpeg_path():
        pytest.skip("FFmpeg not available")

    source, model = _prepare_fake_pipeline(monkeypatch, tmp_path)

    output, status = app.generate(
        str(source), model.name, 0, 1.0, 0.85, "MP3"
    )

    output_path = Path(output)
    assert output_path.suffix.lower() == ".mp3"
    assert output_path.is_file() and output_path.stat().st_size > 0
    assert "Saved:" in status


def test_generate_resamples_48k_rvc_output_before_mixing(monkeypatch, tmp_path):
    from oneclick_cover.audio_utils import _ffmpeg_path

    if not _ffmpeg_path():
        pytest.skip("FFmpeg not available")

    source, model = _prepare_fake_pipeline(monkeypatch, tmp_path)

    def fake_convert_48k(input_vocal, output_vocal, model_path, pitch=0):
        output_vocal = Path(output_vocal)
        output_vocal.parent.mkdir(parents=True, exist_ok=True)
        sf.write(
            str(output_vocal),
            np.full((24000, 2), 0.05, dtype=np.float32),
            48000,
        )

    monkeypatch.setattr(app, "convert_voice", fake_convert_48k)

    output, status = app.generate(
        str(source), model.name, 0, 1.0, 0.85, "WAV"
    )

    audio, sample_rate = sf.read(output, dtype="float32", always_2d=True)
    assert sample_rate == 44100
    assert audio.shape == (22050, 2)
    assert "Saved:" in status

def test_generate_reports_rvc_failure_without_claiming_success(monkeypatch, tmp_path):
    import gradio as gr

    source, model = _prepare_fake_pipeline(monkeypatch, tmp_path)

    def fail_conversion(input_vocal, output_vocal, model_path, pitch=0):
        raise RuntimeError("RVC inference failed: test failure")

    monkeypatch.setattr(app, "convert_voice", fail_conversion)

    with pytest.raises(gr.Error, match="RVC inference failed: test failure"):
        app.generate(str(source), model.name, 0, 1.0, 0.85, "WAV")

    # A failed conversion must not leave a plausible finished cover behind.
    assert not list(Path(app.OUTPUT_DIR).glob("cover_*/cover.wav"))
