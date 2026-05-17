"""BOM Realtime Weather integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_PRODUCT_ID, CONF_STATION_NAME, CONF_WMO, DOMAIN
from .coordinator import BOMClient, BOMDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.WEATHER, Platform.SENSOR]

type BOMConfigEntry = ConfigEntry[BOMDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: BOMConfigEntry) -> bool:
    """Set up BOM Realtime Weather from a config entry."""
    session = async_get_clientsession(hass)
    client = BOMClient(session, entry.data[CONF_PRODUCT_ID], entry.data[CONF_WMO])
    coordinator = BOMDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    if not entry.data.get(CONF_STATION_NAME) and coordinator.data:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_STATION_NAME: coordinator.data.station_name}
        )

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BOMConfigEntry) -> bool:
    """Unload a BOM Realtime Weather config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
