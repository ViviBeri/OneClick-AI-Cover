from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from oneclick_cover.separation import separate_vocals


def main() -> int:
    sample_rate = 44_100
    duration_seconds = 4
    sample_count = sample_rate * duration_seconds
    time_axis = np.arange(sample_count, dtype=np.float32) / sample_rate

    # Deterministic synthetic audio avoids shipping copyrighted or personal recordings.
    left = (
        0.18 * np.sin(2 * np.pi * 220 * time_axis)
        + 0.08 * np.sin(2 * np.pi * 440 * time_axis)
        + 0.06 * np.sin(2 * np.pi * 110 * time_axis)
    )
    right = (
        0.16 * np.sin(2 * np.pi * 261.63 * time_axis)
        + 0.07 * np.sin(2 * np.pi * 523.25 * time_axis)
        + 0.05 * np.sin(2 * np.pi * 130.81 * time_axis)
    )
    audio = np.column_stack((left, right)).astype(np.float32)

    with tempfile.TemporaryDirectory(prefix="demucs-smoke-") as temporary:
        root = Path(temporary)
        source = root / "synthetic-input.wav"
        sf.write(source, audio, sample_rate, subtype="PCM_16")

        vocals, instrumental = separate_vocals(source, root / "job", shifts=0)
        for stem in (vocals, instrumental):
            if not stem.is_file() or stem.stat().st_size == 0:
                raise RuntimeError(f"Demucs did not create a non-empty stem: {stem}")
            info = sf.info(stem)
            if info.frames <= 0 or info.samplerate <= 0 or info.channels <= 0:
                raise RuntimeError(f"Demucs created invalid audio metadata: {stem}")
            samples, _ = sf.read(stem, dtype="float32", always_2d=True)
            if not np.isfinite(samples).all():
                raise RuntimeError(f"Demucs created non-finite audio samples: {stem}")
            print(
                f"DEMUCS STEM OK: {stem.name}; "
                f"duration={info.duration:.2f}s; "
                f"sample_rate={info.samplerate}; channels={info.channels}; "
                f"bytes={stem.stat().st_size}",
                flush=True,
            )

    print("REAL DEMUCS MODEL INFERENCE SMOKE TEST PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
