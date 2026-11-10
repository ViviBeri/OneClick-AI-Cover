"""Single-worker background execution for local cover jobs."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from typing import Callable

from oneclick_cover.jobs import JobStatus, LocalJobStore, ProcessingJob

JobTask = Callable[[Callable[[float, str], None]], str | Path]


class LocalJobRunner:
    """Run one local processing task at a time and publish job state."""

    def __init__(self, store: LocalJobStore | None = None) -> None:
        self.store = store or LocalJobStore()
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="oneclick-cover",
        )
        self._lock = RLock()
        self._futures: dict[str, Future[None]] = {}
        self._closed = False

    def submit(self, task: JobTask) -> ProcessingJob:
        """Queue a task that receives a progress callback and returns its output path."""
        with self._lock:
            if self._closed:
                raise RuntimeError("The local job runner is shut down.")
            job = self.store.create()
            future = self._executor.submit(self._run, job.id, task)
            self._futures[job.id] = future
            return job

    def get(self, job_id: str) -> ProcessingJob | None:
        return self.store.get(job_id)

    def list(self) -> tuple[ProcessingJob, ...]:
        return self.store.list()

    def cancel(self, job_id: str) -> bool:
        """Cancel a queued task; running Demucs/RVC subprocesses are not interrupted."""
        with self._lock:
            job = self.store.get(job_id)
            if job is None:
                raise KeyError(f"Unknown processing job: {job_id}")
            if job.status is not JobStatus.QUEUED:
                return False
            future = self._futures.get(job_id)
            if future is None or not future.cancel():
                return False
            self.store.cancel(job_id)
            return True

    def shutdown(self, wait: bool = True) -> None:
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait, cancel_futures=False)

    def _run(self, job_id: str, task: JobTask) -> None:
        with self._lock:
            job = self.store.get(job_id)
            if job is None or job.status is not JobStatus.QUEUED:
                return
            self.store.mark_running(job_id)

        def report(fraction: float, message: str) -> None:
            self.store.update_progress(job_id, fraction, message)

        try:
            output = task(report)
            self.store.complete(job_id, output)
        except Exception as exc:
            current = self.store.get(job_id)
            if current is not None and current.status in {JobStatus.QUEUED, JobStatus.RUNNING}:
                self.store.fail(job_id, str(exc) or exc.__class__.__name__)
