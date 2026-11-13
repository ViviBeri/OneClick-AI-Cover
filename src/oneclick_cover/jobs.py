"""SQLite-backed job metadata for local processing.

Only job metadata is stored here. Audio and model files remain in managed
local folders and are never copied into the database.
"""

from __future__ import annotations

import sqlite3
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
    """Thread-safe SQLite job registry with validated state transitions.

    Passing no database path creates an isolated in-memory database, which is
    useful for tests. The application supplies a persistent path.
    """

    def __init__(self, database_path: str | Path | None = None) -> None:
        self._lock = RLock()
        self.database_path = Path(database_path).resolve() if database_path else None
        if self.database_path is not None:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection_target = str(self.database_path)
        else:
            connection_target = ":memory:"
        self._connection = sqlite3.connect(
            connection_target, check_same_thread=False, timeout=10.0
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        if self.database_path is not None:
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = NORMAL")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                progress REAL NOT NULL CHECK (progress >= 0.0 AND progress <= 1.0),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                output_path TEXT,
                error TEXT
            )
            """
        )
        self._connection.execute(
            """
            UPDATE jobs
            SET status = ?, message = ?, error = ?, updated_at = ?
            WHERE status IN (?, ?)
            """,
            (
                JobStatus.FAILED.value,
                "Interrupted by application shutdown",
                "The application closed before this job finished.",
                datetime.now(timezone.utc).isoformat(),
                JobStatus.QUEUED.value,
                JobStatus.RUNNING.value,
            ),
        )
        self._connection.commit()

    def close(self) -> None:
        """Close the database connection."""
        with self._lock:
            self._connection.close()

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
            self._connection.execute(
                """
                INSERT INTO jobs
                (id, status, progress, message, created_at, updated_at, output_path, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id, job.status.value, job.progress, job.message,
                    job.created_at.isoformat(), job.updated_at.isoformat(), None, None,
                ),
            )
            self._connection.commit()
        return job

    def get(self, job_id: str) -> ProcessingJob | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE id = ?", (job_id,)
            ).fetchone()
            return self._from_row(row) if row else None

    def list(self) -> tuple[ProcessingJob, ...]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM jobs ORDER BY created_at, id"
            ).fetchall()
            return tuple(self._from_row(row) for row in rows)

    def mark_running(self, job_id: str, message: str = "Starting") -> ProcessingJob:
        return self._replace(
            job_id, {JobStatus.QUEUED}, status=JobStatus.RUNNING, message=message
        )

    def update_progress(self, job_id: str, progress: float, message: str) -> ProcessingJob:
        value = float(progress)
        if not 0.0 <= value <= 1.0:
            raise ValueError("Job progress must be between 0.0 and 1.0.")
        return self._replace(
            job_id, {JobStatus.RUNNING}, progress=value, message=str(message)
        )

    def complete(self, job_id: str, output_path: str | Path) -> ProcessingJob:
        path = Path(output_path).resolve()
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
            current = self.get(job_id)
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
            self._connection.execute(
                """
                UPDATE jobs
                SET status = ?, progress = ?, message = ?, updated_at = ?,
                    output_path = ?, error = ?
                WHERE id = ?
                """,
                (
                    updated.status.value, updated.progress, updated.message,
                    updated.updated_at.isoformat(),
                    str(updated.output_path) if updated.output_path else None,
                    updated.error, updated.id,
                ),
            )
            self._connection.commit()
            return updated

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ProcessingJob:
        record = dict(row)
        return ProcessingJob(
            id=record["id"],
            status=JobStatus(record["status"]),
            progress=float(record["progress"]),
            message=record["message"],
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
            output_path=Path(record["output_path"]) if record["output_path"] else None,
            error=record["error"],
        )
