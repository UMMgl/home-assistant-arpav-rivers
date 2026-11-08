from __future__ import annotations

from typing import TYPE_CHECKING

from .runtime_const import DEFAULT_PROFILE, PLATFORMS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .types import ArpavRiversConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: ArpavRiversConfigEntry) -> bool:
    from .coordinator import ArpavRiversCoordinator, station_ids_for_profile

    profile = entry.data.get("profile", DEFAULT_PROFILE)
    coordinator = ArpavRiversCoordinator(hass, station_ids_for_profile(profile))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ArpavRiversConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

