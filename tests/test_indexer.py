import pytest

from app.embeddings.indexer import (
    Progress,
    Row,
    estimate_tokens,
    plan_batches,
    to_vector_literal,
)
from app.embeddings.ratelimit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def limiter(rpm: int, tpm: int, clock: FakeClock) -> RateLimiter:
    return RateLimiter(rpm, tpm, clock=clock.time, sleep=clock.sleep)


class TestRateLimiter:
    def test_requests_within_quota_do_not_wait(self):
        clock = FakeClock()
        rl = limiter(3, 10_000, clock)
        for _ in range(3):
            assert rl.acquire(1_000) == 0
        assert clock.sleeps == []

    def test_fourth_request_in_a_minute_waits_for_the_window(self):
        clock = FakeClock()
        rl = limiter(3, 10_000, clock)
        for _ in range(3):
            rl.acquire(100)
            clock.now += 1
        waited = rl.acquire(100)
        assert waited == pytest.approx(57.05)  # until the first request is 60 s old

    def test_token_budget_is_enforced(self):
        clock = FakeClock()
        rl = limiter(100, 10_000, clock)
        rl.acquire(9_000)
        waited = rl.acquire(2_000)
        assert waited == pytest.approx(60.05)
        assert clock.now >= 60

    def test_a_request_larger_than_the_quota_is_rejected(self):
        with pytest.raises(ValueError):
            limiter(3, 10_000, FakeClock()).acquire(10_001)


def test_token_estimate_errs_on_the_high_side():
    text = "Profitul net al grupului a crescut în exercițiul financiar."  # ~13 real tokens
    assert estimate_tokens(text) >= 15
    assert estimate_tokens("") == 1


def test_batches_respect_text_and_token_limits():
    rows = [Row(i, "x" * 300) for i in range(10)]  # 100 estimated tokens each
    batches = plan_batches(rows, max_texts=4, max_tokens=250)
    assert [len(b) for b in batches] == [2, 2, 2, 2, 2]
    batches = plan_batches(rows, max_texts=3, max_tokens=10_000)
    assert [len(b) for b in batches] == [3, 3, 3, 1]
    assert [r.id for b in batches for r in b] == list(range(10))


def test_a_single_oversized_row_still_gets_its_own_batch():
    batches = plan_batches([Row(1, "x" * 3000)], max_texts=10, max_tokens=100)
    assert [[r.id for r in b] for b in batches] == [[1]]


def test_vector_literal_format():
    assert to_vector_literal([0.5, -0.25, 1.0]) == "[0.5,-0.25,1]"


def test_progress_estimates_remaining_time():
    assert Progress(done=0, total=10, tokens=0, elapsed=0).remaining_seconds is None
    assert Progress(done=2, total=10, tokens=0, elapsed=60).remaining_seconds == 240
