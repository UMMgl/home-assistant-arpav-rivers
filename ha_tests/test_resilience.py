from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.arpav_rivers.client import ArpavClient, ArpavSourceError
from custom_components.arpav_rivers.coordinator import (
    ArpavRiversCoordinator,
    CoordinatorPayload,
    SourceBackoffError,
    station_ids_for_profile,
)
from custom_components.arpav_rivers.health import SourceHealth, SourceStatus
from custom_components.arpav_rivers.observations import Observation, QualityState, SeriesSnapshot
from custom_components.arpav_rivers.runtime_const import DEFAULT_PROFILE, PROFILES
from custom_components.arpav_rivers.sensor import ArpavObservationSensor
from veneto_hydro_client import VenetoHydroSourceError


def observation(station="0287", **changes):
    now = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)
    return replace(Observation(
        station_id=station, station_name="Synthetic station", series_id="level",
        parameter="River level", sensor_type="LIVIDRO", unit="m",
        frequency_minutes=10, observed_at_source=now, observed_at_utc=now,
        acquired_at=now, value=1.5, raw_value="1.50", quality=QualityState.VALID,
    ), **changes)


async def test_station_failure_preserves_history_then_recovers(hass):
    coordinator = ArpavRiversCoordinator(hass, ("0287", "0276"))
    old = observation()
    other = observation("0276")
    coordinator.client.fetch_station = AsyncMock(side_effect=[
        [SeriesSnapshot(old, old)], [SeriesSnapshot(other, other)],
        ArpavSourceError("offline"), [SeriesSnapshot(other, other)],
        [SeriesSnapshot(replace(old, value=2.0), old)], [SeriesSnapshot(other, other)],
    ])
    first = await coordinator._async_update_data()
    failed = await coordinator._async_update_data()
    assert failed.series[old.key] == first.series[old.key]
    assert failed.last_successful_acquisition["0287"] == first.last_successful_acquisition["0287"]
    assert failed.source_errors == {"0287": "offline"}
    assert failed.source_health["0287"]["source_status"] == "degraded"
    recovered = await coordinator._async_update_data()
    assert not recovered.source_errors
    assert recovered.series[old.key].current.value == 2.0
    assert recovered.source_health["0287"]["consecutive_failures"] == 0


async def test_total_outage_blocks_initial_setup_but_retains_previous_data(hass):
    coordinator = ArpavRiversCoordinator(hass, ("0287",))
    coordinator.client.fetch_station = AsyncMock(side_effect=ArpavSourceError("offline"))
    with pytest.raises(UpdateFailed, match="All ARPAV"):
        await coordinator._async_update_data()
    old = observation()
    coordinator._previous = CoordinatorPayload(series={old.key: SeriesSnapshot(old, old)})
    data = await coordinator._async_update_data()
    assert data.series[old.key].current == old
    assert data.source_errors == {"0287": "offline"}


async def test_circuit_backoff_skips_network_until_recovery(hass):
    coordinator = ArpavRiversCoordinator(hass, ("0287",))
    fetch = AsyncMock(return_value=[])
    coordinator._source_health["0287"] = SourceHealth(
        status=SourceStatus.BACKOFF,
        next_retry_at=datetime.now(UTC) + timedelta(hours=1),
    )
    with pytest.raises(SourceBackoffError):
        await coordinator._guarded_fetch("0287", fetch)
    fetch.assert_not_awaited()
    coordinator._source_health["0287"].next_retry_at = datetime.now(UTC) - timedelta(seconds=1)
    assert await coordinator._guarded_fetch("0287", fetch) == []
    assert coordinator._source_health["0287"].status == SourceStatus.HEALTHY


async def test_non_hydrometric_and_invalid_samples_cannot_replace_last_valid(hass):
    coordinator = ArpavRiversCoordinator(hass, ("0287",))
    valid = observation()
    older = replace(valid, value=0.5, observed_at_utc=valid.observed_at_utc - timedelta(hours=1))
    sentinel = replace(valid, quality=QualityState.SENTINEL, value=None)
    rain = replace(valid, series_id="rain", sensor_type="PREC")
    coordinator._remember_last_valid(None)
    coordinator._remember_last_valid(sentinel)
    coordinator._remember_last_valid(valid)
    coordinator._remember_last_valid(older)
    coordinator.client.fetch_station = AsyncMock(return_value=[
        SeriesSnapshot(sentinel, older, (older, sentinel)), SeriesSnapshot(rain, rain),
    ])
    data = await coordinator._async_update_data()
    assert set(data.series) == {valid.key}
    assert data.series[valid.key].last_valid == valid
    assert data.series[valid.key].current.value is None
    assert data.series[valid.key].history == (older, sentinel)


async def test_sensor_reports_missing_invalid_stale_and_source_failure(hass):
    coordinator = ArpavRiversCoordinator(hass, ("0287",))
    valid = observation()
    coordinator.async_set_updated_data(CoordinatorPayload(series={valid.key: SeriesSnapshot(valid)}))
    sensor = ArpavObservationSensor(coordinator, valid.key, SeriesSnapshot(valid))
    assert sensor.available and sensor.native_value == 1.5
    invalid = replace(valid, quality=QualityState.SENTINEL, value=None)
    coordinator.async_set_updated_data(CoordinatorPayload(series={valid.key: SeriesSnapshot(invalid, valid)}))
    assert not sensor.available and sensor.native_value is None
    assert sensor.extra_state_attributes["last_valid_value"] == 1.5
    stale = replace(valid, quality=QualityState.STALE, observed_at_source=None, observed_at_utc=None)
    coordinator.async_set_updated_data(CoordinatorPayload(series={valid.key: SeriesSnapshot(stale)}))
    assert sensor.available and sensor.native_value == 1.5
    coordinator.data.source_errors["0287"] = "offline"
    assert not sensor.available and sensor.native_value is None
    assert sensor.extra_state_attributes["quality"] == "source_error"
    coordinator.async_set_updated_data(CoordinatorPayload())
    assert not sensor.available and sensor.native_value is None
    assert sensor.extra_state_attributes == {"quality": "source_error"}


async def test_adapter_translates_transport_errors(hass):
    client = ArpavClient(coordinator_session(hass))
    with (
        patch.object(type(client._client), "fetch_arpav_station", new=AsyncMock(side_effect=VenetoHydroSourceError("offline"))),
        pytest.raises(ArpavSourceError, match="offline"),
    ):
        await client.fetch_station("0287")


def coordinator_session(hass):
    from homeassistant.helpers.aiohttp_client import async_get_clientsession
    return async_get_clientsession(hass)


def test_unknown_profile_uses_documented_default():
    assert station_ids_for_profile("unknown") == PROFILES[DEFAULT_PROFILE]
    assert station_ids_for_profile("piave") == PROFILES["piave"]
