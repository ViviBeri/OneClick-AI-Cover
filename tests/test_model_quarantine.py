from pathlib import Path

import app
from oneclick_cover import hf_models


def test_hugging_face_download_is_stored_outside_active_voice_models(tmp_path, monkeypatch):
    active_dir = tmp_path / "models" / "voices"
    quarantine_dir = tmp_path / "models" / "unverified"
    active_dir.mkdir(parents=True)
    quarantine_dir.mkdir(parents=True)

    captured = {}

    def fake_download(repo_id, filename, destination_dir, confirmed):
        captured["repo_id"] = repo_id
        captured["filename"] = filename
        captured["destination_dir"] = Path(destination_dir)
        captured["confirmed"] = confirmed
        (Path(destination_dir) / Path(filename).name).write_bytes(b"test-model")
        return "downloaded to quarantine"

    monkeypatch.setattr(app, "VOICE_DIR", active_dir)
    monkeypatch.setattr(app, "UNVERIFIED_MODEL_DIR", quarantine_dir)
    monkeypatch.setattr(hf_models, "download_public_pth_model", fake_download)

    _, status = app.download_hf_model(
        "trusted/publisher", "folder/voice.pth", True
    )

    assert captured["destination_dir"] == quarantine_dir
    assert captured["confirmed"] is True
    assert (quarantine_dir / "voice.pth").is_file()
    assert not (active_dir / "voice.pth").exists()
    assert "outside the active voice-model folder" in status


def test_quarantined_downloads_are_not_selectable_for_conversion(tmp_path, monkeypatch):
    active_dir = tmp_path / "models" / "voices"
    quarantine_dir = tmp_path / "models" / "unverified"
    active_dir.mkdir(parents=True)
    quarantine_dir.mkdir(parents=True)

    (active_dir / "approved.pth").write_bytes(b"approved-model")
    (quarantine_dir / "not-yet-approved.pth").write_bytes(b"unverified-model")

    monkeypatch.setattr(app, "VOICE_DIR", active_dir)
    monkeypatch.setattr(app, "UNVERIFIED_MODEL_DIR", quarantine_dir)

    assert app.models() == ["approved.pth"]
    assert "not-yet-approved.pth" not in app.models()
