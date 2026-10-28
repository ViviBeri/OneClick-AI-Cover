from oneclick_cover.validation import validate_audio_file, validate_voice_model
import pytest

def test_rejects_missing_audio(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        validate_audio_file(tmp_path / "missing.mp3")

def test_rejects_unsupported_audio(tmp_path):
    path = tmp_path / "song.ogg"
    path.write_bytes(b"audio")
    with pytest.raises(ValueError, match="Unsupported"):
        validate_audio_file(path)

def test_rejects_empty_audio(tmp_path):
    path = tmp_path / "song.wav"
    path.write_bytes(b"")
    with pytest.raises(ValueError, match="empty"):
        validate_audio_file(path)

def test_rejects_tiny_model(tmp_path):
    path = tmp_path / "voice.pth"
    path.write_bytes(b"tiny")
    with pytest.raises(ValueError, match="small"):
        validate_voice_model(path)
