from __future__ import annotations

from pathlib import Path

import soundfile as sf
import torch


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
    """Save Demucs stems without torchaudio.save/TorchCodec.

    Demucs 4.0.1 calls torchaudio.save for WAV/FLAC output. TorchAudio 2.11
    delegates those operations to TorchCodec, which needs FFmpeg shared DLLs
    on Windows. SoundFile already ships with the app and can write these stems
    directly, so keep the model pipeline independent of that extra runtime.
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

    if suffix == ".wav" and as_float:
        subtype = "FLOAT"
    elif bits_per_sample == 16:
        subtype = "PCM_16"
    elif bits_per_sample == 24 or suffix == ".flac":
        subtype = "PCM_24"
    elif bits_per_sample == 32:
        subtype = "PCM_32"
    else:
        raise ValueError(f"Unsupported PCM bit depth: {bits_per_sample}")

    audio = wav.detach().cpu().transpose(0, 1).numpy()
    sf.write(str(destination), audio, samplerate, subtype=subtype)
