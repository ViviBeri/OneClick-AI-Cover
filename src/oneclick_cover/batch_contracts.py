"""Transactional batch publication contracts for M2.2a.

A batch is complete only when its self-validating manifest is durable and
matches every file in the published directory.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

MANIFEST_NAME = "_COMPLETE.json"
STAGING_PREFIX = ".oneclick-batch-"
MANIFEST_VERSION = 1
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


def _canonical_json(value: dict[str, object]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _fsync_directory(directory: Path) -> None:
    """Flush directory metadata on POSIX and Windows before publishing state."""
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.restype = ctypes.c_void_p\n        create_file.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]\n        kernel32.FlushFileBuffers.argtypes = [ctypes.c_void_p]\n        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = create_file(
            str(directory), 0x80000000, 0x00000007, None, 3, 0x02000000, None
        )
        invalid = ctypes.c_void_p(-1).value
        if handle == invalid:
            raise OSError(ctypes.get_last_error(), "Unable to open directory for flush")
        try:
            if not kernel32.FlushFileBuffers(handle):
                raise OSError(ctypes.get_last_error(), "Unable to flush directory metadata")
        finally:
            kernel32.CloseHandle(handle)
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
        "batch_id": batch_id,
        "engine_identity": engine_identity,
        "files": [{"name": name, "sha256": digest} for name, digest in entries],
    }
    payload["self_sha256"] = hashlib.sha256(_canonical_json(payload)).hexdigest()
    encoded = _canonical_json(payload) + b"\\n"
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
) -> BatchManifest | None:
    """Return None for every absent, malformed, stale, or mismatched batch."""
    root = Path(directory)
    marker = root / MANIFEST_NAME
    try:
        raw = marker.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict):
            return None
        self_digest = payload.pop("self_sha256")
        if not isinstance(self_digest, str) or not _HEX_SHA256.fullmatch(self_digest):
            return None
        if hashlib.sha256(_canonical_json(payload)).hexdigest() != self_digest:
            return None
        if payload.get("version") != MANIFEST_VERSION:
            return None
        batch_id = payload.get("batch_id")
        engine_identity = payload.get("engine_identity")
        files = payload.get("files")
        if not isinstance(batch_id, str) or not batch_id:
            return None
        if engine_identity != expected_engine_identity or not isinstance(files, list):
            return None
        listed: list[tuple[str, str]] = []
        for item in files:
            if not isinstance(item, dict):
                return None
            name, digest = item.get("name"), item.get("sha256")
            if (
                not isinstance(name, str)
                or Path(name).name != name
                or name in {"", MANIFEST_NAME}
                or not isinstance(digest, str)
                or not _HEX_SHA256.fullmatch(digest)
            ):
                return None
            listed.append((name, digest))
        if not listed or len({name for name, _ in listed}) != len(listed):
            return None
        actual = {
            path.name for path in root.iterdir()
            if path.is_file() and path.name != MANIFEST_NAME
        }
        if actual != {name for name, _ in listed}:
            return None
        for name, digest in listed:
            path = root / name
            if not path.is_file() or _sha256(path) != digest:
                return None
        return BatchManifest(batch_id, engine_identity, tuple(sorted(listed)))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


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
        modified = datetime.fromtimestamp(
            candidate.stat().st_mtime, tz=timezone.utc
        )
        if modified >= cutoff:
            continue
        # A valid completion marker makes this directory non-disposable.
        if (candidate / MANIFEST_NAME).exists():
            continue
        shutil.rmtree(candidate)
        removed.append(candidate)
    return tuple(removed)
