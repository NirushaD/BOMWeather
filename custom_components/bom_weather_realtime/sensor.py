"""Sensor entities for BOM realtime observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
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


@dataclass(frozen=True, kw_only=True)
class BOMSensorEntityDescription(SensorEntityDescription):
    """Description for a BOM observation sensor."""

    value_fn: Callable[[BOMObservation], Any]


def _value(key: str) -> Callable[[BOMObservation], Any]:
    """Return a value function for a raw BOM key."""
    return lambda observation: _as_float(observation.value(key))


SENSOR_DESCRIPTIONS: tuple[BOMSensorEntityDescription, ...] = (
    BOMSensorEntityDescription(
        key="air_temp",
        translation_key="air_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("air_temp"),
    ),
    BOMSensorEntityDescription(
        key="apparent_t",
        translation_key="apparent_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("apparent_t"),
    ),
    BOMSensorEntityDescription(
        key="dewpt",
        translation_key="dew_point",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("dewpt"),
    ),
    BOMSensorEntityDescription(
        key="rel_hum",
        translation_key="relative_humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("rel_hum"),
    ),
    BOMSensorEntityDescription(
        key="press_msl",
        translation_key="mean_sea_level_pressure",
        native_unit_of_measurement=UnitOfPressure.HPA,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("press_msl"),
    ),
    BOMSensorEntityDescription(
        key="wind_spd_kmh",
        translation_key="wind_speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("wind_spd_kmh"),
    ),
    BOMSensorEntityDescription(
        key="gust_kmh",
        translation_key="wind_gust",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("gust_kmh"),
    ),
    BOMSensorEntityDescription(
        key="wind_dir_deg",
        translation_key="wind_direction",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("wind_dir_deg"),
    ),
    BOMSensorEntityDescription(
        key="rain_trace",
        translation_key="rain_since_9am",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=_value("rain_trace"),
    ),
    BOMSensorEntityDescription(
        key="rain_ten",
        translation_key="rain_last_10_minutes",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("rain_ten"),
    ),
    BOMSensorEntityDescription(
        key="vis_km",
        translation_key="visibility",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_value("vis_km"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BOM observation sensors."""
    coordinator: BOMDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        BOMSensor(coordinator, entry, description) for description in SENSOR_DESCRIPTIONS
    )


class BOMSensor(CoordinatorEntity[BOMDataUpdateCoordinator], SensorEntity):
    """Represent a BOM observation sensor."""

    _attr_attribution = "Weather data provided by the Australian Bureau of Meteorology"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BOMDataUpdateCoordinator,
        entry: ConfigEntry,
        description: BOMSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        station_name = entry.data.get(CONF_STATION_NAME) or coordinator.data.station_name
        self._attr_unique_id = f"{coordinator.data.unique_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.data.unique_id)},
            "name": f"BOM {station_name}",
            "manufacturer": "Australian Bureau of Meteorology",
            "configuration_url": coordinator.client.url,
        }

    @property
    def native_value(self) -> Any:
        """Return the latest sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)


def _as_float(value: Any) -> float | None:
    """Convert BOM scalar values to floats."""
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
