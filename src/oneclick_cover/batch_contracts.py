"""Transactional batch publication contracts for M2.2a.

A batch is complete only when its self-validating manifest is durable and
matches every file in the published directory.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from oneclick_cover.canonicalization import canonicalize

MANIFEST_NAME = "_COMPLETE.json"
STAGING_PREFIX = ".staging-"
MANIFEST_VERSION = 1
MANIFEST_CANONICALIZATION = "RFC8785"
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class BatchProgressEvent:
    batch_id: str
    track_index: int
    track_total: int
    track_filename: str
    event: Literal["started", "completed", "failed", "cancelled"]
    timestamp_ms: int
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.batch_id or not self.track_filename:
            raise ValueError("Batch progress identity fields must not be empty.")
        if self.track_total < 1 or not 1 <= self.track_index <= self.track_total:
            raise ValueError("Batch progress track position is invalid.")
        if self.timestamp_ms < 0:
            raise ValueError("Batch progress timestamp must be non-negative.")
        if self.event == "failed" and not self.error_code:
            raise ValueError("Failed progress events require an error code.")
        if self.event != "failed" and self.error_code is not None:
            raise ValueError("Only failed progress events may include an error code.")


class ManifestValidationError(ValueError):
    """Base class for invalid or incompatible completion manifests."""


class ManifestParseError(ManifestValidationError):
    """Raised when a manifest is malformed or uses an unsupported format."""


class SelfHashMismatch(ManifestValidationError):
    """Raised when the manifest's own canonical digest does not match."""


class OutputHashMismatch(ManifestValidationError):
    """Raised when output membership or a file digest does not match."""


class EngineIdentityMismatch(ManifestValidationError):
    """Raised when the manifest belongs to a different conversion engine."""


@dataclass(frozen=True)
class BatchManifest:
    batch_id: str
    engine_identity: str
    files: tuple[tuple[str, str], ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(directory: Path) -> None:
    """Sync directory metadata where supported.

    Windows does not provide a supported directory-handle FlushFileBuffers
    operation. Files are flushed individually before publication; Windows
    directory metadata durability relies on filesystem journaling.
    """
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def write_completion_manifest(
    directory: Path,
    *,
    batch_id: str,
    engine_identity: str,
) -> BatchManifest:
    """Durably publish the manifest last; caller owns lifecycle synchronization."""
    root = Path(directory)
    if not root.is_dir() or not batch_id or not engine_identity:
        raise ValueError("A directory, batch ID, and engine identity are required.")
    if (root / MANIFEST_NAME).exists():
        raise FileExistsError(f"Completion manifest already exists: {root / MANIFEST_NAME}")
    entries = sorted(
        (path.name, _sha256(path))
        for path in root.iterdir()
        if path.is_file() and path.name != MANIFEST_NAME
    )
    if not entries:
        raise ValueError("A completed batch must contain at least one output file.")
    if any(not _HEX_SHA256.fullmatch(digest) for _, digest in entries):
        raise ValueError("Invalid output digest.")
    payload: dict[str, object] = {
        "version": MANIFEST_VERSION,
        "canonicalization": MANIFEST_CANONICALIZATION,
        "batch_id": batch_id,
        "engine_identity": engine_identity,
        "files": [{"name": name, "sha256": digest} for name, digest in entries],
    }
    payload["self_sha256"] = hashlib.sha256(canonicalize(payload)).hexdigest()
    encoded = canonicalize(payload) + bytes([10])
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".complete-", suffix=".tmp", dir=root
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, root / MANIFEST_NAME)
        _fsync_directory(root)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return BatchManifest(batch_id, engine_identity, tuple(entries))


def read_completion_manifest(
    directory: Path, *, expected_engine_identity: str
) -> BatchManifest:
    """Load and validate a JCS-authenticated manifest or raise a typed error."""
    root = Path(directory)
    marker = root / MANIFEST_NAME
    try:
        raw = marker.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ManifestParseError(f"Cannot read a valid completion manifest: {error}") from error

    if not isinstance(payload, dict):
        raise ManifestParseError("Completion manifest must be a JSON object.")
    if payload.get("canonicalization") != MANIFEST_CANONICALIZATION:
        raise ManifestParseError("Completion manifest is not marked as RFC 8785 canonical JSON.")

    self_digest = payload.pop("self_sha256", None)
    if not isinstance(self_digest, str) or not _HEX_SHA256.fullmatch(self_digest):
        raise ManifestParseError("Completion manifest self_sha256 is missing or malformed.")
    try:
        canonical_payload = canonicalize(payload)
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ManifestParseError(f"Completion manifest cannot be canonicalized: {error}") from error
    if hashlib.sha256(canonical_payload).hexdigest() != self_digest:
        raise SelfHashMismatch("Completion manifest self_sha256 does not match.")

    if payload.get("version") != MANIFEST_VERSION:
        raise ManifestParseError("Unsupported completion manifest version.")
    batch_id = payload.get("batch_id")
    engine_identity = payload.get("engine_identity")
    files = payload.get("files")
    if not isinstance(batch_id, str) or not batch_id:
        raise ManifestParseError("Completion manifest batch_id is invalid.")
    if engine_identity != expected_engine_identity:
        raise EngineIdentityMismatch("Completion manifest engine identity does not match.")
    if not isinstance(files, list):
        raise ManifestParseError("Completion manifest files must be a list.")

    listed: list[tuple[str, str]] = []
    for item in files:
        if not isinstance(item, dict):
            raise ManifestParseError("Completion manifest file entries must be objects.")
        name, digest = item.get("name"), item.get("sha256")
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or name in {"", MANIFEST_NAME, ".cleanup_pending"}
            or not isinstance(digest, str)
            or not _HEX_SHA256.fullmatch(digest)
        ):
            raise ManifestParseError("Completion manifest contains an invalid file entry.")
        listed.append((name, digest))
    if not listed or len({name for name, _ in listed}) != len(listed):
        raise ManifestParseError("Completion manifest file list is empty or duplicated.")

    actual = {
        path.name for path in root.iterdir()
        if path.is_file() and path.name not in {MANIFEST_NAME, ".cleanup_pending"}
    }
    if actual != {name for name, _ in listed}:
        raise OutputHashMismatch("Output file membership does not match the completion manifest.")
    for name, digest in listed:
        path = root / name
        if not path.is_file() or _sha256(path) != digest:
            raise OutputHashMismatch(f"Output hash does not match for {name}.")
    return BatchManifest(batch_id, engine_identity, tuple(sorted(listed)))

def new_batch_id() -> str:
    return uuid4().hex


def mark_cleanup_pending(staging_directory: Path) -> None:
    """Persist a sweepable marker without touching user-selected destinations."""
    marker = Path(staging_directory) / ".cleanup_pending"
    with marker.open("w", encoding="utf-8") as stream:
        stream.write(datetime.now(timezone.utc).isoformat())
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_directory(Path(staging_directory))


def _has_valid_completion_manifest(directory: Path) -> bool:
    """Protect only batches whose completion manifest and outputs validate."""
    try:
        payload = json.loads((directory / MANIFEST_NAME).read_text(encoding="utf-8"))
        engine_identity = payload.get("engine_identity") if isinstance(payload, dict) else None
        return (
            isinstance(engine_identity, str)
            and bool(engine_identity)
            and read_completion_manifest(
                directory, expected_engine_identity=engine_identity
            ) is not None
        )
    except (OSError, UnicodeError, ManifestValidationError, TypeError):
        return False


def sweep_stale_staging(
    staging_root: Path,
    *,
    older_than: datetime | None = None,
) -> tuple[Path, ...]:
    """Remove only old, app-owned staging directories explicitly marked pending."""
    root = Path(staging_root)
    cutoff = older_than or (datetime.now(timezone.utc) - timedelta(hours=24))
    if not root.is_dir():
        return ()
    removed: list[Path] = []
    for candidate in root.iterdir():
        if (
            not candidate.is_dir()
            or not candidate.name.startswith(STAGING_PREFIX)
            or not (candidate / ".cleanup_pending").is_file()
        ):
            continue
        try:
            modified = datetime.fromtimestamp(
                candidate.stat().st_mtime, tz=timezone.utc
            )
            if modified >= cutoff:
                continue
            # A valid manifest protects published output; corrupt markers do not.
            if _has_valid_completion_manifest(candidate):
                continue
            shutil.rmtree(candidate)
            removed.append(candidate)
        except OSError as error:
            logging.getLogger(__name__).warning(
                "Could not sweep stale staging directory %s: %s", candidate, error
            )
    return tuple(removed)
