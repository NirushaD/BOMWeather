"""Constants for the BOM Realtime Weather integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "bom_weather_realtime"

CONF_STATE = "state"
CONF_WMO = "wmo"
CONF_STATION_NAME = "station_name"
CONF_PRODUCT_ID = "product_id"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=10)
BOM_BASE_URL = "https://reg.bom.gov.au/fwo"

STATE_PRODUCTS: dict[str, str] = {
    "NT": "IDD60910",
    "NSW/ACT": "IDN60910",
    "QLD": "IDQ60910",
    "SA": "IDS60910",
    "TAS": "IDT60910",
    "VIC": "IDV60910",
    "WA": "IDW60910",
}
