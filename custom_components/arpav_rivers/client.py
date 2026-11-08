from __future__ import annotations

from aiohttp import ClientSession

from veneto_hydro_client import (
    ArpavObservation,
    ArpavSeriesSnapshot,
    RetryPolicy,
    SourceQuality,
    VenetoHydroClient,
    VenetoHydroSourceError,
)

from .observations import Observation, QualityState, SeriesSnapshot
from .runtime_const import DEFAULT_REQUEST_TIMEOUT


class ArpavSourceError(RuntimeError):
    """Raised when the public ARPAV source cannot be read safely."""


def _quality(value: SourceQuality) -> QualityState:
    return QualityState(value.value)


def _observation(value: ArpavObservation) -> Observation:
    return Observation(
        station_id=value.station_id,
        station_name=value.station_name,
        series_id=value.series_id,
        parameter=value.parameter,
        sensor_type=value.sensor_type,
        unit=value.unit,
        frequency_minutes=value.frequency_minutes,
        observed_at_source=value.observed_at_source,
        observed_at_utc=value.observed_at_utc,
        acquired_at=value.acquired_at,
        value=value.value,
        raw_value=value.raw_value,
        quality=_quality(value.quality),
        source_url=value.source_url,
        official_thresholds=value.official_thresholds,
    )


def _snapshot(value: ArpavSeriesSnapshot) -> SeriesSnapshot:
    return SeriesSnapshot(
        current=_observation(value.current),
        last_valid=_observation(value.last_valid) if value.last_valid else None,
        history=tuple(_observation(item) for item in value.history),
    )


class ArpavClient:
    """Home Assistant adapter over the public ARPAV transport client."""

    def __init__(
        self,
        session: ClientSession,
        *,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._client = VenetoHydroClient(
            session,
            request_timeout_seconds=float(request_timeout),
            retry_policy=retry_policy or RetryPolicy(),
        )

    async def fetch_station(self, station_id: str) -> list[SeriesSnapshot]:
        try:
            result = await self._client.fetch_arpav_station(station_id)
        except VenetoHydroSourceError as err:
            raise ArpavSourceError(str(err)) from err
        return [_snapshot(item) for item in result]

