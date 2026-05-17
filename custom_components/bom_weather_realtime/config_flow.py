"""Config flow for BOM Realtime Weather."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_PRODUCT_ID,
    CONF_STATE,
    CONF_STATION_NAME,
    CONF_WMO,
    DOMAIN,
    STATE_PRODUCTS,
)
from .coordinator import BOMApiError, BOMClient


class BOMRealtimeWeatherConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BOM Realtime Weather."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            state = user_input[CONF_STATE]
            product_id = STATE_PRODUCTS[state]
            wmo = str(user_input[CONF_WMO]).strip()

            await self.async_set_unique_id(f"{product_id}_{wmo}".lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = BOMClient(session, product_id, wmo)
            try:
                observation = await client.async_get_latest_observation()
            except BOMApiError:
                errors["base"] = "cannot_connect"
            else:
                station_name = str(
                    user_input.get(CONF_STATION_NAME) or observation.station_name
                ).strip()
                return self.async_create_entry(
                    title=f"BOM {station_name}",
                    data={
                        CONF_STATE: state,
                        CONF_PRODUCT_ID: product_id,
                        CONF_WMO: wmo,
                        CONF_STATION_NAME: station_name,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_STATE, default="NSW/ACT"): vol.In(STATE_PRODUCTS),
                vol.Required(CONF_WMO): str,
                vol.Optional(CONF_STATION_NAME): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
