from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.arpav_rivers.client import ArpavSourceError
from custom_components.arpav_rivers.runtime_const import DOMAIN


async def _start_user_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )


async def test_user_flow_success(hass, enable_custom_integrations) -> None:
    with (
        patch(
            "custom_components.arpav_rivers.config_flow.ArpavClient.fetch_station",
            new=AsyncMock(return_value=[]),
        ) as fetch_station,
        patch(
            "custom_components.arpav_rivers.async_setup_entry",
            new=AsyncMock(return_value=True),
        ),
    ):
        result = await _start_user_flow(hass)
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"profile": "bacchiglione"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "HA ARPAV River Level"
    assert result["data"] == {"profile": "bacchiglione"}
    fetch_station.assert_awaited_once_with("0276")


async def test_user_flow_rejects_duplicate(hass, enable_custom_integrations) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        title="HA ARPAV River Level",
        data={"profile": "bacchiglione"},
    )
    entry.add_to_hass(hass)

    result = await _start_user_flow(hass)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_user_flow_reports_cannot_connect(hass, enable_custom_integrations) -> None:
    with patch(
        "custom_components.arpav_rivers.config_flow.ArpavClient.fetch_station",
        new=AsyncMock(side_effect=ArpavSourceError("offline")),
    ):
        result = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"profile": "bacchiglione"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_reports_unknown_error(hass, enable_custom_integrations) -> None:
    with patch(
        "custom_components.arpav_rivers.config_flow.ArpavClient.fetch_station",
        new=AsyncMock(side_effect=RuntimeError("unexpected")),
    ):
        result = await _start_user_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"profile": "bacchiglione"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}
