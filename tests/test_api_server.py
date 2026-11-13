from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from oneclick_cover.api_server import LocalApiServer


def request_health(server, token=None):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{server.base_url}/health", headers=headers)
    try:
        with urlopen(request, timeout=2) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def test_server_starts_on_loopback_with_random_token_and_stops(tmp_path):
    server = LocalApiServer(
        upload_dir=tmp_path / "uploads",
        voice_dir=tmp_path / "voices",
        output_dir=tmp_path / "outputs",
    )
    server.start()
    try:
        assert server.host == "127.0.0.1"
        assert server.port is not None
        assert len(server.token) >= 32
        assert request_health(server)[0] == 401
        status, body = request_health(server, server.token)
        assert status == 200
        assert body == b'{"status":"ok"}'
    finally:
        server.stop()

    assert server.port is None
    with pytest.raises(RuntimeError, match="not started"):
        _ = server.token
    with pytest.raises(RuntimeError, match="cannot be restarted"):
        server.start()


def test_server_start_is_idempotent(tmp_path):
    server = LocalApiServer(
        upload_dir=tmp_path / "uploads",
        voice_dir=tmp_path / "voices",
        output_dir=tmp_path / "outputs",
    )
    try:
        server.start()
        port = server.port
        token = server.token
        assert server.start() is server
        assert server.port == port
        assert server.token == token
    finally:
        server.stop()


def test_server_rejects_invalid_startup_timeout():
    with pytest.raises(ValueError, match="positive"):
        LocalApiServer(startup_timeout=0)


def test_server_reopens_persistent_job_history(tmp_path):
    database = tmp_path / "state" / "jobs.sqlite3"
    output = tmp_path / "outputs" / "cover.wav"
    output.parent.mkdir()
    output.write_bytes(b"audio")

    first = LocalApiServer(
        upload_dir=tmp_path / "uploads",
        voice_dir=tmp_path / "voices",
        output_dir=output.parent,
        job_database_path=database,
    )
    first.start()
    job = first.runner.store.create()
    first.runner.store.mark_running(job.id)
    first.runner.store.complete(job.id, output)
    first.stop()

    second = LocalApiServer(
        upload_dir=tmp_path / "uploads",
        voice_dir=tmp_path / "voices",
        output_dir=output.parent,
        job_database_path=database,
    )
    second.start()
    try:
        restored = second.runner.get(job.id)
        assert restored is not None
        assert restored.status.value == "completed"
        assert restored.output_path == output.resolve()
    finally:
        second.stop()
