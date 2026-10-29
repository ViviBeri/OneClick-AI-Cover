from pathlib import Path
from types import SimpleNamespace

from oneclick_cover import conversion


def test_conversion_disables_index_when_no_index_picker_exists(monkeypatch, tmp_path):
    backend = tmp_path / "rvc"
    (backend / "infer").mkdir(parents=True)
    (backend / "infer" / "cli.py").write_text("# test stub", encoding="utf-8")
    python = backend / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    model = tmp_path / "voice.pth"
    model.write_bytes(b"model")
    source = tmp_path / "vocal.wav"
    source.write_bytes(b"audio")
    output = tmp_path / "converted.wav"
    captured = {}

    def fake_run(command, **kwargs):
        import numpy as np
        import soundfile as sf

        captured["command"] = command
        sf.write(str(output), np.zeros((2205, 1), dtype=np.float32), 22050)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(conversion, "RVC_ROOT", backend)
    monkeypatch.setattr(conversion.subprocess, "run", fake_run)

    conversion.convert_voice(source, output, model, pitch=2)

    command = captured["command"]
    index_rate = command.index("--index-rate")
    assert command[index_rate + 1] == "0"
    assert command[command.index("--pitch") + 1] == "2"
    import soundfile as sf
    assert sf.info(str(output)).frames == 2205



def test_conversion_reports_missing_backend_cli(monkeypatch, tmp_path):
    monkeypatch.setattr(conversion, "RVC_ROOT", tmp_path / "missing-rvc")
    try:
        conversion.convert_voice(
            tmp_path / "vocal.wav",
            tmp_path / "converted.wav",
            tmp_path / "voice.pth",
        )
    except RuntimeError as exc:
        assert "RVC backend is missing" in str(exc)
    else:
        raise AssertionError("Expected a clear error when the RVC CLI is missing")


def test_conversion_includes_backend_diagnostics_on_failure(monkeypatch, tmp_path):
    backend = tmp_path / "rvc"
    (backend / "infer").mkdir(parents=True)
    (backend / "infer" / "cli.py").write_text("# test stub", encoding="utf-8")
    python = backend / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    model = tmp_path / "voice.pth"
    model.write_bytes(b"model")
    source = tmp_path / "vocal.wav"
    source.write_bytes(b"audio")

    def fake_run(command, **kwargs):
        return SimpleNamespace(
            returncode=2,
            stderr="RuntimeError: test backend diagnostic",
            stdout="",
        )

    monkeypatch.setattr(conversion, "RVC_ROOT", backend)
    monkeypatch.setattr(conversion.subprocess, "run", fake_run)

    try:
        conversion.convert_voice(source, tmp_path / "converted.wav", model)
    except RuntimeError as exc:
        assert "RVC voice conversion failed" in str(exc)
        assert "test backend diagnostic" in str(exc)
    else:
        raise AssertionError("Expected conversion failure to surface backend diagnostics")


def test_conversion_rejects_success_without_output(monkeypatch, tmp_path):
    backend = tmp_path / "rvc"
    (backend / "infer").mkdir(parents=True)
    (backend / "infer" / "cli.py").write_text("# test stub", encoding="utf-8")
    python = backend / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    model = tmp_path / "voice.pth"
    model.write_bytes(b"model")
    source = tmp_path / "vocal.wav"
    source.write_bytes(b"audio")

    monkeypatch.setattr(conversion, "RVC_ROOT", backend)
    monkeypatch.setattr(
        conversion.subprocess,
        "run",
        lambda command, **kwargs: SimpleNamespace(returncode=0, stderr="", stdout=""),
    )

    try:
        conversion.convert_voice(source, tmp_path / "converted.wav", model)
    except RuntimeError as exc:
        assert "did not create the converted vocal file" in str(exc)
    else:
        raise AssertionError("Expected a clear error when the output file is absent")



def test_conversion_rejects_missing_input_audio_before_subprocess(monkeypatch, tmp_path):
    backend = tmp_path / "rvc"
    (backend / "infer").mkdir(parents=True)
    (backend / "infer" / "cli.py").write_text("# test stub", encoding="utf-8")
    python = backend / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    model = tmp_path / "voice.pth"
    model.write_bytes(b"model")
    monkeypatch.setattr(conversion, "RVC_ROOT", backend)

    def unexpected_run(*args, **kwargs):
        raise AssertionError("RVC should not launch when input audio is missing")

    monkeypatch.setattr(conversion.subprocess, "run", unexpected_run)

    try:
        conversion.convert_voice(tmp_path / "missing.wav", tmp_path / "out.wav", model)
    except RuntimeError as exc:
        assert "Input vocal file does not exist" in str(exc)
    else:
        raise AssertionError("Expected a clear error when input audio is missing")


def test_conversion_rejects_missing_voice_model_before_subprocess(monkeypatch, tmp_path):
    backend = tmp_path / "rvc"
    (backend / "infer").mkdir(parents=True)
    (backend / "infer" / "cli.py").write_text("# test stub", encoding="utf-8")
    python = backend / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    source = tmp_path / "vocal.wav"
    source.write_bytes(b"audio")
    monkeypatch.setattr(conversion, "RVC_ROOT", backend)

    def unexpected_run(*args, **kwargs):
        raise AssertionError("RVC should not launch when the voice model is missing")

    monkeypatch.setattr(conversion.subprocess, "run", unexpected_run)

    try:
        conversion.convert_voice(source, tmp_path / "out.wav", tmp_path / "missing.pth")
    except RuntimeError as exc:
        assert "Voice model file does not exist" in str(exc)
    else:
        raise AssertionError("Expected a clear error when the voice model is missing")



def test_audio_validation_accepts_supported_nonempty_files(tmp_path):
    from oneclick_cover.validation import validate_audio_file

    for suffix in (".mp3", ".wav", ".flac", ".MP3", ".WAV"):
        audio = tmp_path / f"song{suffix}"
        audio.write_bytes(b"nonempty fixture")
        validate_audio_file(audio)


def test_audio_validation_rejects_missing_file_and_directory(tmp_path):
    import pytest
    from oneclick_cover.validation import validate_audio_file

    with pytest.raises(ValueError, match="does not exist"):
        validate_audio_file(tmp_path / "missing.wav")
    with pytest.raises(ValueError, match="does not exist"):
        validate_audio_file(tmp_path)


def test_audio_validation_rejects_unsupported_extension_and_empty_file(tmp_path):
    import pytest
    from oneclick_cover.validation import validate_audio_file

    unsupported = tmp_path / "song.m4a"
    unsupported.write_bytes(b"audio")
    with pytest.raises(ValueError, match="Unsupported audio format"):
        validate_audio_file(unsupported)

    empty = tmp_path / "empty.wav"
    empty.touch()
    with pytest.raises(ValueError, match="empty"):
        validate_audio_file(empty)


def test_voice_model_validation_accepts_nontrivial_pth_file(tmp_path):
    from oneclick_cover.validation import validate_voice_model

    model = tmp_path / "voice.pth"
    model.write_bytes(b"x" * 1024)
    validate_voice_model(model)


def test_voice_model_validation_rejects_missing_model_and_directory(tmp_path):
    import pytest
    from oneclick_cover.validation import validate_voice_model

    with pytest.raises(ValueError, match="Voice model not found"):
        validate_voice_model(tmp_path / "missing.pth")
    with pytest.raises(ValueError, match="Voice model not found"):
        validate_voice_model(tmp_path)


def test_voice_model_validation_rejects_wrong_extension_and_tiny_file(tmp_path):
    import pytest
    from oneclick_cover.validation import validate_voice_model

    wrong_type = tmp_path / "voice.bin"
    wrong_type.write_bytes(b"x" * 2048)
    with pytest.raises(ValueError, match="must be a .pth"):
        validate_voice_model(wrong_type)

    tiny_model = tmp_path / "partial.pth"
    tiny_model.write_bytes(b"partial")
    with pytest.raises(ValueError, match="suspiciously small"):
        validate_voice_model(tiny_model)


def test_conversion_rejects_stale_output_when_backend_writes_nothing(monkeypatch, tmp_path):
    backend = tmp_path / "rvc"
    (backend / "infer").mkdir(parents=True)
    (backend / "infer" / "cli.py").write_text("# test stub", encoding="utf-8")
    python = backend / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    model = tmp_path / "voice.pth"
    model.write_bytes(b"model")
    source = tmp_path / "vocal.wav"
    source.write_bytes(b"audio")
    output = tmp_path / "converted.wav"
    output.write_bytes(b"stale output from an earlier run")

    monkeypatch.setattr(conversion, "RVC_ROOT", backend)
    monkeypatch.setattr(
        conversion.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=0, stderr="", stdout="")
    )
    try:
        conversion.convert_voice(source, output, model)
    except RuntimeError as exc:
        assert "did not create the converted vocal" in str(exc)
    else:
        raise AssertionError("A stale output file must not satisfy the output check")


def test_conversion_rejects_non_audio_output(monkeypatch, tmp_path):
    backend = tmp_path / "rvc"
    (backend / "infer").mkdir(parents=True)
    (backend / "infer" / "cli.py").write_text("# test stub", encoding="utf-8")
    python = backend / ".venv" / "Scripts" / "python.exe"
    python.parent.mkdir(parents=True)
    python.write_text("", encoding="utf-8")
    model = tmp_path / "voice.pth"
    model.write_bytes(b"model")
    source = tmp_path / "vocal.wav"
    source.write_bytes(b"audio")
    output = tmp_path / "converted.wav"

    monkeypatch.setattr(conversion, "RVC_ROOT", backend)

    def fake_run(command, **kwargs):
        output.write_bytes(b"not a valid audio file")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(conversion.subprocess, "run", fake_run)

    import pytest
    with pytest.raises(RuntimeError, match="not a readable audio file"):
        conversion.convert_voice(source, output, model)
