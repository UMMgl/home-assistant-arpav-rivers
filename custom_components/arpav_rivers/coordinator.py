from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TypeVar

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import ArpavClient
from .health import SourceHealth
from .observations import Observation, QualityState, SeriesSnapshot
from .runtime_const import DEFAULT_PROFILE, DEFAULT_UPDATE_INTERVAL, PROFILES

_LOGGER = logging.getLogger(__name__)
T = TypeVar("T")


class SourceBackoffError(RuntimeError):
    pass


@dataclass(slots=True)
class CoordinatorPayload:
    series: dict[str, SeriesSnapshot] = field(default_factory=dict)
    source_errors: dict[str, str] = field(default_factory=dict)
    source_health: dict[str, dict[str, object]] = field(default_factory=dict)
    next_poll_at: datetime | None = None
    last_successful_acquisition: dict[str, datetime] = field(default_factory=dict)


class ArpavRiversCoordinator(DataUpdateCoordinator[CoordinatorPayload]):
    """Coordinate public ARPAV river-level observations."""

    def __init__(self, hass: HomeAssistant, station_ids: tuple[str, ...]) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="HA ARPAV River Level",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.station_ids = station_ids
        self.client = ArpavClient(async_get_clientsession(hass))
        self._last_valid: dict[str, Observation] = {}
        self._source_health: dict[str, SourceHealth] = {}
        self._previous = CoordinatorPayload()

    async def _guarded_fetch(self, source_key: str, fetcher: Callable[[], Awaitable[T]]) -> T:
        health = self._source_health.setdefault(source_key, SourceHealth())
        now = datetime.now(UTC)
        if not health.can_attempt(now):
            until = health.next_retry_at.isoformat() if health.next_retry_at else "later"
            raise SourceBackoffError(f"{source_key} circuit backoff until {until}")
        health.record_attempt(now)
        try:
            result = await fetcher()
        except Exception as err:
            health.record_failure(
                err,
                now=datetime.now(UTC),
                base_backoff_seconds=int(DEFAULT_UPDATE_INTERVAL.total_seconds()),
                max_backoff_seconds=int(DEFAULT_UPDATE_INTERVAL.total_seconds() * 6),
            )
            raise
        health.record_success(datetime.now(UTC))
        return result

    def _snapshot_source_health(self, payload: CoordinatorPayload) -> None:
        payload.next_poll_at = datetime.now(UTC) + DEFAULT_UPDATE_INTERVAL
        payload.source_health = {
            key: health.attributes(next_poll_at=payload.next_poll_at)
            for key, health in self._source_health.items()
        }

    def _remember_last_valid(self, obs: Observation | None) -> None:
        if obs is None or obs.quality != QualityState.VALID or obs.value is None:
            return
        previous = self._last_valid.get(obs.key)
        if (
            previous is None
            or previous.observed_at_utc is None
            or (
                obs.observed_at_utc is not None
                and obs.observed_at_utc >= previous.observed_at_utc
            )
        ):
            self._last_valid[obs.key] = obs

    async def _async_update_data(self) -> CoordinatorPayload:
        payload = CoordinatorPayload(
            last_successful_acquisition=dict(self._previous.last_successful_acquisition)
        )
        semaphore = asyncio.Semaphore(5)

        async def load(station_id: str) -> tuple[str, list[SeriesSnapshot] | Exception]:
            async with semaphore:
                try:
                    result = await self._guarded_fetch(
                        station_id, lambda: self.client.fetch_station(station_id)
                    )
                    return station_id, result
                # Isolate station failures while preserving successful stations.
                except Exception as err:  # noqa: BLE001
                    return station_id, err

        results = await asyncio.gather(*(load(station_id) for station_id in self.station_ids))
        success_count = 0
        for station_id, result in results:
            if isinstance(result, Exception):
                payload.source_errors[station_id] = str(result)
                for key, snapshot in self._previous.series.items():
                    if snapshot.current.station_id == station_id:
                        payload.series[key] = snapshot
                continue

            success_count += 1
            payload.last_successful_acquisition[station_id] = datetime.now(UTC)
            for source_snapshot in result:
                obs = source_snapshot.current
                if obs.sensor_type != "LIVIDRO":
                    continue
                self._remember_last_valid(source_snapshot.last_valid)
                self._remember_last_valid(obs)
                payload.series[obs.key] = SeriesSnapshot(
                    current=obs,
                    last_valid=self._last_valid.get(obs.key),
                    history=source_snapshot.history,
                )

        self._snapshot_source_health(payload)
        if success_count == 0 and not self._previous.series:
            raise UpdateFailed("All ARPAV station requests failed")
        self._previous = payload
        return payload


def station_ids_for_profile(profile: str) -> tuple[str, ...]:
    return PROFILES.get(profile, PROFILES[DEFAULT_PROFILE])
