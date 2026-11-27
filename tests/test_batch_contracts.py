import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from oneclick_cover.batch_contracts import (
    MANIFEST_NAME,
    BatchProgressEvent,
    mark_cleanup_pending,
    read_completion_manifest,
    sweep_stale_staging,
    write_completion_manifest,
)


def test_manifest_round_trip_validates_membership_hashes_and_engine(tmp_path):
    (tmp_path / "one.wav").write_bytes(b"first audio")
    (tmp_path / "two.wav").write_bytes(b"second audio")
    written = write_completion_manifest(
        tmp_path, batch_id="batch-1", engine_identity="rvc@pinned-sha"
    )
    loaded = read_completion_manifest(
        tmp_path, expected_engine_identity="rvc@pinned-sha"
    )
    assert loaded == written
    assert read_completion_manifest(
        tmp_path, expected_engine_identity="rvc@different-sha"
    ) is None


def test_manifest_rejects_truncation(tmp_path):
    (tmp_path / "one.wav").write_bytes(b"audio")
    write_completion_manifest(
        tmp_path, batch_id="batch-2", engine_identity="rvc@pinned-sha"
    )
    marker = tmp_path / MANIFEST_NAME
    marker.write_bytes(marker.read_bytes()[:20])
    assert read_completion_manifest(
        tmp_path, expected_engine_identity="rvc@pinned-sha"
    ) is None


def test_manifest_rejects_output_hash_mismatch_and_extra_files(tmp_path):
    (tmp_path / "one.wav").write_bytes(b"original audio")
    write_completion_manifest(
        tmp_path, batch_id="batch-3", engine_identity="rvc@pinned-sha"
    )
    (tmp_path / "one.wav").write_bytes(b"changed audio")
    assert read_completion_manifest(
        tmp_path, expected_engine_identity="rvc@pinned-sha"
    ) is None
    (tmp_path / "one.wav").write_bytes(b"original audio")
    (tmp_path / "extra.wav").write_bytes(b"unlisted audio")
    assert read_completion_manifest(
        tmp_path, expected_engine_identity="rvc@pinned-sha"
    ) is None


def test_manifest_rejects_self_hash_tampering(tmp_path):
    (tmp_path / "one.wav").write_bytes(b"audio")
    write_completion_manifest(
        tmp_path, batch_id="batch-4", engine_identity="rvc@pinned-sha"
    )
    marker = tmp_path / MANIFEST_NAME
    payload = json.loads(marker.read_text(encoding="utf-8"))
    payload["batch_id"] = "tampered"
    marker.write_text(json.dumps(payload), encoding="utf-8")
    assert read_completion_manifest(
        tmp_path, expected_engine_identity="rvc@pinned-sha"
    ) is None


def test_progress_event_schema_validates_track_and_error_contract():
    event = BatchProgressEvent(
        batch_id="batch-5",
        track_index=1,
        track_total=2,
        track_filename="song.wav",
        event="started",
        timestamp_ms=1234,
    )
    assert event.event == "started"
    with pytest.raises(ValueError, match="error code"):
        BatchProgressEvent(
            batch_id="batch-5",
            track_index=1,
            track_total=2,
            track_filename="song.wav",
            event="failed",
            timestamp_ms=1234,
        )


def test_cleanup_pending_staging_is_removed_only_after_24_hours(tmp_path):
    staging = tmp_path / ".oneclick-batch-abandoned"
    staging.mkdir()
    (staging / "partial.wav").write_bytes(b"partial")
    mark_cleanup_pending(staging)
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    os.utime(staging, (old.timestamp(), old.timestamp()))
    removed = sweep_stale_staging(
        tmp_path, older_than=datetime.now(timezone.utc) - timedelta(hours=24)
    )
    assert removed == (staging,)
    assert not staging.exists()


def test_staging_sweep_preserves_recent_unmarked_and_completed_directories(tmp_path):
    recent = tmp_path / ".oneclick-batch-recent"
    recent.mkdir()
    mark_cleanup_pending(recent)

    future = tmp_path / ".oneclick-batch-future"
    future.mkdir()
    mark_cleanup_pending(future)
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    os.utime(future, (future_time.timestamp(), future_time.timestamp()))

    unmarked = tmp_path / ".oneclick-batch-unmarked"
    unmarked.mkdir()
    (unmarked / "partial.wav").write_bytes(b"partial")

    completed = tmp_path / ".oneclick-batch-completed"
    completed.mkdir()
    (completed / "track.wav").write_bytes(b"audio")
    write_completion_manifest(
        completed, batch_id="done", engine_identity="rvc@pinned-sha"
    )
    completed_time = datetime.now(timezone.utc) - timedelta(hours=48)
    os.utime(completed, (completed_time.timestamp(), completed_time.timestamp()))

    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    removed = sweep_stale_staging(tmp_path, older_than=cutoff)

    assert removed == ()
    assert recent.exists()
    assert future.exists()
    assert unmarked.exists()
    assert completed.exists()
    assert read_completion_manifest(
        completed, expected_engine_identity="rvc@pinned-sha"
    ) is not None
