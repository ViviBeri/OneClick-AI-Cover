from pathlib import Path
from types import SimpleNamespace

import pytest

import app


class FakeApiServer:
    def __init__(self, tmp_path, *, fail_start=False):
        self.fail_start = fail_start
        self.started = False
        self.stopped = False
        self.upload_dir = tmp_path / "uploads"
        self.voice_dir = tmp_path / "voices"
        self.output_dir = tmp_path / "outputs"
        for folder in (self.upload_dir, self.voice_dir, self.output_dir):
            folder.mkdir()
        self.runner = SimpleNamespace(store=object())

    def start(self):
        self.started = True
        if self.fail_start:
            raise RuntimeError("API startup failed")

    def stop(self):
        self.stopped = True


class FakeTimer:
    def __init__(self, *_args, **_kwargs):
        pass

    def start(self):
        pass


def prepare_launch(monkeypatch, calls):
    monkeypatch.setattr(app.gr, "mount_gradio_app", lambda parent, _demo, **_kwargs: parent)
    monkeypatch.setattr(app.uvicorn, "run", lambda application, **kwargs: calls.append((application, kwargs)))
    monkeypatch.setattr(app, "Timer", FakeTimer)


def test_desktop_launch_stops_api_after_gradio_exits(monkeypatch, tmp_path):
    server = FakeApiServer(tmp_path)
    launched = []
    prepare_launch(monkeypatch, launched)

    app.launch_application(api_server_factory=lambda: server)

    assert server.started is True
    assert server.stopped is True
    assert launched[0][1]["host"] == "127.0.0.1"
    assert launched[0][1]["port"] == 7860
    assert app._active_job_store is None


def test_desktop_launch_stops_api_when_gradio_startup_fails(monkeypatch, tmp_path):
    server = FakeApiServer(tmp_path)

    def fail_run(_application, **_kwargs):
        raise RuntimeError("Gradio startup failed")

    monkeypatch.setattr(app.gr, "mount_gradio_app", lambda parent, _demo, **_kwargs: parent)
    monkeypatch.setattr(app.uvicorn, "run", fail_run)
    monkeypatch.setattr(app, "Timer", FakeTimer)

    with pytest.raises(RuntimeError, match="Gradio startup failed"):
        app.launch_application(api_server_factory=lambda: server)

    assert server.started is True
    assert server.stopped is True
    assert app._active_job_store is None


def test_desktop_launch_cleans_up_after_api_startup_failure(monkeypatch, tmp_path):
    server = FakeApiServer(tmp_path, fail_start=True)
    monkeypatch.setattr(app.uvicorn, "run", lambda *_args, **_kwargs: pytest.fail("Gradio must not start"))

    with pytest.raises(RuntimeError, match="API startup failed"):
        app.launch_application(api_server_factory=lambda: server)

    assert server.stopped is True
    assert app._active_job_store is None
