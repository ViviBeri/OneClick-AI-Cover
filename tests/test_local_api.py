from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from oneclick_cover.api import create_local_api, validate_loopback_host
from oneclick_cover.jobs import JobStatus, LocalJobStore
from oneclick_cover.runner import LocalJobRunner


TOKEN = "local-api-test-token-that-is-long-enough-123"


@pytest.fixture
def api_fixture(tmp_path):
    uploads = tmp_path / "uploads"
    voices = tmp_path / "voices"
    outputs = tmp_path / "outputs"
    uploads.mkdir()
    voices.mkdir()
    (uploads / "song.wav").write_bytes(b"song")
    (voices / "trusted.pth").write_bytes(b"model")
    runner = LocalJobRunner()
    app = create_local_api(
        runner,
        token=TOKEN,
        upload_dir=uploads,
        voice_dir=voices,
        output_dir=outputs,
    )
    try:
        yield TestClient(app, base_url="http://127.0.0.1"), runner, outputs
    finally:
        runner.shutdown()


def auth():
    return {"Authorization": f"Bearer {TOKEN}"}


def test_api_requires_bearer_token(api_fixture):
    client, _, _ = api_fixture
    assert client.get("/health").status_code == 401
    assert client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/health", headers=auth()).json() == {"status": "ok"}


def test_api_rejects_untrusted_model_and_path_traversal(api_fixture):
    client, _, _ = api_fixture
    headers = auth()
    payload = {
        "song_name": "song.wav",
        "model_name": "trusted.pth",
        "trust_confirmed": False,
    }
    assert client.post("/jobs", json=payload, headers=headers).status_code == 400
    payload.update(trust_confirmed=True, song_name="../outside.wav")
    assert client.post("/jobs", json=payload, headers=headers).status_code == 400
    payload.update(song_name="song.wav", model_name="../trusted.pth")
    assert client.post("/jobs", json=payload, headers=headers).status_code == 400


def test_api_rejects_short_token_and_non_loopback_host(tmp_path):
    runner = LocalJobRunner()
    try:
        with pytest.raises(ValueError, match="32 characters"):
            create_local_api(
                runner, token="short", upload_dir=tmp_path / "u",
                voice_dir=tmp_path / "v", output_dir=tmp_path / "o",
            )
    finally:
        runner.shutdown()

    assert validate_loopback_host("127.0.0.1") == "127.0.0.1"
    with pytest.raises(ValueError, match="loopback"):
        validate_loopback_host("0.0.0.0")


def test_api_returns_job_status_and_result(api_fixture, monkeypatch):
    client, runner, outputs = api_fixture
    result = outputs / "cover.wav"
    result.write_bytes(b"audio")
    job = runner.store.create()
    runner.store.mark_running(job.id)
    runner.store.complete(job.id, result)

    response = client.get(f"/jobs/{job.id}", headers=auth())
    assert response.status_code == 200
    assert response.json()["status"] == JobStatus.COMPLETED.value
    download = client.get(f"/jobs/{job.id}/result", headers=auth())
    assert download.status_code == 200
    assert download.content == b"audio"


def test_api_does_not_expose_result_for_incomplete_job(api_fixture):
    client, runner, _ = api_fixture
    job = runner.store.create()
    response = client.get(f"/jobs/{job.id}/result", headers=auth())
    assert response.status_code == 409



def test_api_rejects_browser_origin_requests(api_fixture):
    client, _, _ = api_fixture
    response = client.get(
        "/health",
        headers={**auth(), "Origin": "https://attacker.example"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Browser access is not enabled for the local API."


def test_api_rejects_non_loopback_host_headers(api_fixture):
    client, _, _ = api_fixture
    response = client.get(
        "/health",
        headers={**auth(), "Host": "attacker.example"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "The local API only accepts loopback hosts."
