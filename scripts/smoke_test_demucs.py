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

        def report_progress(fraction: float, message: str) -> None:
            if message:
                print(f"DEMUCS: {fraction:.0%} {message}", flush=True)

        vocals, instrumental = separate_vocals(
            source, root / "job", progress=report_progress, shifts=0
        )
        original, original_rate = sf.read(source, dtype="float32", always_2d=True)
        if original_rate != sample_rate:
            raise RuntimeError(
                f"Unexpected input sample rate: {original_rate}; expected {sample_rate}"
            )

        stem_audio = []
        stem_rms = []
        for stem in (vocals, instrumental):
            if not stem.is_file() or stem.stat().st_size == 0:
                raise RuntimeError(f"Demucs did not create a non-empty stem: {stem}")
            info = sf.info(stem)
            if info.frames <= 0 or info.samplerate != sample_rate or info.channels != 2:
                raise RuntimeError(f"Demucs created invalid audio metadata: {stem}")
            if abs(info.duration - duration_seconds) > 0.1:
                raise RuntimeError(
                    f"Demucs stem duration is unexpected: {stem}; "
                    f"expected about {duration_seconds}s, got {info.duration:.2f}s"
                )
            samples, stem_rate = sf.read(stem, dtype="float32", always_2d=True)
            if stem_rate != original_rate or samples.shape != original.shape:
                raise RuntimeError(
                    f"Demucs stem shape/rate does not match input: {stem}; "
                    f"stem={samples.shape}@{stem_rate}, input={original.shape}@{original_rate}"
                )
            if not np.isfinite(samples).all():
                raise RuntimeError(f"Demucs created non-finite audio samples: {stem}")
            rms = float(np.sqrt(np.mean(np.square(samples))))
            peak = float(np.max(np.abs(samples)))
            stem_audio.append(samples)
            stem_rms.append(rms)
            print(
                f"DEMUCS STEM: {stem.name}; "
                f"duration={info.duration:.2f}s; "
                f"sample_rate={info.samplerate}; channels={info.channels}; "
                f"RMS={rms:.6f}; peak={peak:.6f}; bytes={stem.stat().st_size}",
                flush=True,
            )

        # Either stem may legitimately be near-silent for simple input. The
        # pair must retain energy and reconstruct the original mixture.
        if max(stem_rms) <= 1e-5:
            raise RuntimeError(f"Both Demucs stems are silent or near-silent: RMS={stem_rms}")
        reconstructed = stem_audio[0] + stem_audio[1]
        input_rms = float(np.sqrt(np.mean(np.square(original))))
        residual_rms = float(np.sqrt(np.mean(np.square(reconstructed - original))))
        relative_error = residual_rms / max(input_rms, 1e-8)
        print(
            f"DEMUCS RECONSTRUCTION: input_RMS={input_rms:.6f}; "
            f"residual_RMS={residual_rms:.8f}; relative_error={relative_error:.6%}",
            flush=True,
        )
        if relative_error > 0.02:
            raise RuntimeError(
                "Demucs stems do not reconstruct the input mixture within tolerance: "
                f"relative error {relative_error:.6%} > 2%"
            )

    print("REAL DEMUCS MODEL INFERENCE SMOKE TEST PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
