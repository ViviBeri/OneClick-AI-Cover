import pytest

import app


class FakeApiServer:
    def __init__(self, *, fail_start=False):
        self.fail_start = fail_start
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True
        if self.fail_start:
            raise RuntimeError("API startup failed")

    def stop(self):
        self.stopped = True


def test_desktop_launch_stops_api_after_gradio_exits(monkeypatch):
    server = FakeApiServer()
    launched = []

    def fake_launch(**kwargs):
        launched.append(kwargs)

    monkeypatch.setattr(app.demo, "launch", fake_launch)
    app.launch_application(api_server_factory=lambda: server)

    assert server.started is True
    assert server.stopped is True
    assert launched[0]["server_name"] == "127.0.0.1"
    assert launched[0]["server_port"] == 7860


def test_desktop_launch_stops_api_when_gradio_startup_fails(monkeypatch):
    server = FakeApiServer()

    def fail_launch(**kwargs):
        raise RuntimeError("Gradio startup failed")

    monkeypatch.setattr(app.demo, "launch", fail_launch)
    with pytest.raises(RuntimeError, match="Gradio startup failed"):
        app.launch_application(api_server_factory=lambda: server)

    assert server.started is True
    assert server.stopped is True


def test_desktop_launch_cleans_up_after_api_startup_failure(monkeypatch):
    server = FakeApiServer(fail_start=True)
    monkeypatch.setattr(app.demo, "launch", lambda **kwargs: pytest.fail("Gradio must not start"))

    with pytest.raises(RuntimeError, match="API startup failed"):
        app.launch_application(api_server_factory=lambda: server)

    assert server.stopped is True
