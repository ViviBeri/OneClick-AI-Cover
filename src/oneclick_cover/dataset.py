from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

SUPPORTED_AUDIO = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}


def _ffmpeg_path() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def safe_dataset_name(name: str) -> str:
    """Return a portable folder name without path traversal or unsafe characters."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    if not cleaned:
        raise ValueError("Enter a dataset name using letters, numbers, hyphens, or underscores.")
    return cleaned[:48]


def prepare_recordings(
    uploaded_files: Iterable[str | Path],
    dataset_name: str,
    dataset_root: Path,
) -> tuple[Path, int]:
    """Convert uploaded recordings to mono WAV files in a local RVC dataset folder."""
    files = list(uploaded_files or [])
    if not files:
        raise ValueError("Upload at least one recording first.")
    name = safe_dataset_name(dataset_name)
    target = (dataset_root / name).resolve()
    root = dataset_root.resolve()
    if target.parent != root:
        raise ValueError("Invalid dataset folder name.")
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError(
            "FFmpeg is unavailable. Re-run install.bat to install the bundled FFmpeg "
            "helper, or install FFmpeg and add ffmpeg.exe to PATH, then restart the app. "
            "No recordings were processed."
        )
    valid = []
    for item in files:
        source = Path(item)
        if not source.is_file():
            raise ValueError(f"Recording not found: {source.name}")
        if source.suffix.lower() not in SUPPORTED_AUDIO:
            raise ValueError(f"Unsupported recording format: {source.name}")
        if source.stat().st_size == 0:
            raise ValueError(f"Recording is empty: {source.name}")
        valid.append(source)
    target.mkdir(parents=True, exist_ok=True)
    count = 0
    for index, source in enumerate(valid, start=1):
        output = target / f"recording_{index:03d}.wav"
        command = [
            ffmpeg, "-nostdin", "-y", "-i", str(source), "-vn",
            "-ac", "1", "-ar", "44100", "-c:a", "pcm_s16le", str(output)
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode or not output.exists() or output.stat().st_size == 0:
            detail = (result.stderr or result.stdout or "No FFmpeg diagnostic output")[-2000:]
            raise RuntimeError(f"Could not convert {source.name}.\n{detail}")
        count += 1
    return target, count
