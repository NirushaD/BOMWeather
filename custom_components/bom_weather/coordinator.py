"""Data coordinator for BOM Weather."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BOMObservation, BOMWeatherClient, BOMWeatherError
from .const import (
    CONF_PRODUCT_ID,
    CONF_FORECAST_AREA,
    CONF_FORECAST_PRODUCT_ID,
    CONF_SCAN_INTERVAL,
    CONF_STATION_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    entry_value,
)

_LOGGER = logging.getLogger(__name__)


class BOMWeatherCoordinator(DataUpdateCoordinator[BOMObservation]):
    """Fetch BOM observations on a schedule."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator."""
        self.config_entry = entry
        self.client = BOMWeatherClient(
            async_get_clientsession(hass),
            entry_value(entry, CONF_PRODUCT_ID),
            entry_value(entry, CONF_STATION_ID),
            entry_value(entry, CONF_FORECAST_PRODUCT_ID),
            entry_value(entry, CONF_FORECAST_AREA),
        )

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=entry_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> BOMObservation:
        """Fetch data from BOM."""
        try:
            return await self.client.async_get_weather_data()
        except BOMWeatherError as err:
            raise UpdateFailed(str(err)) from err
