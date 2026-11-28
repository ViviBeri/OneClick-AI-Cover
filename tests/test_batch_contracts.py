import hashlib
import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from oneclick_cover import canonicalization
from oneclick_cover.batch_contracts import (
    EngineIdentityMismatch,
    ManifestParseError,
    OutputHashMismatch,
    SelfHashMismatch,
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
    with pytest.raises(EngineIdentityMismatch):
        read_completion_manifest(
            tmp_path, expected_engine_identity="rvc@different-sha"
        )


def test_manifest_rejects_truncation(tmp_path):
    (tmp_path / "one.wav").write_bytes(b"audio")
    write_completion_manifest(
        tmp_path, batch_id="batch-2", engine_identity="rvc@pinned-sha"
    )
    marker = tmp_path / MANIFEST_NAME
    marker.write_bytes(marker.read_bytes()[:20])
    with pytest.raises(ManifestParseError):
        read_completion_manifest(
            tmp_path, expected_engine_identity="rvc@pinned-sha"
        )


def test_manifest_rejects_output_hash_mismatch_and_extra_files(tmp_path):
    (tmp_path / "one.wav").write_bytes(b"original audio")
    write_completion_manifest(
        tmp_path, batch_id="batch-3", engine_identity="rvc@pinned-sha"
    )
    (tmp_path / "one.wav").write_bytes(b"changed audio")
    with pytest.raises(OutputHashMismatch):
        read_completion_manifest(
            tmp_path, expected_engine_identity="rvc@pinned-sha"
        )
    (tmp_path / "one.wav").write_bytes(b"original audio")
    (tmp_path / "extra.wav").write_bytes(b"unlisted audio")
    with pytest.raises(OutputHashMismatch):
        read_completion_manifest(
            tmp_path, expected_engine_identity="rvc@pinned-sha"
        )


def test_manifest_rejects_self_hash_tampering(tmp_path):
    (tmp_path / "one.wav").write_bytes(b"audio")
    write_completion_manifest(
        tmp_path, batch_id="batch-4", engine_identity="rvc@pinned-sha"
    )
    marker = tmp_path / MANIFEST_NAME
    payload = json.loads(marker.read_text(encoding="utf-8"))
    payload["batch_id"] = "tampered"
    marker.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SelfHashMismatch):
        read_completion_manifest(
            tmp_path, expected_engine_identity="rvc@pinned-sha"
        )


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
    staging = tmp_path / ".staging-abandoned"
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
    recent = tmp_path / ".staging-recent"
    recent.mkdir()
    mark_cleanup_pending(recent)

    future = tmp_path / ".staging-future"
    future.mkdir()
    mark_cleanup_pending(future)
    future_time = datetime.now(timezone.utc) + timedelta(hours=2)
    os.utime(future, (future_time.timestamp(), future_time.timestamp()))

    unmarked = tmp_path / ".staging-unmarked"
    unmarked.mkdir()
    (unmarked / "partial.wav").write_bytes(b"partial")

    completed = tmp_path / ".staging-completed"
    completed.mkdir()
    (completed / "track.wav").write_bytes(b"audio")
    write_completion_manifest(
        completed, batch_id="done", engine_identity="rvc@pinned-sha"
    )
    mark_cleanup_pending(completed)
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



def test_staging_sweep_removes_corrupt_completion_marker(tmp_path):
    staging = tmp_path / ".staging-corrupt"
    staging.mkdir()
    (staging / "partial.wav").write_bytes(b"partial")
    (staging / MANIFEST_NAME).write_text("{broken", encoding="utf-8")
    mark_cleanup_pending(staging)
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    os.utime(staging, (old.timestamp(), old.timestamp()))
    removed = sweep_stale_staging(
        tmp_path, older_than=datetime.now(timezone.utc) - timedelta(hours=24)
    )
    assert removed == (staging,)
    assert not staging.exists()



def test_manifest_rejects_forged_canonicalization_identifier(tmp_path):
    (tmp_path / "one.wav").write_bytes(b"audio")
    write_completion_manifest(
        tmp_path, batch_id="forged-id", engine_identity="rvc@pinned-sha"
    )
    marker = tmp_path / MANIFEST_NAME
    payload = json.loads(marker.read_text(encoding="utf-8"))
    payload["canonicalization"] = "json.dumps"
    marker.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ManifestParseError, match="RFC 8785"):
        read_completion_manifest(
            tmp_path, expected_engine_identity="rvc@pinned-sha"
        )

def test_legacy_json_dumps_manifest_is_rejected_by_jcs_reader(tmp_path):
    (tmp_path / "legacy.wav").write_bytes(b"legacy audio")
    payload = {
        "version": 1,
        "batch_id": "legacy",
        "engine_identity": "rvc@pinned-sha",
        "files": [
            {
                "name": "legacy.wav",
                "sha256": hashlib.sha256(b"legacy audio").hexdigest(),
            }
        ],
    }
    payload["self_sha256"] = __import__("hashlib").sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    (tmp_path / MANIFEST_NAME).write_text(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestParseError, match="RFC 8785"):
        read_completion_manifest(
            tmp_path, expected_engine_identity="rvc@pinned-sha"
        )


def test_manifest_writer_and_reader_use_shared_canonicalizer(monkeypatch, tmp_path):
    (tmp_path / "one.wav").write_bytes(b"audio")
    canonical_calls = []
    original = canonicalization.canonicalize

    def recording_canonicalize(value):
        encoded = original(value)
        canonical_calls.append(encoded)
        return encoded

    monkeypatch.setattr(canonicalization, "canonicalize", recording_canonicalize)
    write_completion_manifest(
        tmp_path, batch_id="shared", engine_identity="rvc@pinned-sha"
    )

    marker_bytes = (tmp_path / MANIFEST_NAME).read_bytes()
    assert marker_bytes.endswith(bytes([10]))
    written_payload_bytes = marker_bytes[:-1]
    parsed = json.loads(written_payload_bytes.decode("utf-8"))
    original_self_hash = parsed.pop("self_sha256")

    # Writer call 1 hashes the payload before self_sha256 is inserted.
    # Writer call 2 serializes the complete payload. Reader call 3 rebuilds
    # the payload after parsing and removing self_sha256.
    assert len(canonical_calls) == 3
    assert canonical_calls[1] == written_payload_bytes
    assert canonical_calls[0] == canonical_calls[2]
    assert hashlib.sha256(canonical_calls[2]).hexdigest() == original_self_hash

    read_completion_manifest(
        tmp_path, expected_engine_identity="rvc@pinned-sha"
    )
