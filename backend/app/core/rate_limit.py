from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List
from fastapi import HTTPException, status


class InMemoryRateLimiter:
    def __init__(self):
        self._lock = Lock()
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._last_call: Dict[str, float] = {}

    def check_rate_limit(self, key: str, max_requests: int, window_seconds: float) -> None:
        now = time.time()
        with self._lock:
            timestamps = self._requests[key]
            # Prune expired timestamps
            cutoff = now - window_seconds
            self._requests[key] = [t for t in timestamps if t > cutoff]
            if len(self._requests[key]) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please slow down.",
                )
            self._requests[key].append(now)

    def check_min_interval(self, key: str, min_interval_seconds: float) -> None:
        now = time.time()
        with self._lock:
            last = self._last_call.get(key, 0.0)
            if now - last < min_interval_seconds:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Please wait {int(min_interval_seconds - (now - last)) + 1}s before sending another update.",
                )
            self._last_call[key] = now

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()
            self._last_call.clear()


class LoginLockoutTracker:
    """Tracks failed login attempts per account and per IP with exponential backoff."""

    def __init__(self, max_attempts: int = 5, base_lockout_seconds: float = 30.0, max_lockout_seconds: float = 900.0):
        self._lock = Lock()
        self._failures: Dict[str, int] = defaultdict(int)
        self._locked_until: Dict[str, float] = {}
        self.max_attempts = max_attempts
        self.base_lockout_seconds = base_lockout_seconds
        self.max_lockout_seconds = max_lockout_seconds

    def check_locked(self, key: str) -> None:
        now = time.time()
        with self._lock:
            until = self._locked_until.get(key, 0.0)
            if until > now:
                retry_after = int(until - now) + 1
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed login attempts. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )

    def record_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            self._failures[key] += 1
            count = self._failures[key]
            if count >= self.max_attempts:
                exponent = count - self.max_attempts
                delay = min(self.base_lockout_seconds * (2 ** exponent), self.max_lockout_seconds)
                self._locked_until[key] = now + delay

    def reset_key(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._failures.clear()
            self._locked_until.clear()


sos_rate_limiter = InMemoryRateLimiter()
login_lockout = LoginLockoutTracker()
