from datetime import UTC, datetime
from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.arpav_rivers.coordinator import (
    CoordinatorPayload,
)
from custom_components.arpav_rivers.observations import (
    Observation,
    QualityState,
    SeriesSnapshot,
)
from custom_components.arpav_rivers.runtime_const import DOMAIN


async def test_config_entry_sets_up_hydrometric_sensor(
    hass,
    enable_custom_integrations,
):
    now = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)
    observation = Observation(
        station_id="0287",
        station_name="Bacchiglione a Bovolenta",
        series_id="300005755",
        parameter="Livello idrometrico 1",
        sensor_type="LIVIDRO",
        unit="m",
        frequency_minutes=10,
        observed_at_source=now,
        observed_at_utc=now,
        acquired_at=now,
        value=1.5,
        raw_value="1.50",
        quality=QualityState.VALID,
        source_url="https://example.invalid/0287.xml",
        official_thresholds=(5.5, 6.5, 7.0),
    )
    payload = CoordinatorPayload(
        series={observation.key: SeriesSnapshot(observation, observation)},
        last_successful_acquisition={"0287": now},
        source_health={
            "0287": {
                "source_status": "healthy",
                "consecutive_failures": 0,
                "last_attempt": now.isoformat(),
                "last_successful_update": now.isoformat(),
                "next_retry_at": None,
                "next_poll_at": now.isoformat(),
                "last_source_error": None,
            }
        },
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        title="HA ARPAV River Level",
        data={"profile": "bacchiglione"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.arpav_rivers.coordinator.ArpavRiversCoordinator._async_update_data",
        return_value=payload,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    matching = [
        state for state in hass.states.async_all()
        if state.attributes.get("series_id") == "300005755"
    ]
    assert len(matching) == 1
    assert matching[0].state == "1.5"
    assert matching[0].attributes["quality"] == "valid"
    assert matching[0].attributes["source_status"] == "healthy"
    assert matching[0].attributes["official_thresholds"] == [5.5, 6.5, 7.0]

