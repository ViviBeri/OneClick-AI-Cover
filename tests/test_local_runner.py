from threading import Event
from pathlib import Path

import pytest

from oneclick_cover.jobs import JobStatus
from oneclick_cover.runner import LocalJobRunner


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
        result = runner.get(job.id)
        assert result is not None
        assert result.status is JobStatus.COMPLETED
        assert result.progress == 1.0
        assert result.output_path == output
    finally:
        runner.shutdown()


def test_runner_records_task_failure():
    runner = LocalJobRunner()
    finished = Event()

    def task(progress):
        raise RuntimeError("pipeline failed")

    try:
        job = runner.submit(task)
        for _ in range(300):
            result = runner.get(job.id)
            if result and result.status is JobStatus.FAILED:
                finished.set()
                break
            finished.wait(0.01)
        result = runner.get(job.id)
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
