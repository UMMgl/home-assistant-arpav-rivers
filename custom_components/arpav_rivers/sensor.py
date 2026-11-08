from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ArpavRiversCoordinator
from .observations import QualityState, SeriesSnapshot
from .runtime_const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[ArpavRiversCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ArpavObservationSensor(coordinator, key, snapshot)
        for key, snapshot in coordinator.data.series.items()
    )


def _source_health(coordinator: ArpavRiversCoordinator, source_key: str) -> dict[str, Any]:
    return dict(coordinator.data.source_health.get(source_key, {}))


class ArpavObservationSensor(CoordinatorEntity[ArpavRiversCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ArpavRiversCoordinator,
        key: str,
        snapshot: SeriesSnapshot,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        obs = snapshot.current
        self.entity_description = SensorEntityDescription(
            key=key,
            name=obs.parameter,
            native_unit_of_measurement=obs.unit,
        )
        self._attr_unique_id = f"arpav_{obs.station_id}_{obs.series_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, obs.station_id)},
            "name": obs.station_name,
            "manufacturer": "ARPAV",
            "model": "Meteo-Idro station",
        }

    @property
    def _snapshot(self) -> SeriesSnapshot | None:
        return self.coordinator.data.series.get(self._key)

    @property
    def _source_error(self) -> str | None:
        snapshot = self._snapshot
        return None if snapshot is None else self.coordinator.data.source_errors.get(snapshot.current.station_id)

    @property
    def available(self) -> bool:
        snapshot = self._snapshot
        return (
            super().available
            and snapshot is not None
            and self._source_error is None
            and snapshot.current.quality in {QualityState.VALID, QualityState.STALE}
        )

    @property
    def native_value(self) -> float | None:
        snapshot = self._snapshot
        if snapshot is None or self._source_error is not None:
            return None
        if snapshot.current.quality not in {QualityState.VALID, QualityState.STALE}:
            return None
        return snapshot.current.value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        snapshot = self._snapshot
        if snapshot is None:
            return {"quality": QualityState.SOURCE_ERROR.value}
        obs = snapshot.current
        last_success = self.coordinator.data.last_successful_acquisition.get(obs.station_id)
        return {
            "quality": QualityState.SOURCE_ERROR.value if self._source_error else obs.quality.value,
            "observed_at_source": obs.observed_at_source.isoformat() if obs.observed_at_source else None,
            "observed_at_utc": obs.observed_at_utc.isoformat() if obs.observed_at_utc else None,
            "acquired_at": obs.acquired_at.isoformat(),
            "frequency_minutes": obs.frequency_minutes,
            "series_id": obs.series_id,
            "source_url": obs.source_url,
            "official_thresholds": list(obs.official_thresholds),
            "last_valid_value": snapshot.last_valid.value if snapshot.last_valid else None,
            "last_valid_at_utc": (
                snapshot.last_valid.observed_at_utc.isoformat()
                if snapshot.last_valid and snapshot.last_valid.observed_at_utc
                else None
            ),
            "last_successful_acquisition": last_success.isoformat() if last_success else None,
            **_source_health(self.coordinator, obs.station_id),
        }
