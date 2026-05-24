"""Constants for the BOM Weather integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry

DOMAIN = "bom_weather"

CONF_PRODUCT_ID = "product_id"
CONF_STATION_ID = "station_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FORECAST_PRODUCT_ID = "forecast_product_id"
CONF_FORECAST_AREA = "forecast_area"

DEFAULT_NAME = "BOM Weather"
DEFAULT_PRODUCT_ID = "IDN60801"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_FORECAST_PRODUCT_ID = ""
DEFAULT_FORECAST_AREA = ""


def entry_value(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Return an option value, falling back to the original config data."""
    return entry.options.get(key, entry.data.get(key, default))
