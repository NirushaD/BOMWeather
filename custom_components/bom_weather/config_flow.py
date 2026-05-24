"""Config flow for BOM Weather."""

from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithReload
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

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
from .discovery import (
    BOMDiscoveryError,
    FORECAST_PRODUCTS,
    OBSERVATION_REGIONS,
    async_get_forecast_areas,
    async_get_observation_stations,
    infer_region,
    split_option_value,
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


def _region_schema(default_region: str) -> vol.Schema:
    """Return the BOM region options schema."""
    return vol.Schema(
        {
            vol.Required(
                "region",
                default=default_region,
            ): vol.In(
                {
                    region: region_data[0]
                    for region, region_data in OBSERVATION_REGIONS.items()
                }
            ),
        }
    )


def _dropdown_options_schema(
    station_options: dict[str, str],
    forecast_options: dict[str, str],
    default_station: str,
    default_forecast: str,
) -> vol.Schema:
    """Return dropdown options for station and forecast area."""
    schema: dict[Any, Any] = {
        vol.Required(
            "station",
            default=default_station,
        ): vol.In(station_options),
    }

    if forecast_options:
        schema[
            vol.Optional(
                "forecast",
                default=default_forecast,
            )
        ] = vol.In({"": "No forecast"} | forecast_options)

    return vol.Schema(schema)


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
        return BOMWeatherOptionsFlow()

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


class BOMWeatherOptionsFlow(OptionsFlowWithReload):
    """Handle BOM Weather options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage BOM Weather options."""
        if user_input is not None:
            self._region = user_input["region"]
            return await self.async_step_location()

        return self.async_show_form(
            step_id="init",
            data_schema=_region_schema(
                infer_region(
                    entry_value(
                        self.config_entry,
                        CONF_PRODUCT_ID,
                        DEFAULT_PRODUCT_ID,
                    )
                )
            ),
        )

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage station and forecast options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            product_id, station_id = split_option_value(user_input["station"])
            forecast_product_id = ""
            forecast_area = ""
            if forecast_value := user_input.get("forecast"):
                forecast_product_id, forecast_area = split_option_value(forecast_value)

            return self.async_create_entry(
                title="",
                data={
                    **self.config_entry.options,
                    CONF_PRODUCT_ID: product_id,
                    CONF_STATION_ID: station_id,
                    CONF_FORECAST_PRODUCT_ID: forecast_product_id,
                    CONF_FORECAST_AREA: forecast_area,
                },
            )

        try:
            session = async_get_clientsession(self.hass)
            stations = await async_get_observation_stations(session, self._region)
            forecast_areas = await async_get_forecast_areas(session, self._region)
        except BOMDiscoveryError:
            return await self.async_step_manual()

        station_options = {
            station.option_value: station.option_label for station in stations
        }
        forecast_options = {
            forecast_area.option_value: forecast_area.option_label
            for forecast_area in forecast_areas
        }
        default_station = _default_station_option(
            station_options,
            entry_value(self.config_entry, CONF_PRODUCT_ID, DEFAULT_PRODUCT_ID),
            entry_value(self.config_entry, CONF_STATION_ID, ""),
        )
        default_forecast = _default_forecast_option(
            forecast_options,
            entry_value(
                self.config_entry,
                CONF_FORECAST_PRODUCT_ID,
                FORECAST_PRODUCTS.get(self._region, ""),
            ),
            entry_value(self.config_entry, CONF_FORECAST_AREA, ""),
        )

        return self.async_show_form(
            step_id="location",
            data_schema=_dropdown_options_schema(
                station_options,
                forecast_options,
                default_station,
                default_forecast,
            ),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options with manual fields when BOM discovery is unavailable."""
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
            step_id="manual",
            data_schema=_options_schema(self.config_entry, user_input),
            errors=errors,
        )


def _default_station_option(
    station_options: dict[str, str],
    product_id: str,
    station_id: str,
) -> str:
    """Return the default station select value."""
    value = f"{product_id}|{station_id}"
    if value in station_options:
        return value
    return next(iter(station_options))


def _default_forecast_option(
    forecast_options: dict[str, str],
    product_id: str,
    forecast_area: str,
) -> str:
    """Return the default forecast select value."""
    value = f"{product_id}|{forecast_area}"
    if value in forecast_options:
        return value
    return ""
