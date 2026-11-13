"""Local audio-separation backend registry."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from oneclick_cover.separation import separate_vocals
from oneclick_cover.audio_separator_backend import AudioSeparatorBackend

ProgressCallback = Callable[[float, str], None]


class SeparationBackend(Protocol):
    """Contract shared by local vocal-separation engines."""

    name: str

    def separate(
        self,
        input_wav: Path,
        job_dir: Path,
        progress: ProgressCallback | None = None,
        *,
        device: str = "cpu",
        segment: float = 5,
        timeout: float = 1800,
    ) -> tuple[Path, Path]:
        """Return vocal and instrumental WAV paths."""


@dataclass(frozen=True)
class DemucsBackend:
    """Existing low-memory Demucs implementation."""

    name: str = "demucs"

    def separate(
        self,
        input_wav: Path,
        job_dir: Path,
        progress: ProgressCallback | None = None,
        *,
        device: str = "cpu",
        segment: float = 5,
        timeout: float = 1800,
    ) -> tuple[Path, Path]:
        return separate_vocals(
            input_wav,
            job_dir,
            progress=progress,
            device=device,
            segment=int(segment),
            timeout=timeout,
        )


_BACKENDS: dict[str, SeparationBackend] = {
    "demucs": DemucsBackend(),
    "audio-separator": AudioSeparatorBackend(),
}


def get_separation_backend(name: str) -> SeparationBackend:
    """Return a supported backend without downloading or importing model code."""
    normalized = str(name).strip().lower()
    if not normalized:
        raise ValueError("Choose an audio-separation backend.")
    try:
        return _BACKENDS[normalized]
    except KeyError as exc:
        available = ", ".join(sorted(_BACKENDS))
        raise ValueError(
            f"Unsupported separation backend '{normalized}'. "
            f"Available backends: {available}."
        ) from exc
