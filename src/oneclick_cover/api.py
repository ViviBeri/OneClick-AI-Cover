"""Authenticated loopback API for local cover jobs."""

from __future__ import annotations

import hmac
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from oneclick_cover.pipeline import run_cover_pipeline
from oneclick_cover.runner import LocalJobRunner
from oneclick_cover.jobs import ProcessingJob


class CreateJobRequest(BaseModel):
    song_name: str = Field(min_length=1, max_length=255)
    model_name: str = Field(min_length=1, max_length=255)
    pitch: int = Field(default=0, ge=-12, le=12)
    vocal_gain: float = Field(default=1.0, ge=0.2, le=2.0)
    instrumental_gain: float = Field(default=0.85, ge=0.2, le=2.0)
    output_format: Literal["WAV", "MP3"] = "WAV"
    trust_confirmed: bool


def _serialize(job: ProcessingJob) -> dict:
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


def create_local_api(
    runner: LocalJobRunner,
    *,
    token: str,
    upload_dir: str | Path,
    voice_dir: str | Path,
    output_dir: str | Path,
) -> FastAPI:
    """Build an API whose every route requires the per-launch bearer token."""
    if len(token) < 32:
        raise ValueError("The local API token must contain at least 32 characters.")

    uploads = Path(upload_dir).resolve()
    voices = Path(voice_dir).resolve()
    outputs = Path(output_dir).resolve()
    uploads.mkdir(parents=True, exist_ok=True)
    voices.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="OneClick AI Cover Local API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def enforce_local_request_boundary(request: Request, call_next):
        """Reject DNS-rebinding Host headers and browser-originated requests.

        The API is a native local integration boundary for now. Browser access
        must go through a separately reviewed same-origin credential broker.
        """
        host = (request.url.hostname or "").lower()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            return JSONResponse(
                status_code=403,
                content={"detail": "The local API only accepts loopback hosts."},
            )
        if request.headers.get("origin") is not None:
            return JSONResponse(
                status_code=403,
                content={"detail": "Browser access is not enabled for the local API."},
            )
        return await call_next(request)

    def authenticate(authorization: str | None = Header(default=None)) -> None:
        scheme, _, supplied = (authorization or "").partition(" ")
        if scheme.lower() != "bearer" or not hmac.compare_digest(supplied, token):
            raise HTTPException(status_code=401, detail="Authentication required.")

    def require_upload(name: str) -> Path:
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

    @app.get("/health", dependencies=[Depends(authenticate)])
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/jobs", status_code=202, dependencies=[Depends(authenticate)])
    def create_job(request: CreateJobRequest) -> dict:
        if not request.trust_confirmed:
            raise HTTPException(status_code=400, detail="Voice-model trust acknowledgement is required.")
        song = require_upload(request.song_name)
        model = require_model(request.model_name)

        def task(progress):
            return run_cover_pipeline(
                song,
                model,
                request.pitch,
                request.vocal_gain,
                request.instrumental_gain,
                request.output_format,
                outputs,
                progress=progress,
            )

        try:
            job = runner.submit(task)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail="Local processing is unavailable.") from exc
        return _serialize(job)

    @app.get("/jobs", dependencies=[Depends(authenticate)])
    def list_jobs() -> list[dict]:
        return [_serialize(job) for job in runner.list()]

    @app.get("/jobs/{job_id}", dependencies=[Depends(authenticate)])
    def get_job(job_id: str) -> dict:
        job = runner.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return _serialize(job)

    @app.post("/jobs/{job_id}/cancel", dependencies=[Depends(authenticate)])
    def cancel_job(job_id: str) -> dict:
        try:
            cancelled = runner.cancel(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Job not found.") from exc
        if not cancelled:
            raise HTTPException(status_code=409, detail="Only queued jobs can be cancelled.")
        return _serialize(runner.get(job_id))

    @app.get("/jobs/{job_id}/result", dependencies=[Depends(authenticate)])
    def get_result(job_id: str) -> FileResponse:
        job = runner.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        if job.output_path is None or job.status.value != "completed":
            raise HTTPException(status_code=409, detail="Job has no completed result.")
        result = job.output_path.resolve()
        if result.parent.parent != outputs and outputs not in result.parents:
            raise HTTPException(status_code=404, detail="Result not found.")
        if not result.is_file():
            raise HTTPException(status_code=404, detail="Result not found.")
        return FileResponse(result, filename=result.name)

    return app


def validate_loopback_host(host: str) -> str:
    """Reject non-loopback bind addresses before starting the API server."""
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The local API may only bind to a loopback address.")
    return host
