"""Weather platform for BOM Weather."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.components.weather import WeatherEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PRODUCT_ID, CONF_STATION_ID, DOMAIN
from .coordinator import BOMWeatherCoordinator

CONDITION_MAP = {
    "thunderstorm": "lightning-rainy",
    "thunder": "lightning",
    "heavy rain": "pouring",
    "showers": "rainy",
    "shower": "rainy",
    "rainy": "rainy",
    "rain": "rainy",
    "mostly clear": "sunny",
    "clear": "sunny",
    "sunny": "sunny",
    "partly cloudy": "partlycloudy",
    "mostly cloudy": "partlycloudy",
    "cloudy": "cloudy",
    "overcast": "cloudy",
    "foggy": "fog",
    "fog": "fog",
    "haze": "fog",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BOM weather entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([BOMWeatherEntity(coordinator)])


class BOMWeatherEntity(CoordinatorEntity[BOMWeatherCoordinator], WeatherEntity):
    """Weather entity backed by a BOM observation feed."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS
    _attr_humidity_unit = PERCENTAGE

    def __init__(self, coordinator: BOMWeatherCoordinator) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = (
            f"{entry.data[CONF_PRODUCT_ID]}_{entry.data[CONF_STATION_ID]}_weather"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        entry = self.coordinator.config_entry
        data = self.coordinator.data.data if self.coordinator.data else {}
        header = self.coordinator.data.header if self.coordinator.data else {}
        station_name = data.get("name") or header.get("name") or entry.title

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{entry.data[CONF_PRODUCT_ID]}_{entry.data[CONF_STATION_ID]}",
                )
            },
            manufacturer="Bureau of Meteorology",
            name=str(station_name),
            configuration_url=self.coordinator.client.source_url,
        )

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        data = self.coordinator.data.data
        weather = _as_text(data.get("weather"))
        cloud = _as_text(data.get("cloud"))

        for source in (weather, cloud):
            condition = _condition_from_text(source)
            if condition:
                if condition == "sunny" and _is_night(
                    data.get("local_date_time_full")
                ):
                    return "clear-night"
                return condition

        wind_kmh = _as_float(data.get("wind_spd_kmh"))
        gust_kmh = _as_float(data.get("gust_kmh"))
        if (wind_kmh and wind_kmh >= 40) or (gust_kmh and gust_kmh >= 60):
            return "windy"

        if _is_night(data.get("local_date_time_full")):
            return "clear-night"

        return "sunny"

    @property
    def native_temperature(self) -> float | None:
        """Return air temperature in Celsius."""
        return _as_float(self.coordinator.data.data.get("air_temp"))

    @property
    def native_apparent_temperature(self) -> float | None:
        """Return apparent temperature in Celsius."""
        return _as_float(self.coordinator.data.data.get("apparent_t"))

    @property
    def native_dew_point(self) -> float | None:
        """Return dew point in Celsius."""
        return _as_float(self.coordinator.data.data.get("dewpt"))

    @property
    def native_pressure(self) -> float | None:
        """Return mean sea level pressure in hPa."""
        return _as_float(self.coordinator.data.data.get("press_msl"))

    @property
    def humidity(self) -> int | None:
        """Return relative humidity."""
        value = _as_float(self.coordinator.data.data.get("rel_hum"))
        return round(value) if value is not None else None

    @property
    def native_wind_speed(self) -> float | None:
        """Return wind speed in km/h."""
        return _as_float(self.coordinator.data.data.get("wind_spd_kmh"))

    @property
    def native_wind_gust_speed(self) -> float | None:
        """Return wind gust speed in km/h."""
        return _as_float(self.coordinator.data.data.get("gust_kmh"))

    @property
    def native_visibility(self) -> float | None:
        """Return visibility in kilometres."""
        return _as_float(self.coordinator.data.data.get("vis_km"))

    @property
    def wind_bearing(self) -> float | str | None:
        """Return wind bearing."""
        value = _as_float(self.coordinator.data.data.get("wind_dir_deg"))
        if value is not None:
            return value
        return _as_text(self.coordinator.data.data.get("wind_dir"))

    @property
    def attribution(self) -> str:
        """Return attribution."""
        return "Data provided by the Australian Bureau of Meteorology"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional BOM observation attributes."""
        data = self.coordinator.data.data
        header = self.coordinator.data.header
        return {
            "station_name": data.get("name") or header.get("name"),
            "product_id": header.get("ID")
            or self.coordinator.config_entry.data[CONF_PRODUCT_ID],
            "station_id": str(
                data.get("wmo") or self.coordinator.config_entry.data[CONF_STATION_ID]
            ),
            "local_observation_time": data.get("local_date_time_full"),
            "observation_time_utc": _bom_utc_to_iso(data.get("aifstime_utc")),
            "cloud": data.get("cloud"),
            "weather": data.get("weather"),
            "rain_since_9am_mm": _as_float(data.get("rain_trace")),
            "source_url": self.coordinator.data.source_url,
        }


def _condition_from_text(value: str | None) -> str | None:
    """Map BOM condition text to Home Assistant weather conditions."""
    if not value:
        return None

    lowered = value.lower()
    for phrase, condition in CONDITION_MAP.items():
        if phrase in lowered:
            return condition
    return None


def _as_float(value: Any) -> float | None:
    """Convert a BOM value to float when possible."""
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str | None:
    """Convert a BOM value to stripped text."""
    if value in (None, "", "-"):
        return None
    return str(value).strip()


def _is_night(value: Any) -> bool:
    """Return true when the BOM local observation time is at night."""
    text = _as_text(value)
    if not text:
        return False
    try:
        hour = datetime.strptime(text, "%Y%m%d%H%M%S").hour
    except ValueError:
        return False
    return hour >= 18 or hour < 6


def _bom_utc_to_iso(value: Any) -> str | None:
    """Convert BOM UTC timestamp format to ISO 8601."""
    text = _as_text(value)
    if not text:
        return None
    try:
        return (
            datetime.strptime(text, "%Y%m%d%H%M%S")
            .replace(tzinfo=timezone.utc)
            .isoformat()
        )
    except ValueError:
        return text
