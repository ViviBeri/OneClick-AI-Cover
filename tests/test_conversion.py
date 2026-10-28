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
        captured["command"] = command
        output.write_bytes(b"converted")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr(conversion, "RVC_ROOT", backend)
    monkeypatch.setattr(conversion.subprocess, "run", fake_run)

    conversion.convert_voice(source, output, model, pitch=2)

    command = captured["command"]
    index_rate = command.index("--index-rate")
    assert command[index_rate + 1] == "0"
    assert command[command.index("--pitch") + 1] == "2"
    assert output.read_bytes() == b"converted"



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
