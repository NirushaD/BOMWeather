"""Config flow for BOM Weather."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_PRODUCT_ID,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    DEFAULT_NAME,
    DEFAULT_PRODUCT_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

PRODUCT_RE = re.compile(r"^ID[A-Z]\d{5}$")
STATION_RE = re.compile(r"^\d{5}$")


def _schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Return the config flow schema."""
    user_input = user_input or {}
    return vol.Schema(
        {
            vol.Required("name", default=user_input.get("name", DEFAULT_NAME)): str,
            vol.Required(
                CONF_PRODUCT_ID,
                default=user_input.get(CONF_PRODUCT_ID, DEFAULT_PRODUCT_ID),
            ): str,
            vol.Required(CONF_STATION_ID, default=user_input.get(CONF_STATION_ID, "")): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
        }
    )


class BOMWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BOM Weather."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            product_id = user_input[CONF_PRODUCT_ID].strip().upper()
            station_id = user_input[CONF_STATION_ID].strip()
            name = user_input["name"].strip() or DEFAULT_NAME

            if not PRODUCT_RE.match(product_id):
                errors[CONF_PRODUCT_ID] = "invalid_product"
            if not STATION_RE.match(station_id):
                errors[CONF_STATION_ID] = "invalid_station"

            if not errors:
                await self.async_set_unique_id(f"{product_id}_{station_id}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={
                        "name": name,
                        CONF_PRODUCT_ID: product_id,
                        CONF_STATION_ID: station_id,
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )

            user_input = {
                **user_input,
                CONF_PRODUCT_ID: product_id,
                CONF_STATION_ID: station_id,
                "name": name,
            }

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )
