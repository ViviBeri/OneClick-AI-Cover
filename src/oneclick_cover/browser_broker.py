"""In-memory security primitives for the same-origin browser broker.

These helpers deliberately do not expose or proxy the native API bearer token.
They are building blocks; route integration belongs to the Gradio application.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Callable


@dataclass(frozen=True)
class BrowserSession:
    """Credentials returned once when a browser session is created."""

    session_id: str
    csrf_token: str
    expires_at: float


class BrowserSessionStore:
    """Short-lived, process-local browser sessions with hashed stored secrets."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 1800,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Session lifetime must be positive.")
        self._ttl_seconds = float(ttl_seconds)
        self._clock = clock
        self._sessions: dict[str, tuple[str, float]] = {}
        self._lock = RLock()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def create(self) -> BrowserSession:
        """Create a session and return its cookie and CSRF secrets once."""
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = self._clock() + self._ttl_seconds
        with self._lock:
            self._purge_expired()
            self._sessions[self._digest(session_id)] = (
                self._digest(csrf_token),
                expires_at,
            )
        return BrowserSession(session_id, csrf_token, expires_at)

    def validate(
        self,
        session_id: str | None,
        *,
        csrf_token: str | None = None,
        require_csrf: bool = False,
    ) -> bool:
        """Validate a session and, for mutations, its separate CSRF token."""
        if not session_id or (require_csrf and not csrf_token):
            return False
        key = self._digest(session_id)
        with self._lock:
            record = self._sessions.get(key)
            if record is None:
                return False
            expected_csrf, expires_at = record
            if expires_at <= self._clock():
                self._sessions.pop(key, None)
                return False
            if require_csrf and not hmac.compare_digest(
                expected_csrf, self._digest(csrf_token or "")
            ):
                return False
            return True

    def revoke_all(self) -> None:
        """Invalidate every browser session, for example during app shutdown."""
        with self._lock:
            self._sessions.clear()

    def _purge_expired(self) -> None:
        now = self._clock()
        expired = [
            key for key, (_, expires_at) in self._sessions.items()
            if expires_at <= now
        ]
        for key in expired:
            self._sessions.pop(key, None)


def validate_browser_request_boundary(
    *,
    host: str | None,
    origin: str | None,
    expected_host: str,
    expected_origin: str,
    state_changing: bool,
) -> bool:
    """Require the exact loopback listener and same-origin browser requests.

    Safe requests may omit Origin, as browsers commonly do for same-origin GETs.
    If supplied, Origin must still match. State-changing requests must include it.
    """
    if not host or not hmac.compare_digest(host.lower(), expected_host.lower()):
        return False
    if state_changing and not origin:
        return False
    if origin is not None and not hmac.compare_digest(origin, expected_origin):
        return False
    return True


# The route layer is intentionally separate from the native bearer-token API.
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from oneclick_cover.jobs import ProcessingJob
from oneclick_cover.pipeline import run_cover_pipeline
from oneclick_cover.runner import LocalJobRunner


class BrowserCreateJobRequest(BaseModel):
    song_name: str = Field(min_length=1, max_length=255)
    model_name: str = Field(min_length=1, max_length=255)
    pitch: int = Field(default=0, ge=-12, le=12)
    vocal_gain: float = Field(default=1.0, ge=0.2, le=2.0)
    instrumental_gain: float = Field(default=0.85, ge=0.2, le=2.0)
    output_format: Literal["WAV", "MP3"] = "WAV"
    trust_confirmed: bool


def _serialize_browser_job(job: ProcessingJob) -> dict:
    return {
        "id": job.id,
        "status": job.status.value,
        "progress": job.progress,
        "message": job.message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "error": job.error,
        "has_result": job.output_path is not None,
    }


def create_browser_broker_app(
    runner: LocalJobRunner,
    *,
    session_store: BrowserSessionStore,
    upload_dir: str | Path,
    voice_dir: str | Path,
    output_dir: str | Path,
    expected_host: str,
    expected_origin: str,
    cookie_name: str = "oneclick_browser_session",
) -> FastAPI:
    """Create same-origin browser routes without exposing the native API token."""
    uploads = Path(upload_dir).resolve()
    voices = Path(voice_dir).resolve()
    outputs = Path(output_dir).resolve()
    uploads.mkdir(parents=True, exist_ok=True)
    voices.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def enforce_browser_boundary(request: Request, call_next):
        state_changing = request.method not in {"GET", "HEAD", "OPTIONS"}
        if not validate_browser_request_boundary(
            host=request.headers.get("host"),
            origin=request.headers.get("origin"),
            expected_host=expected_host,
            expected_origin=expected_origin,
            state_changing=state_changing,
        ):
            return JSONResponse(
                status_code=403,
                content={"detail": "Request must come from the local application origin."},
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def require_session(
        request: Request,
        csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
        *,
        mutation: bool = False,
    ) -> None:
        session_id = request.cookies.get(cookie_name)
        if not session_store.validate(
            session_id, csrf_token=csrf_token, require_csrf=mutation
        ):
            raise HTTPException(status_code=401, detail="A valid browser session is required.")

    def require_upload(name: str) -> Path:
        if Path(name).name != name:
            raise HTTPException(status_code=400, detail="Song must be selected by filename.")
        candidate = (uploads / name).resolve()
        if candidate.parent != uploads or not candidate.is_file():
            raise HTTPException(status_code=400, detail="Song must be an existing file in the upload folder.")
        if candidate.suffix.lower() not in {".wav", ".mp3", ".flac"}:
            raise HTTPException(status_code=400, detail="Unsupported song format.")
        return candidate

    def require_model(name: str) -> Path:
        if Path(name).name != name or not name.lower().endswith(".pth"):
            raise HTTPException(status_code=400, detail="Select a voice model by filename.")
        candidate = (voices / name).resolve()
        if candidate.parent != voices or not candidate.is_file():
            raise HTTPException(status_code=404, detail="Voice model not found.")
        return candidate

    @app.post("/api/browser/session")
    def create_session(response_request: Request):
        session = session_store.create()
        response = JSONResponse({"csrf_token": session.csrf_token})
        response.set_cookie(
            key=cookie_name,
            value=session.session_id,
            max_age=max(1, int(session.expires_at - session_store._clock())),
            httponly=True,
            secure=False,
            samesite="strict",
            path="/api/browser",
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.delete("/api/browser/session")
    def delete_session(request: Request, csrf_token: str | None = Header(default=None, alias="X-CSRF-Token")):
        require_session(request, csrf_token, mutation=True)
        response = JSONResponse({"status": "signed_out"})
        response.delete_cookie(cookie_name, path="/api/browser", httponly=True, samesite="strict")
        return response

    @app.get("/api/browser/jobs")
    def list_jobs(request: Request):
        require_session(request)
        return [_serialize_browser_job(job) for job in runner.list()]

    @app.post("/api/browser/jobs", status_code=202)
    def create_job(
        payload: BrowserCreateJobRequest,
        request: Request,
        csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    ):
        require_session(request, csrf_token, mutation=True)
        if not payload.trust_confirmed:
            raise HTTPException(status_code=400, detail="Voice-model trust acknowledgement is required.")
        song = require_upload(payload.song_name)
        model = require_model(payload.model_name)

        def task(progress):
            return run_cover_pipeline(
                song,
                model,
                payload.pitch,
                payload.vocal_gain,
                payload.instrumental_gain,
                payload.output_format,
                outputs,
                progress=progress,
            )

        try:
            job = runner.submit(task)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Local processing is unavailable.") from exc
        return _serialize_browser_job(job)

    @app.get("/api/browser/jobs/{job_id}")
    def get_job(job_id: str, request: Request):
        require_session(request)
        job = runner.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return _serialize_browser_job(job)

    @app.post("/api/browser/jobs/{job_id}/cancel")
    def cancel_job(
        job_id: str,
        request: Request,
        csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    ):
        require_session(request, csrf_token, mutation=True)
        try:
            cancelled = runner.cancel(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found.") from exc
        if not cancelled:
            raise HTTPException(status_code=409, detail="Only queued jobs can be cancelled.")
        return _serialize_browser_job(runner.get(job_id))

    @app.get("/api/browser/jobs/{job_id}/result")
    def get_result(job_id: str, request: Request):
        require_session(request)
        job = runner.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.output_path is None or job.status.value != "completed":
            raise HTTPException(status_code=409, detail="Job has no completed result.")
        result = job.output_path.resolve()
        if outputs not in result.parents or not result.is_file():
            raise HTTPException(status_code=404, detail="Result not found.")
        return FileResponse(result, filename=result.name)

    return app
