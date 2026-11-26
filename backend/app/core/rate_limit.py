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


sos_rate_limiter = InMemoryRateLimiter()
