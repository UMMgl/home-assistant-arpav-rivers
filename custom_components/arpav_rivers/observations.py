from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class QualityState(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    MISSING = "missing"
    STALE = "stale"
    SENTINEL = "sentinel"
    SOURCE_ERROR = "source_error"


@dataclass(frozen=True, slots=True)
class Observation:
    station_id: str
    station_name: str
    series_id: str
    parameter: str
    sensor_type: str
    unit: str | None
    frequency_minutes: int | None
    observed_at_source: datetime | None
    observed_at_utc: datetime | None
    acquired_at: datetime
    value: float | None
    raw_value: str | None
    quality: QualityState
    source_url: str | None = None
    official_thresholds: tuple[float, ...] = ()

    @property
    def key(self) -> str:
        return f"{self.station_id}:{self.series_id}"


@dataclass(slots=True)
class SeriesSnapshot:
    current: Observation
    last_valid: Observation | None = None
    history: tuple[Observation, ...] = ()
