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
