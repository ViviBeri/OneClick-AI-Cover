from pathlib import Path
from threading import Event
from time import monotonic, sleep

import pytest

from oneclick_cover.jobs import JobStatus
from oneclick_cover.runner import LocalJobRunner


def wait_for_status(runner, job_id, expected, timeout=3):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        job = runner.get(job_id)
        if job is not None and job.status is expected:
            return job
        sleep(0.01)
    return runner.get(job_id)


def test_runner_executes_task_and_publishes_progress_and_result(tmp_path):
    runner = LocalJobRunner()
    finished = Event()
    output = tmp_path / "cover.wav"

    def task(progress):
        progress(0.4, "Converting voice")
        output.write_bytes(b"audio")
        finished.set()
        return output

    try:
        job = runner.submit(task)
        assert finished.wait(3)
        result = wait_for_status(runner, job.id, JobStatus.COMPLETED)
        assert result is not None
        assert result.status is JobStatus.COMPLETED
        assert result.progress == 1.0
        assert result.output_path == output
    finally:
        runner.shutdown()


def test_runner_records_task_failure():
    runner = LocalJobRunner()

    def task(progress):
        raise RuntimeError("pipeline failed")

    try:
        job = runner.submit(task)
        result = wait_for_status(runner, job.id, JobStatus.FAILED)
        assert result is not None
        assert result.status is JobStatus.FAILED
        assert result.error == "pipeline failed"
    finally:
        runner.shutdown()


def test_runner_cancels_queued_task_without_starting_it():
    runner = LocalJobRunner()
    started = Event()
    release = Event()

    def blocking_task(progress):
        started.set()
        release.wait(3)
        return "unused.wav"

    try:
        first = runner.submit(blocking_task)
        assert started.wait(3)
        second = runner.submit(lambda progress: "unused.wav")
        assert runner.cancel(second.id) is True
        assert runner.get(second.id).status is JobStatus.CANCELLED
        assert runner.cancel(first.id) is False
    finally:
        release.set()
        runner.shutdown()


def test_runner_rejects_submit_after_shutdown():
    runner = LocalJobRunner()
    runner.shutdown()
    with pytest.raises(RuntimeError, match="shut down"):
        runner.submit(lambda progress: Path("unused.wav"))
