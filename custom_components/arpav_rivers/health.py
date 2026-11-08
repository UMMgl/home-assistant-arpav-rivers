from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class SourceStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    BACKOFF = "backoff"


@dataclass(slots=True)
class SourceHealth:
    status: SourceStatus = SourceStatus.HEALTHY
    consecutive_failures: int = 0
    last_attempt: datetime | None = None
    last_successful_update: datetime | None = None
    next_retry_at: datetime | None = None
    last_error: str | None = None

    def can_attempt(self, now: datetime | None = None) -> bool:
        now = _utc(now)
        if self.status != SourceStatus.BACKOFF or self.next_retry_at is None:
            return True
        if now >= self.next_retry_at:
            self.status = SourceStatus.DEGRADED
            self.next_retry_at = None
            return True
        return False

    def record_attempt(self, now: datetime | None = None) -> None:
        self.last_attempt = _utc(now)

    def record_success(self, now: datetime | None = None) -> None:
        now = _utc(now)
        self.status = SourceStatus.HEALTHY
        self.consecutive_failures = 0
        self.last_successful_update = now
        self.next_retry_at = None
        self.last_error = None

    def record_failure(
        self,
        error: Exception | str,
        *,
        now: datetime | None = None,
        backoff_after_failures: int = 3,
        base_backoff_seconds: int = 30,
        max_backoff_seconds: int = 300,
    ) -> None:
        now = _utc(now)
        self.consecutive_failures += 1
        self.last_error = str(error)
        if self.consecutive_failures < backoff_after_failures:
            self.status = SourceStatus.DEGRADED
            self.next_retry_at = None
            return
        exponent = self.consecutive_failures - backoff_after_failures
        delay = min(max_backoff_seconds, base_backoff_seconds * (2**exponent))
        self.status = SourceStatus.BACKOFF
        self.next_retry_at = now + timedelta(seconds=delay)

    def attributes(self, *, next_poll_at: datetime | None = None) -> dict[str, object]:
        return {
            "source_status": self.status.value,
            "consecutive_failures": self.consecutive_failures,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "last_successful_update": self.last_successful_update.isoformat() if self.last_successful_update else None,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "next_poll_at": _utc(next_poll_at).isoformat() if next_poll_at else None,
            "last_source_error": self.last_error,
        }


def _utc(value: datetime | None) -> datetime:
    value = value or datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
