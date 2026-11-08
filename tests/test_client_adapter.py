from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast

from aiohttp import ClientSession

from custom_components.arpav_rivers.client import ArpavClient
from custom_components.arpav_rivers.observations import QualityState
from veneto_hydro_client import ArpavObservation, ArpavSeriesSnapshot, SourceQuality


def _session() -> ClientSession:
    return cast(ClientSession, object())


class _StubHydroClient:
    def __init__(self, arpav_station) -> None:
        self._arpav_station = arpav_station

    async def fetch_arpav_station(self, _station_id: str):
        return self._arpav_station


def test_arpav_adapter_preserves_source_semantics() -> None:
    now = datetime(2026, 8, 22, 6, 0, tzinfo=UTC)
    source = ArpavObservation(
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
        quality=SourceQuality.VALID,
        source_url="https://example.invalid/0287.xml",
        official_thresholds=(5.5, 6.5, 7.0),
    )
    client = ArpavClient(_session())
    client._client = cast(
        object,
        _StubHydroClient([ArpavSeriesSnapshot(source, source, (source,))]),
    )

    result = asyncio.run(client.fetch_station("0287"))

    assert len(result) == 1
    assert result[0].current.key == "0287:300005755"
    assert result[0].current.quality == QualityState.VALID
    assert result[0].current.official_thresholds == (5.5, 6.5, 7.0)
    assert result[0].last_valid is not None
    assert result[0].last_valid.value == 1.5

