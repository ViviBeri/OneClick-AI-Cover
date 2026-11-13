"""UI-independent orchestration for a local AI cover job."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Callable

from oneclick_cover.audio_utils import export_mp3, match_sample_rate, mix_audio, transcode_to_wav
from oneclick_cover.conversion import convert_voice
from oneclick_cover.separation_backends import get_separation_backend
from oneclick_cover.validation import validate_audio_file, validate_voice_model

ProgressCallback = Callable[[float, str], None]


def run_cover_pipeline(
    song: str | Path,
    model_path: str | Path,
    pitch: int,
    vocal_gain: float,
    instrumental_gain: float,
    output_format: str,
    output_dir: str | Path,
    *,
    demucs_device: str = "cpu",
    demucs_segment: float = 5.0,
    demucs_timeout: float = 1800,
    separation_backend: str = "demucs",
    progress: ProgressCallback | None = None,
    transcode_fn=transcode_to_wav,
    separate_fn=None,
    convert_fn=convert_voice,
    match_sample_rate_fn=match_sample_rate,
    mix_fn=mix_audio,
    export_mp3_fn=export_mp3,
    validate_audio_fn=validate_audio_file,
    validate_model_fn=validate_voice_model,
) -> Path:
    """Run the complete local pipeline without depending on Gradio or UI state."""
    source = Path(song)
    voice_model = Path(model_path)
    destination_root = Path(output_dir)
    job_dir: Path | None = None

    def report(fraction: float, message: str) -> None:
        if progress is not None:
            progress(min(1.0, max(0.0, float(fraction))), message)

    try:
        validate_audio_fn(source)
        validate_model_fn(voice_model)
        job_dir = Path(tempfile.mkdtemp(prefix="cover_", dir=destination_root))
        wav = job_dir / "input.wav"

        report(0.1, "Preparing audio")
        transcode_fn(source, wav)

        report(0.25, f"Separating vocals ({separation_backend})")

        def separation_progress(fraction: float, message: str) -> None:
            report(0.25 + 0.35 * fraction, message or "Separating vocals")

        backend = get_separation_backend(separation_backend)
        separator = separate_fn or backend.separate
        vocals, instrumental = separator(
            wav,
            job_dir,
            progress=separation_progress,
            device=demucs_device,
            segment=float(demucs_segment),
            timeout=float(demucs_timeout),
        )

        report(0.6, "Converting voice")
        converted = job_dir / "converted.wav"
        convert_fn(vocals, converted, voice_model, int(pitch))

        report(0.85, "Mixing")
        output = job_dir / "cover.wav"
        converted = match_sample_rate_fn(
            converted, instrumental, job_dir / "converted_matched.wav"
        )
        mix_fn(converted, instrumental, output, float(vocal_gain), float(instrumental_gain))

        if output_format == "MP3":
            mp3 = job_dir / "cover.mp3"
            export_mp3_fn(output, mp3)
            output = mp3
        elif output_format != "WAV":
            raise ValueError("Output format must be WAV or MP3.")

        if not output.is_file() or output.stat().st_size == 0:
            raise RuntimeError("The cover pipeline completed without a usable output file.")

        report(1.0, "Done")
        return output
    except Exception:
        if job_dir is not None:
            shutil.rmtree(job_dir, ignore_errors=True)
        raise
