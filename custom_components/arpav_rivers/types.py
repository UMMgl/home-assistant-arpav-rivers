from __future__ import annotations

from homeassistant.config_entries import ConfigEntry

from .coordinator import ArpavRiversCoordinator

type ArpavRiversConfigEntry = ConfigEntry[ArpavRiversCoordinator]
