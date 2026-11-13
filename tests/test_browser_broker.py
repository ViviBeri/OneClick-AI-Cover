from oneclick_cover.browser_broker import (
    BrowserSessionStore,
    validate_browser_request_boundary,
)


def test_session_requires_cookie_and_separate_csrf_for_mutations():
    store = BrowserSessionStore()
    session = store.create()

    assert store.validate(session.session_id)
    assert not store.validate(None)
    assert not store.validate(session.session_id, require_csrf=True)
    assert not store.validate(
        session.session_id, csrf_token="wrong", require_csrf=True
    )
    assert store.validate(
        session.session_id,
        csrf_token=session.csrf_token,
        require_csrf=True,
    )


def test_session_expires_and_can_be_revoked():
    now = [100.0]
    store = BrowserSessionStore(ttl_seconds=5, clock=lambda: now[0])
    session = store.create()
    assert store.validate(session.session_id)

    now[0] = 105.0
    assert not store.validate(session.session_id)

    active = store.create()
    store.revoke_all()
    assert not store.validate(active.session_id)


def test_session_store_rejects_non_positive_lifetime():
    import pytest

    with pytest.raises(ValueError, match="positive"):
        BrowserSessionStore(ttl_seconds=0)


def test_browser_boundary_requires_exact_host_and_origin_for_mutations():
    expected = {
        "host": "127.0.0.1:7860",
        "expected_host": "127.0.0.1:7860",
        "expected_origin": "http://127.0.0.1:7860",
    }
    assert validate_browser_request_boundary(
        **expected, origin="http://127.0.0.1:7860", state_changing=True
    )
    assert not validate_browser_request_boundary(
        **expected, origin="https://attacker.example", state_changing=True
    )
    assert not validate_browser_request_boundary(
        **expected, origin=None, state_changing=True
    )
    assert not validate_browser_request_boundary(
        **{**expected, "host": "attacker.example"},
        origin="http://127.0.0.1:7860",
        state_changing=False,
    )


def test_safe_same_origin_request_may_omit_origin():
    assert validate_browser_request_boundary(
        host="127.0.0.1:7860",
        origin=None,
        expected_host="127.0.0.1:7860",
        expected_origin="http://127.0.0.1:7860",
        state_changing=False,
    )


import pytest
from fastapi.testclient import TestClient

from oneclick_cover.browser_broker import create_browser_broker_app
from oneclick_cover.jobs import LocalJobStore
from oneclick_cover.runner import LocalJobRunner


@pytest.fixture
def broker_fixture(tmp_path):
    uploads = tmp_path / "uploads"
    voices = tmp_path / "voices"
    outputs = tmp_path / "outputs"
    uploads.mkdir()
    voices.mkdir()
    (uploads / "song.wav").write_bytes(b"song")
    (voices / "trusted.pth").write_bytes(b"model")
    runner = LocalJobRunner(store=LocalJobStore())
    sessions = BrowserSessionStore()
    app = create_browser_broker_app(
        runner,
        session_store=sessions,
        upload_dir=uploads,
        voice_dir=voices,
        output_dir=outputs,
        expected_host="127.0.0.1:7860",
        expected_origin="http://127.0.0.1:7860",
    )
    client = TestClient(app, base_url="http://127.0.0.1:7860")
    try:
        yield client, runner, outputs
    finally:
        sessions.revoke_all()
        runner.shutdown()


def start_browser_session(client):
    response = client.post(
        "/api/browser/session",
        headers={"Origin": "http://127.0.0.1:7860"},
    )
    assert response.status_code == 200
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=strict" in response.headers["set-cookie"].lower()
    return response.json()["csrf_token"]


def test_broker_requires_same_origin_and_valid_session(broker_fixture):
    client, _, _ = broker_fixture
    assert client.get("/api/browser/jobs").status_code == 401
    csrf = start_browser_session(client)

    assert client.get("/api/browser/jobs").status_code == 200
    assert client.post(
        "/api/browser/session",
        headers={"Origin": "https://attacker.example"},
    ).status_code == 403
    assert client.post(
        "/api/browser/jobs",
        json={"song_name": "song.wav", "model_name": "trusted.pth", "trust_confirmed": True},
        headers={"Origin": "http://127.0.0.1:7860", "X-CSRF-Token": "wrong"},
    ).status_code == 401
    assert csrf


def test_broker_rejects_host_and_missing_mutation_origin(broker_fixture):
    client, _, _ = broker_fixture
    assert client.get(
        "/api/browser/jobs",
        headers={"Host": "attacker.example"},
    ).status_code == 403
    assert client.post("/api/browser/session").status_code == 403


def test_broker_lists_jobs_and_requires_csrf_for_logout(broker_fixture):
    client, runner, _ = broker_fixture
    csrf = start_browser_session(client)
    job = runner.store.create()

    response = client.get("/api/browser/jobs")
    assert response.status_code == 200
    assert response.json()[0]["id"] == job.id

    assert client.delete("/api/browser/session").status_code == 401
    response = client.delete(
        "/api/browser/session",
        headers={"Origin": "http://127.0.0.1:7860", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert client.get("/api/browser/jobs").status_code == 401


def test_broker_validates_job_filenames_and_trust(broker_fixture):
    client, _, _ = broker_fixture
    csrf = start_browser_session(client)
    headers = {"Origin": "http://127.0.0.1:7860", "X-CSRF-Token": csrf}

    payload = {"song_name": "../song.wav", "model_name": "trusted.pth", "trust_confirmed": True}
    assert client.post("/api/browser/jobs", json=payload, headers=headers).status_code == 400

    payload.update(song_name="song.wav", trust_confirmed=False)
    assert client.post("/api/browser/jobs", json=payload, headers=headers).status_code == 400
