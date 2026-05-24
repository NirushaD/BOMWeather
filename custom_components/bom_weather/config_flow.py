"""Config flow for BOM Weather."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_PRODUCT_ID,
    CONF_FORECAST_AREA,
    CONF_FORECAST_PRODUCT_ID,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    DEFAULT_FORECAST_AREA,
    DEFAULT_FORECAST_PRODUCT_ID,
    DEFAULT_NAME,
    DEFAULT_PRODUCT_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    entry_value,
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
                CONF_FORECAST_PRODUCT_ID,
                default=user_input.get(
                    CONF_FORECAST_PRODUCT_ID,
                    DEFAULT_FORECAST_PRODUCT_ID,
                ),
            ): str,
            vol.Optional(
                CONF_FORECAST_AREA,
                default=user_input.get(CONF_FORECAST_AREA, DEFAULT_FORECAST_AREA),
            ): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=5, max=120)),
        }
    )


def _options_schema(
    config_entry: ConfigEntry,
    user_input: dict[str, Any] | None = None,
) -> vol.Schema:
    """Return the options flow schema."""
    user_input = user_input or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_PRODUCT_ID,
                default=user_input.get(
                    CONF_PRODUCT_ID,
                    entry_value(config_entry, CONF_PRODUCT_ID, DEFAULT_PRODUCT_ID),
                ),
            ): str,
            vol.Required(
                CONF_STATION_ID,
                default=user_input.get(
                    CONF_STATION_ID,
                    entry_value(config_entry, CONF_STATION_ID, ""),
                ),
            ): str,
            vol.Optional(
                CONF_FORECAST_PRODUCT_ID,
                default=user_input.get(
                    CONF_FORECAST_PRODUCT_ID,
                    entry_value(
                        config_entry,
                        CONF_FORECAST_PRODUCT_ID,
                        DEFAULT_FORECAST_PRODUCT_ID,
                    ),
                ),
            ): str,
            vol.Optional(
                CONF_FORECAST_AREA,
                default=user_input.get(
                    CONF_FORECAST_AREA,
                    entry_value(
                        config_entry,
                        CONF_FORECAST_AREA,
                        DEFAULT_FORECAST_AREA,
                    ),
                ),
            ): str,
        }
    )


def _validate_location_input(user_input: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    """Validate and normalise location and forecast settings."""
    errors: dict[str, str] = {}

    product_id = user_input[CONF_PRODUCT_ID].strip().upper()
    station_id = user_input[CONF_STATION_ID].strip()
    forecast_product_id = user_input[CONF_FORECAST_PRODUCT_ID].strip().upper()
    forecast_area = user_input[CONF_FORECAST_AREA].strip()

    if not PRODUCT_RE.match(product_id):
        errors[CONF_PRODUCT_ID] = "invalid_product"
    if not STATION_RE.match(station_id):
        errors[CONF_STATION_ID] = "invalid_station"
    if forecast_product_id and not PRODUCT_RE.match(forecast_product_id):
        errors[CONF_FORECAST_PRODUCT_ID] = "invalid_product"
    if forecast_product_id and not forecast_area:
        errors[CONF_FORECAST_AREA] = "forecast_area_required"
    if forecast_area and not forecast_product_id:
        errors[CONF_FORECAST_PRODUCT_ID] = "forecast_product_required"

    return errors, {
        CONF_PRODUCT_ID: product_id,
        CONF_STATION_ID: station_id,
        CONF_FORECAST_PRODUCT_ID: forecast_product_id,
        CONF_FORECAST_AREA: forecast_area,
    }


class BOMWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BOM Weather."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> BOMWeatherOptionsFlow:
        """Create the options flow."""
        return BOMWeatherOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, location_data = _validate_location_input(user_input)
            product_id = location_data[CONF_PRODUCT_ID]
            station_id = location_data[CONF_STATION_ID]
            name = user_input["name"].strip() or DEFAULT_NAME

            if not errors:
                await self.async_set_unique_id(f"{product_id}_{station_id}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=name,
                    data={
                        "name": name,
                        **location_data,
                        CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    },
                )

            user_input = {
                **user_input,
                **location_data,
                "name": name,
            }

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input),
            errors=errors,
        )


class BOMWeatherOptionsFlow(config_entries.OptionsFlow):
    """Handle BOM Weather options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialise options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage BOM Weather options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            errors, location_data = _validate_location_input(user_input)

            if not errors:
                return self.async_create_entry(
                    title="",
                    data={
                        **self.config_entry.options,
                        **location_data,
                    },
                )

            user_input = {
                **user_input,
                **location_data,
            }

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(self.config_entry, user_input),
            errors=errors,
        )
