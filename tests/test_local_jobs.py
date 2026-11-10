from pathlib import Path

import pytest

from oneclick_cover.jobs import JobStatus, LocalJobStore
from oneclick_cover.pipeline import run_cover_pipeline


def test_pipeline_runs_without_gradio_and_reports_progress(tmp_path):
    source = tmp_path / "song.wav"
    model = tmp_path / "voice.pth"
    source.write_bytes(b"source")
    model.write_bytes(b"model")
    events = []

    def write(path):
        path.write_bytes(b"audio")
        return path

    output = run_cover_pipeline(
        source,
        model,
        2,
        1.0,
        0.8,
        "WAV",
        tmp_path,
        progress=lambda fraction, message: events.append((fraction, message)),
        validate_audio_fn=lambda path: None,
        validate_model_fn=lambda path: None,
        transcode_fn=lambda source, destination: write(destination),
        separate_fn=lambda wav, folder, **kwargs: (write(folder / "vocals.wav"), write(folder / "instrumental.wav")),
        convert_fn=lambda vocals, converted, model_path, pitch: write(converted),
        match_sample_rate_fn=lambda converted, instrumental, destination: converted,
        mix_fn=lambda vocal, instrumental, output, vocal_gain, instrumental_gain: write(output),
    )

    assert output.is_file()
    assert events[0] == (0.1, "Preparing audio")
    assert events[-1] == (1.0, "Done")
    assert [fraction for fraction, _ in events] == sorted(fraction for fraction, _ in events)


def test_pipeline_removes_partial_job_directory_after_failure(tmp_path):
    source = tmp_path / "song.wav"
    model = tmp_path / "voice.pth"
    source.write_bytes(b"source")
    model.write_bytes(b"model")

    def fail(*args, **kwargs):
        raise RuntimeError("separation failed")

    with pytest.raises(RuntimeError, match="separation failed"):
        run_cover_pipeline(
            source, model, 0, 1.0, 0.8, "WAV", tmp_path,
            validate_audio_fn=lambda path: None,
            validate_model_fn=lambda path: None,
            transcode_fn=lambda source, destination: destination.write_bytes(b"audio"),
            separate_fn=fail,
        )

    assert not list(tmp_path.glob("cover_*"))


def test_job_store_tracks_valid_state_transitions(tmp_path):
    store = LocalJobStore()
    queued = store.create()
    assert queued.status is JobStatus.QUEUED

    running = store.mark_running(queued.id)
    assert running.status is JobStatus.RUNNING

    updated = store.update_progress(queued.id, 0.45, "Separating vocals")
    assert updated.progress == 0.45
    assert updated.message == "Separating vocals"

    output = tmp_path / "cover.wav"
    output.write_bytes(b"audio")
    completed = store.complete(queued.id, output)
    assert completed.status is JobStatus.COMPLETED
    assert completed.output_path == output
    assert store.get(queued.id) == completed


def test_job_store_rejects_invalid_transitions_and_progress():
    store = LocalJobStore()
    queued = store.create()

    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        store.update_progress(queued.id, 1.2, "Invalid")

    cancelled = store.cancel(queued.id)
    assert cancelled.status is JobStatus.CANCELLED
    with pytest.raises(ValueError, match="Cannot update a cancelled job"):
        store.mark_running(queued.id)

    running = store.mark_running(store.create().id)
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        store.update_progress(running.id, -0.1, "Invalid")


def test_job_store_records_failures():
    store = LocalJobStore()
    job = store.create()
    failed = store.fail(job.id, "RVC failed")
    assert failed.status is JobStatus.FAILED
    assert failed.error == "RVC failed"
    with pytest.raises(ValueError, match="Cannot update a failed job"):
        store.mark_running(job.id)
