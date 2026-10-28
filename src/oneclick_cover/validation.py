from pathlib import Path
SUPPORTED_AUDIO = {".mp3", ".wav", ".flac"}
def validate_audio_file(path: Path) -> None:
    if not path.exists() or not path.is_file(): raise ValueError("The selected song file does not exist.")
    if path.suffix.lower() not in SUPPORTED_AUDIO: raise ValueError("Unsupported audio format. Choose MP3, WAV, or FLAC.")
    if path.stat().st_size == 0: raise ValueError("The selected audio file is empty.")
def validate_voice_model(path: Path) -> None:
    if not path.exists() or not path.is_file(): raise ValueError(f"Voice model not found: {path}")
    if path.suffix.lower() != ".pth": raise ValueError("Voice model must be a .pth file.")
    if path.stat().st_size < 1024: raise ValueError("The selected .pth file is suspiciously small or incomplete.")
