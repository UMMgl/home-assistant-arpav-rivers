from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import ArpavClient, ArpavSourceError
from .runtime_const import DEFAULT_PROFILE, DOMAIN, PROFILES

_LOGGER = logging.getLogger(__name__)


class ArpavRiversConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _async_validate_connection(self, profile: str) -> None:
        client = ArpavClient(async_get_clientsession(self.hass))
        await client.fetch_station(PROFILES[profile][0])

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._async_validate_connection(user_input["profile"])
            except ArpavSourceError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception validating ARPAV connection")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="HA ARPAV River Level",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("profile", default=DEFAULT_PROFILE): vol.In(sorted(PROFILES))
            }),
            errors=errors,
        )

