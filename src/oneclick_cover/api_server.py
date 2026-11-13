"""Lifecycle management for the authenticated loopback job API."""

from __future__ import annotations

import secrets
import socket
from threading import Event, RLock, Thread
from time import monotonic, sleep
from pathlib import Path

import uvicorn

from oneclick_cover.api import create_local_api, validate_loopback_host
from oneclick_cover.runner import LocalJobRunner
from oneclick_cover.settings import OUTPUT_DIR, ROOT, VOICE_DIR


class LocalApiServer:
    """Own the local API, its runner, and a per-launch bearer token."""

    def __init__(
        self,
        *,
        upload_dir: str | Path | None = None,
        voice_dir: str | Path = VOICE_DIR,
        output_dir: str | Path = OUTPUT_DIR,
        startup_timeout: float = 10.0,
        runner: LocalJobRunner | None = None,
    ) -> None:
        if startup_timeout <= 0:
            raise ValueError("Startup timeout must be positive.")
        self.host = validate_loopback_host("127.0.0.1")
        self.upload_dir = Path(upload_dir or ROOT / "uploads")
        self.voice_dir = Path(voice_dir)
        self.output_dir = Path(output_dir)
        self.startup_timeout = startup_timeout
        self.runner = runner or LocalJobRunner()
        self._owns_runner = runner is None
        self._token: str | None = None
        self._server: uvicorn.Server | None = None
        self._thread: Thread | None = None
        self._socket: socket.socket | None = None
        self._lock = RLock()
        self._stopped = False
        self.port: int | None = None

    @property
    def token(self) -> str:
        """Return the in-memory token to a trusted local integration only."""
        if self._token is None:
            raise RuntimeError("The local API server has not started.")
        return self._token

    @property
    def base_url(self) -> str:
        if self.port is None:
            raise RuntimeError("The local API server has not started.")
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> "LocalApiServer":
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self
            if self._stopped:
                raise RuntimeError("A stopped local API server cannot be restarted.")

            self._token = secrets.token_urlsafe(32)
            app = create_local_api(
                self.runner,
                token=self._token,
                upload_dir=self.upload_dir,
                voice_dir=self.voice_dir,
                output_dir=self.output_dir,
            )
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((self.host, 0))
                listener.listen(128)
                listener.setblocking(False)
                self.port = int(listener.getsockname()[1])

                config = uvicorn.Config(
                    app,
                    host=self.host,
                    port=self.port,
                    log_level="warning",
                    access_log=False,
                    server_header=False,
                    date_header=False,
                )
                server = uvicorn.Server(config)
                thread = Thread(
                    target=server.run,
                    kwargs={"sockets": [listener]},
                    name="oneclick-local-api",
                    daemon=True,
                )
                self._socket = listener
                self._server = server
                self._thread = thread
                thread.start()
            except Exception:
                listener.close()
                self._socket = None
                self._server = None
                self._thread = None
                self.port = None
                self._token = None
                raise

        deadline = monotonic() + self.startup_timeout
        while monotonic() < deadline:
            if self._server is not None and self._server.started:
                return self
            if self._thread is None or not self._thread.is_alive():
                self.stop()
                raise RuntimeError("The local API server exited during startup.")
            sleep(0.01)

        self.stop()
        raise TimeoutError("The local API server did not start before the timeout.")

    def stop(self) -> None:
        with self._lock:
            if self._stopped:
                return
            self._stopped = True
            server = self._server
            thread = self._thread
            listener = self._socket
            if server is not None:
                server.should_exit = True

        if thread is not None and thread.is_alive():
            thread.join(timeout=self.startup_timeout)
        if thread is not None and thread.is_alive():
            if listener is not None:
                listener.close()
            raise TimeoutError("The local API server did not shut down cleanly.")

        if listener is not None:
            listener.close()
        if self._owns_runner:
            self.runner.shutdown(wait=True)

        with self._lock:
            self._token = None
            self.port = None
            self._socket = None
            self._server = None
            self._thread = None

    def __enter__(self) -> "LocalApiServer":
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()
