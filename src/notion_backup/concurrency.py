# ABOUTME: Thread-safe rate limiting for Notion API calls.
# ABOUTME: Provides RateLimiter to throttle requests to stay within API limits.

import threading
import time


class RateLimiter:
    """Thread-safe rate limiter using simple timing.

    Ensures requests don't exceed a specified rate by blocking callers
    until enough time has passed since the last request.
    """

    def __init__(self, calls_per_second: float = 2.5):
        """Initialize rate limiter.

        Args:
            calls_per_second: Maximum requests per second. Default 2.5 leaves
                headroom below Notion's 3/sec limit.
        """
        self._min_interval = 1.0 / calls_per_second
        self._lock = threading.Lock()
        self._last_call = 0.0

    def acquire(self) -> None:
        """Block until a request slot is available.

        Thread-safe: multiple threads can call this concurrently and each
        will be properly throttled.
        """
        with self._lock:
            now = time.monotonic()
            wait_time = self._last_call + self._min_interval - now
            if wait_time > 0:
                time.sleep(wait_time)
            self._last_call = time.monotonic()
