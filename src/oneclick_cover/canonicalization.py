"""Strict RFC 8785 canonicalization boundary for identity-bearing JSON records."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import rfc8785


class NonAsciiObjectKeyError(ValueError):
    """Raised when an object key violates the repository's ASCII-key policy."""


def _validate_ascii_object_keys(value: Any, path: str = "$") -> None:
    """Reject non-string or non-ASCII object keys before invoking JCS."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError(f"JSON object key at {path} must be a string")
            if not key.isascii():
                raise NonAsciiObjectKeyError(
                    f"JSON object key at {path} must contain ASCII characters only"
                )
            _validate_ascii_object_keys(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_ascii_object_keys(child, f"{path}[{index}]")


def canonicalize(obj: Any) -> bytes:
    """Return RFC 8785 canonical JSON as UTF-8 bytes, without a trailing newline."""
    _validate_ascii_object_keys(obj)
    return rfc8785.dumps(obj)


def hash_canonical(obj: Any) -> str:
    """Return the lowercase SHA-256 digest of canonical JSON bytes."""
    return hashlib.sha256(canonicalize(obj)).hexdigest()


def is_canonicalizable(obj: Any) -> bool:
    """Return whether the object passes the canonicalization boundary."""
    try:
        canonicalize(obj)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
    return True
