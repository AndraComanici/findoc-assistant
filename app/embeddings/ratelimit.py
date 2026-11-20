"""Stay under a requests-per-minute and tokens-per-minute quota by waiting before each call."""

import time
from collections import deque
from collections.abc import Callable

WINDOW_SECONDS = 60.0


class RateLimiter:
    """A sliding one-minute window: before a request, wait until it fits in both budgets."""

    def __init__(
        self,
        requests_per_minute: int,
        tokens_per_minute: int,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if requests_per_minute < 1 or tokens_per_minute < 1:
            raise ValueError("rate limits must be positive")
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self._clock = clock
        self._sleep = sleep
        self._sent: deque[tuple[float, int]] = deque()  # (time, tokens) of recent requests

    def acquire(self, tokens: int) -> float:
        """Block until a request of this size is allowed, then record it. Returns seconds waited."""
        if tokens > self.tokens_per_minute:
            raise ValueError(f"a request of {tokens} tokens can never fit in the per-minute quota")
        waited = 0.0
        while True:
            now = self._clock()
            while self._sent and now - self._sent[0][0] >= WINDOW_SECONDS:
                self._sent.popleft()
            used = sum(t for _, t in self._sent)
            if (
                len(self._sent) < self.requests_per_minute
                and used + tokens <= self.tokens_per_minute
            ):
                self._sent.append((now, tokens))
                return waited
            # Wait until the oldest request leaves the window, then check again.
            delay = WINDOW_SECONDS - (now - self._sent[0][0]) + 0.05
            self._sleep(delay)
            waited += delay
