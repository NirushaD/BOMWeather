"""Weather entity for BOM realtime observations."""

from __future__ import annotations

from typing import Any

from homeassistant.components.weather import (
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
    WeatherEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_STATION_NAME, DOMAIN
from .coordinator import BOMDataUpdateCoordinator, BOMObservation


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the BOM weather entity."""
    coordinator: BOMDataUpdateCoordinator = entry.runtime_data
    async_add_entities([BOMWeatherEntity(coordinator, entry)])


class BOMWeatherEntity(CoordinatorEntity[BOMDataUpdateCoordinator], WeatherEntity):
    """Represent current weather from a BOM observation station."""

    _attr_attribution = "Weather data provided by the Australian Bureau of Meteorology"
    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_precipitation_unit = UnitOfLength.MILLIMETERS
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS

    def __init__(self, coordinator: BOMDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialise the weather entity."""
        super().__init__(coordinator)
        station_name = entry.data.get(CONF_STATION_NAME) or coordinator.data.station_name
        self._attr_unique_id = f"{coordinator.data.unique_id}_weather"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.data.unique_id)},
            "name": f"BOM {station_name}",
            "manufacturer": "Australian Bureau of Meteorology",
            "configuration_url": coordinator.client.url,
        }

    @property
    def observation(self) -> BOMObservation:
        """Return the latest observation."""
        return self.coordinator.data

    @property
    def native_temperature(self) -> float | None:
        """Return current temperature in Celsius."""
        return _as_float(self.observation.value("air_temp"))

    @property
    def native_apparent_temperature(self) -> float | None:
        """Return apparent temperature in Celsius."""
        return _as_float(self.observation.value("apparent_t"))

    @property
    def native_dew_point(self) -> float | None:
        """Return dew point in Celsius."""
        return _as_float(self.observation.value("dewpt"))

    @property
    def humidity(self) -> float | None:
        """Return relative humidity percentage."""
        return _as_float(self.observation.value("rel_hum"))

    @property
    def native_pressure(self) -> float | None:
        """Return mean sea level pressure in hPa."""
        return _as_float(
            self.observation.value("press_msl") or self.observation.value("press")
        )

    @property
    def native_wind_speed(self) -> float | None:
        """Return wind speed in km/h."""
        return _as_float(self.observation.value("wind_spd_kmh"))

    @property
    def native_wind_gust_speed(self) -> float | None:
        """Return wind gust in km/h."""
        return _as_float(self.observation.value("gust_kmh"))

    @property
    def wind_bearing(self) -> float | str | None:
        """Return wind bearing in degrees or cardinal text."""
        bearing = _as_float(self.observation.value("wind_dir_deg"))
        if bearing is not None:
            return bearing
        return self.observation.value("wind_dir")

    @property
    def native_visibility(self) -> float | None:
        """Return visibility in kilometres."""
        return _as_float(self.observation.value("vis_km"))

    @property
    def cloud_coverage(self) -> int | None:
        """Return cloud coverage as percentage derived from oktas."""
        oktas = _as_float(self.observation.value("cloud_oktas"))
        if oktas is None:
            return None
        return round(max(0, min(oktas, 8)) / 8 * 100)

    @property
    def condition(self) -> str | None:
        """Return a Home Assistant weather condition."""
        return _condition_from_observation(self.observation)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra details from the latest observation."""
        raw = self.observation.raw
        return {
            "station_name": self.observation.station_name,
            "wmo": self.observation.wmo,
            "product_id": self.observation.product_id,
            "observed_at": self.observation.observed_at,
            "local_date_time": raw.get("local_date_time"),
            "rain_since_9am_mm": _as_float(raw.get("rain_trace")),
            "rain_last_10_minutes_mm": _as_float(raw.get("rain_ten")),
            "rain_last_hour_mm": _as_float(raw.get("rain_hour")),
            "weather": raw.get("weather"),
            "cloud": raw.get("cloud"),
        }


def _condition_from_observation(observation: BOMObservation) -> str:
    """Map BOM current weather text and cloud fields to HA conditions."""
    weather = str(observation.value("weather") or "").lower()
    cloud = str(observation.value("cloud") or "").lower()
    text = f"{weather} {cloud}"

    if "thunder" in text and ("rain" in text or "shower" in text):
        return ATTR_CONDITION_LIGHTNING_RAINY
    if "thunder" in text or "lightning" in text:
        return ATTR_CONDITION_LIGHTNING
    if "fog" in text or "mist" in text:
        return ATTR_CONDITION_FOG
    if "heavy rain" in text or "pour" in text:
        return ATTR_CONDITION_POURING
    if "rain" in text or "shower" in text or _rain_present(observation):
        return ATTR_CONDITION_RAINY

    wind_speed = _as_float(observation.value("wind_spd_kmh")) or 0
    gust_speed = _as_float(observation.value("gust_kmh")) or 0
    windy = wind_speed >= 40 or gust_speed >= 60

    oktas = _as_float(observation.value("cloud_oktas"))
    if oktas is not None:
        if windy and oktas >= 3:
            return ATTR_CONDITION_WINDY_VARIANT
        if windy:
            return ATTR_CONDITION_WINDY
        if oktas <= 2:
            return ATTR_CONDITION_SUNNY
        if oktas <= 6:
            return ATTR_CONDITION_PARTLYCLOUDY
        return ATTR_CONDITION_CLOUDY

    if "clear" in text or "fine" in text:
        return ATTR_CONDITION_SUNNY
    if "partly" in text or "scattered" in text:
        return ATTR_CONDITION_PARTLYCLOUDY
    if "cloud" in text or "overcast" in text:
        return ATTR_CONDITION_CLOUDY
    if windy:
        return ATTR_CONDITION_WINDY
    return ATTR_CONDITION_SUNNY


def _rain_present(observation: BOMObservation) -> bool:
    """Return true when short-period rain observations are positive."""
    for key in ("rain_ten", "rain_hour"):
        value = _as_float(observation.value(key))
        if value and value > 0:
            return True
    return False


def _as_float(value: Any) -> float | None:
    """Convert BOM scalar values to floats."""
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
