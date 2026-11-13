"""In-memory security primitives for the same-origin browser broker.

These helpers deliberately do not expose or proxy the native API bearer token.
They are building blocks; route integration belongs to the Gradio application.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Callable


@dataclass(frozen=True)
class BrowserSession:
    """Credentials returned once when a browser session is created."""

    session_id: str
    csrf_token: str
    expires_at: float


class BrowserSessionStore:
    """Short-lived, process-local browser sessions with hashed stored secrets."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 1800,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError("Session lifetime must be positive.")
        self._ttl_seconds = float(ttl_seconds)
        self._clock = clock
        self._sessions: dict[str, tuple[str, float]] = {}
        self._lock = RLock()

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def create(self) -> BrowserSession:
        """Create a session and return its cookie and CSRF secrets once."""
        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        expires_at = self._clock() + self._ttl_seconds
        with self._lock:
            self._purge_expired()
            self._sessions[self._digest(session_id)] = (
                self._digest(csrf_token),
                expires_at,
            )
        return BrowserSession(session_id, csrf_token, expires_at)

    def validate(
        self,
        session_id: str | None,
        *,
        csrf_token: str | None = None,
        require_csrf: bool = False,
    ) -> bool:
        """Validate a session and, for mutations, its separate CSRF token."""
        if not session_id or (require_csrf and not csrf_token):
            return False
        key = self._digest(session_id)
        with self._lock:
            record = self._sessions.get(key)
            if record is None:
                return False
            expected_csrf, expires_at = record
            if expires_at <= self._clock():
                self._sessions.pop(key, None)
                return False
            if require_csrf and not hmac.compare_digest(
                expected_csrf, self._digest(csrf_token or "")
            ):
                return False
            return True

    def revoke_all(self) -> None:
        """Invalidate every browser session, for example during app shutdown."""
        with self._lock:
            self._sessions.clear()

    def _purge_expired(self) -> None:
        now = self._clock()
        expired = [
            key for key, (_, expires_at) in self._sessions.items()
            if expires_at <= now
        ]
        for key in expired:
            self._sessions.pop(key, None)


def validate_browser_request_boundary(
    *,
    host: str | None,
    origin: str | None,
    expected_host: str,
    expected_origin: str,
    state_changing: bool,
) -> bool:
    """Require the exact loopback listener and same-origin browser requests.

    Safe requests may omit Origin, as browsers commonly do for same-origin GETs.
    If supplied, Origin must still match. State-changing requests must include it.
    """
    if not host or not hmac.compare_digest(host.lower(), expected_host.lower()):
        return False
    if state_changing and not origin:
        return False
    if origin is not None and not hmac.compare_digest(origin, expected_origin):
        return False
    return True
