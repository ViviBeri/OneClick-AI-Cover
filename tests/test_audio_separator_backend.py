import json
import subprocess

import pytest

from oneclick_cover.separation_backends import AudioSeparatorBackend


def test_audio_separator_requires_explicit_runtime_and_model(monkeypatch, tmp_path):
    monkeypatch.delenv("ONECLICK_AUDIO_SEPARATOR_PYTHON", raising=False)
    monkeypatch.delenv("ONECLICK_AUDIO_SEPARATOR_MODEL_PATH", raising=False)
    with pytest.raises(RuntimeError, match="not configured"):
        AudioSeparatorBackend().separate(tmp_path / "input.wav", tmp_path)


def test_audio_separator_requires_existing_model(monkeypatch, tmp_path):
    executable = tmp_path / "python.exe"
    executable.touch()
    monkeypatch.setenv("ONECLICK_AUDIO_SEPARATOR_PYTHON", str(executable))
    monkeypatch.setenv("ONECLICK_AUDIO_SEPARATOR_MODEL_PATH", str(tmp_path / "missing.onnx"))
    with pytest.raises(RuntimeError, match="model was not found"):
        AudioSeparatorBackend().separate(tmp_path / "input.wav", tmp_path)


def test_audio_separator_invokes_isolated_worker_and_validates_outputs(monkeypatch, tmp_path):
    executable = tmp_path / "python.exe"
    model = tmp_path / "model.onnx"
    source = tmp_path / "input.wav"
    executable.touch()
    model.touch()
    source.touch()
    workspace = tmp_path / "job"
    workspace.mkdir()
    vocals = workspace / "vocals.wav"
    instrumental = workspace / "instrumental.wav"
    vocals.write_bytes(b"vocals")
    instrumental.write_bytes(b"instrumental")
    monkeypatch.setenv("ONECLICK_AUDIO_SEPARATOR_PYTHON", str(executable))
    monkeypatch.setenv("ONECLICK_AUDIO_SEPARATOR_MODEL_PATH", str(model))

    def fake_run(command, **kwargs):
        assert command[0] == str(executable)
        assert command[1].endswith("audio_separator_worker.py")
        assert kwargs["timeout"] == 90
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"vocals": str(vocals), "instrumental": str(instrumental)}),
            stderr="",
        )

    monkeypatch.setattr("oneclick_cover.separation_backends.subprocess.run", fake_run)
    result = AudioSeparatorBackend().separate(source, workspace, timeout=90)
    assert result == (vocals, instrumental)


def test_audio_separator_rejects_output_outside_job_directory(monkeypatch, tmp_path):
    executable = tmp_path / "python.exe"
    model = tmp_path / "model.onnx"
    source = tmp_path / "input.wav"
    for path in (executable, model, source):
        path.touch()
    workspace = tmp_path / "job"
    workspace.mkdir()
    outside = tmp_path / "vocals.wav"
    outside.write_bytes(b"not allowed")
    inside = workspace / "instrumental.wav"
    inside.write_bytes(b"instrumental")
    monkeypatch.setenv("ONECLICK_AUDIO_SEPARATOR_PYTHON", str(executable))
    monkeypatch.setenv("ONECLICK_AUDIO_SEPARATOR_MODEL_PATH", str(model))
    monkeypatch.setattr(
        "oneclick_cover.separation_backends.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(
            command, 0, stdout=json.dumps(
                {"vocals": str(outside), "instrumental": str(inside)}
            ), stderr=""
        ),
    )
    with pytest.raises(RuntimeError, match="invalid or empty stem"):
        AudioSeparatorBackend().separate(source, workspace)
