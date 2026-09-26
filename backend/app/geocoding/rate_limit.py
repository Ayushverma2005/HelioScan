"""Reusable application-level spacing limiter for outbound provider calls."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

Clock = Callable[[], float]
Sleeper = Callable[[float], None]


class ApplicationRateLimiter:
    """Serialize calls and enforce a minimum interval between their starts."""

    def __init__(
        self,
        min_interval_seconds: float = 1.0,
        *,
        clock: Clock = time.monotonic,
        sleep: Sleeper = time.sleep,
    ) -> None:
        if min_interval_seconds <= 0:
            raise ValueError("min_interval_seconds must be greater than zero")
        self._min_interval_seconds = min_interval_seconds
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next_slot = 0.0

    @contextmanager
    def slot(self) -> Iterator[None]:
        """Wait for and hold one outbound request slot."""
        with self._lock:
            now = self._clock()
            slot = max(now, self._next_slot)
            delay = slot - now
            if delay > 0:
                self._sleep(delay)
            self._next_slot = slot + self._min_interval_seconds
            yield
