from datetime import UTC, datetime, timedelta

from custom_components.arpav_rivers.health import SourceHealth, SourceStatus


def test_success_resets_failures_and_backoff() -> None:
    health = SourceHealth()
    now = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)
    health.record_failure(
        "timeout",
        now=now,
        backoff_after_failures=1,
        base_backoff_seconds=600,
        max_backoff_seconds=3600,
    )
    assert health.status == SourceStatus.BACKOFF
    health.record_success(now + timedelta(minutes=1))
    assert health.status == SourceStatus.HEALTHY
    assert health.consecutive_failures == 0
    assert health.next_retry_at is None


def test_backoff_is_exponential_and_bounded() -> None:
    health = SourceHealth()
    now = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)
    for index in range(5):
        health.record_failure(
            f"failure-{index}",
            now=now,
            backoff_after_failures=1,
            base_backoff_seconds=600,
            max_backoff_seconds=3600,
        )
    assert health.status == SourceStatus.BACKOFF
    assert health.next_retry_at == now + timedelta(seconds=3600)


def test_circuit_skips_until_retry_time_then_degrades_for_probe() -> None:
    health = SourceHealth()
    now = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)
    health.record_failure(
        "timeout",
        now=now,
        backoff_after_failures=1,
        base_backoff_seconds=600,
        max_backoff_seconds=3600,
    )
    assert not health.can_attempt(now + timedelta(minutes=5))
    assert health.can_attempt(now + timedelta(minutes=10))
    assert health.status == SourceStatus.DEGRADED


def test_first_failure_is_degraded_and_attempt_time_is_utc() -> None:
    health = SourceHealth()
    naive = datetime(2026, 8, 22, 6, 0, tzinfo=UTC).replace(tzinfo=None)
    assert health.can_attempt()
    health.record_attempt(naive)
    health.record_failure("offline", now=naive)
    assert health.status == SourceStatus.DEGRADED
    assert health.next_retry_at is None
    attributes = health.attributes(next_poll_at=naive)
    assert attributes["last_attempt"] == "2026-08-22T06:00:00+00:00"
    assert attributes["next_poll_at"] == "2026-08-22T06:00:00+00:00"
