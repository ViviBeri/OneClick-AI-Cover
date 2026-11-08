"""Sanity checks for a finished cover in the opt-in conversion smoke test."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def verify_cover_audio(path: Path, expected_duration: float, tolerance: float = 0.05) -> dict:
    """Reject missing, unreadable, silent, non-finite, or incorrectly sized output."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Cover file is missing or empty: {path}")
    try:
        audio, rate = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception as exc:
        raise RuntimeError(f"Cover is not a readable audio file: {exc}") from exc
    if audio.shape[0] == 0:
        raise RuntimeError("Cover contains no samples.")
    if not np.isfinite(audio).all():
        raise RuntimeError("Cover contains non-finite samples.")
    duration = audio.shape[0] / rate
    if expected_duration > 0 and abs(duration - expected_duration) > expected_duration * tolerance:
        raise RuntimeError(
            f"Cover is {duration:.2f}s but the input clip is {expected_duration:.2f}s "
            f"(allowed difference {tolerance:.0%})."
        )
    rms = float(np.sqrt(np.mean(np.square(audio))))
    if rms < 1e-3:
        raise RuntimeError(f"Cover is effectively silent (RMS {rms:.6f}).")
    return {
        "duration_seconds": round(duration, 3),
        "sample_rate": int(rate),
        "channels": int(audio.shape[1]),
        "rms": round(rms, 5),
        "peak": round(float(np.max(np.abs(audio))), 5),
    }
