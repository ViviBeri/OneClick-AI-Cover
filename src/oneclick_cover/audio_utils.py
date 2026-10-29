from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf

def _ffmpeg_path() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None

def _run(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout or "No diagnostic output")[-3500:]
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command[:4])}\n{detail}")

def _require_output_file(path: Path, operation: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"{operation} completed without creating a non-empty output file: {path}")

def transcode_to_wav(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_path()
    if ffmpeg:
        _run([ffmpeg, "-y", "-i", str(source), "-vn", "-ac", "2", "-ar", "44100", str(destination)])
        _require_output_file(destination, "Audio conversion")
        return
    try:
        audio, sr = sf.read(str(source), dtype="float32", always_2d=True)
        sf.write(str(destination), audio, sr)
        _require_output_file(destination, "Audio conversion")
    except Exception as exc:
        raise RuntimeError("Could not decode this file. Re-run install.bat so the managed FFmpeg package is installed.") from exc

def probe_audio(path: Path) -> dict:
    info = sf.info(str(path)) if path.suffix.lower() in {".wav", ".flac"} else None
    return {"duration": info.duration if info else None, "sample_rate": info.samplerate if info else None}

def _read_stereo(path: Path):
    audio, sr = sf.read(str(path), dtype="float32", always_2d=True)
    if audio.shape[1] == 1: audio = np.repeat(audio, 2, axis=1)
    elif audio.shape[1] > 2: audio = audio[:, :2]
    return audio, sr

def mix_audio(vocal_path: Path, instrumental_path: Path, output_path: Path, vocal_gain: float = 1.0, instrumental_gain: float = 0.85) -> None:
    vocal, vocal_sr = _read_stereo(vocal_path)
    instrumental, instrumental_sr = _read_stereo(instrumental_path)
    if vocal_sr != instrumental_sr: raise RuntimeError(f"Sample-rate mismatch: vocals={vocal_sr}, instrumental={instrumental_sr}.")
    target_len = max(len(vocal), len(instrumental))
    def pad(x):
        if len(x) < target_len: return np.pad(x, ((0, target_len-len(x)), (0, 0)))
        return x[:target_len]
    mix = pad(vocal) * vocal_gain + pad(instrumental) * instrumental_gain
    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
    if peak > 0.99: mix *= 0.99 / peak
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), mix, vocal_sr, subtype="PCM_16")

def export_mp3(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = _ffmpeg_path()
    if not ffmpeg: raise RuntimeError("MP3 export needs FFmpeg. Re-run install.bat to install the managed FFmpeg helper, or choose WAV output.")
    _run([ffmpeg, "-y", "-i", str(source), "-codec:a", "libmp3lame", "-q:a", "2", str(destination)])
    _require_output_file(destination, "MP3 export")
