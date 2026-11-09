import gradio as gr

import app
from oneclick_cover import hf_models


def test_refresh_models_returns_component_configuration(monkeypatch):
    choices = ["voice-a.pth", "voice-b.pth"]
    monkeypatch.setattr(app, "models", lambda: choices)

    result = app.refresh_models()

    assert isinstance(result, gr.Dropdown)
    assert result.choices == [(name, name) for name in choices]
    assert result.value == "voice-a.pth"


def test_import_voice_model_returns_updated_dropdown(monkeypatch, tmp_path):
    source = tmp_path / "voice.pth"
    source.write_bytes(b"test model")
    voice_dir = tmp_path / "voices"
    voice_dir.mkdir()

    monkeypatch.setattr(app, "VOICE_DIR", voice_dir)
    monkeypatch.setattr(app, "validate_voice_model", lambda path: None)
    monkeypatch.setattr(app, "models", lambda: ["voice.pth"])

    result, message = app.import_voice_model(str(source), True)

    assert isinstance(result, gr.Dropdown)
    assert result.choices == [("voice.pth", "voice.pth")]
    assert result.value == "voice.pth"
    assert (voice_dir / "voice.pth").read_bytes() == b"test model"
    assert "Imported voice.pth" in message


def test_downloaded_unverified_model_does_not_change_selection(monkeypatch, tmp_path):
    unverified_dir = tmp_path / "unverified"
    unverified_dir.mkdir()
    monkeypatch.setattr(app, "UNVERIFIED_MODEL_DIR", unverified_dir)
    monkeypatch.setattr(
        hf_models,
        "download_public_pth_model",
        lambda repo_id, filename, destination, confirmed: "Download complete.",
    )

    result, message = app.download_hf_model(
        "publisher/model", "voice.pth", True
    )

    assert result == gr.skip()
    assert "Download complete." in message
    assert "stored outside the active voice-model folder" in message



def test_import_voice_model_requires_explicit_trust(monkeypatch, tmp_path):
    import pytest

    source = tmp_path / "untrusted.pth"
    source.write_bytes(b"test model")

    with pytest.raises(gr.Error, match="Trust acknowledgement required"):
        app.import_voice_model(str(source), False)
