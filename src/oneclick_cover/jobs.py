"""Thread-safe in-memory state for local processing jobs.

This module stores job metadata only. Audio and model files remain on disk in
the local application directories; this registry does not expose a network API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import RLock
from uuid import uuid4


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL = {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}


@dataclass(frozen=True)
class ProcessingJob:
    id: str
    status: JobStatus
    progress: float
    message: str
    created_at: datetime
    updated_at: datetime
    output_path: Path | None = None
    error: str | None = None


class LocalJobStore:
    """Small process-local job registry with validated state transitions."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._jobs: dict[str, ProcessingJob] = {}

    def create(self, message: str = "Waiting to start") -> ProcessingJob:
        now = datetime.now(timezone.utc)
        job = ProcessingJob(
            id=uuid4().hex,
            status=JobStatus.QUEUED,
            progress=0.0,
            message=message,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> ProcessingJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> tuple[ProcessingJob, ...]:
        with self._lock:
            return tuple(sorted(self._jobs.values(), key=lambda job: job.created_at))

    def mark_running(self, job_id: str, message: str = "Starting") -> ProcessingJob:
        return self._replace(job_id, {JobStatus.QUEUED}, status=JobStatus.RUNNING, message=message)

    def update_progress(self, job_id: str, progress: float, message: str) -> ProcessingJob:
        value = float(progress)
        if not 0.0 <= value <= 1.0:
            raise ValueError("Job progress must be between 0.0 and 1.0.")
        return self._replace(
            job_id,
            {JobStatus.RUNNING},
            progress=value,
            message=str(message),
        )

    def complete(self, job_id: str, output_path: str | Path) -> ProcessingJob:
        path = Path(output_path)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("A completed job must reference an existing, non-empty output file.")
        return self._replace(
            job_id,
            {JobStatus.RUNNING},
            status=JobStatus.COMPLETED,
            progress=1.0,
            message="Completed",
            output_path=path,
            error=None,
        )

    def fail(self, job_id: str, error: str) -> ProcessingJob:
        if not str(error).strip():
            raise ValueError("A failed job must include an error message.")
        return self._replace(
            job_id,
            {JobStatus.QUEUED, JobStatus.RUNNING},
            status=JobStatus.FAILED,
            message="Failed",
            error=str(error),
        )

    def cancel(self, job_id: str) -> ProcessingJob:
        return self._replace(
            job_id,
            {JobStatus.QUEUED},
            status=JobStatus.CANCELLED,
            message="Cancelled before processing started",
        )

    def _replace(self, job_id: str, allowed: set[JobStatus], **changes) -> ProcessingJob:
        with self._lock:
            current = self._jobs.get(job_id)
            if current is None:
                raise KeyError(f"Unknown processing job: {job_id}")
            if current.status not in allowed or current.status in _TERMINAL:
                raise ValueError(f"Cannot update a {current.status.value} job.")
            updated = ProcessingJob(
                **{
                    **current.__dict__,
                    **changes,
                    "updated_at": datetime.now(timezone.utc),
                }
            )
            self._jobs[job_id] = updated
            return updated
