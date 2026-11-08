from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch


def load_audio_without_torchcodec(
    path: str | Path,
    frame_offset: int = 0,
    num_frames: int = -1,
    normalize: bool = True,
    channels_first: bool = True,
    format: str | None = None,
) -> tuple[torch.Tensor, int]:
    """Read Demucs input WAV files through SoundFile instead of TorchCodec."""
    if not normalize:
        raise ValueError("Demucs input loading requires normalized float audio.")
    audio, samplerate = sf.read(
        str(path),
        start=frame_offset,
        frames=num_frames,
        dtype="float32",
        always_2d=True,
    )
    waveform = torch.from_numpy(audio)
    if channels_first:
        waveform = waveform.transpose(0, 1)
    return waveform, samplerate


def save_audio_without_torchcodec(
    wav: torch.Tensor,
    path: str | Path,
    samplerate: int,
    bitrate: int = 320,
    clip: str = "rescale",
    bits_per_sample: int = 16,
    as_float: bool = False,
    preset: int = 2,
) -> None:
    """Save Demucs audio I/O without TorchCodec.

    Demucs 4.0.1 calls torchaudio.load/save for WAV input and stem output. TorchAudio 2.11
    delegates those operations to TorchCodec, which needs FFmpeg shared DLLs
    on Windows. SoundFile already ships with the app and can read/write the
    pipeline's WAV files directly, so keep Demucs independent of that runtime.
    """
    from demucs.audio import encode_mp3, prevent_clip

    wav = prevent_clip(wav, mode=clip)
    destination = Path(path)
    suffix = destination.suffix.lower()

    if suffix == ".mp3":
        encode_mp3(wav, destination, samplerate, bitrate, preset, verbose=True)
        return

    if suffix not in {".wav", ".flac"}:
        raise ValueError(f"Invalid suffix for path: {suffix}")

    if bits_per_sample not in {16, 24, 32}:
        raise ValueError(f"Unsupported PCM bit depth: {bits_per_sample}")
    if suffix == ".wav" and as_float:
        subtype = "FLOAT"
    elif bits_per_sample == 16:
        subtype = "PCM_16"
    elif bits_per_sample == 24 or suffix == ".flac":
        subtype = "PCM_24"
    else:
        subtype = "PCM_32"

    audio = wav.detach().cpu().transpose(0, 1).numpy()
    sf.write(str(destination), audio, samplerate, subtype=subtype)
