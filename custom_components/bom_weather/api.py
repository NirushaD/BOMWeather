"""Client for Bureau of Meteorology observation JSON feeds."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any
import xml.etree.ElementTree as ET

from aiohttp import ClientError, ClientResponseError, ClientSession

DEFAULT_BASE_URL = "https://reg.bom.gov.au/fwo"
REQUEST_HEADERS = {
    "Accept": "application/json,text/plain,*/*",
    "User-Agent": (
        "HomeAssistant-BOMWeather/0.3 "
        "(+https://github.com/NirushaD/BOMWeather)"
    ),
}


class BOMWeatherError(Exception):
    """Base exception for BOM weather feed errors."""


class BOMWeatherFeedError(BOMWeatherError):
    """Raised when the BOM feed cannot be fetched or parsed."""


@dataclass(frozen=True)
class BOMObservation:
    """Latest BOM observation and feed metadata."""

    header: dict[str, Any]
    data: dict[str, Any]
    source_url: str
    forecasts: list[dict[str, Any]] = field(default_factory=list)
    forecast_source_url: str | None = None


class BOMWeatherClient:
    """Small async client for BOM public observation feeds."""

    def __init__(
        self,
        session: ClientSession,
        product_id: str,
        station_id: str,
        forecast_product_id: str | None = None,
        forecast_area: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._product_id = product_id.upper()
        self._station_id = station_id
        self._forecast_product_id = (forecast_product_id or "").strip().upper()
        self._forecast_area = (forecast_area or "").strip()
        self._base_url = base_url.rstrip("/")

    @property
    def source_url(self) -> str:
        """Return the JSON feed URL."""
        return (
            f"{self._base_url}/{self._product_id}/"
            f"{self._product_id}.{self._station_id}.json"
        )

    @property
    def forecast_source_url(self) -> str | None:
        """Return the forecast XML feed URL."""
        if not self._forecast_product_id:
            return None
        return f"{self._base_url}/{self._forecast_product_id}.xml"

    async def async_get_weather_data(self) -> BOMObservation:
        """Fetch observation data and optional forecast data."""
        observation = await self.async_get_latest_observation()
        if not self._forecast_product_id or not self._forecast_area:
            return observation

        forecasts = await self.async_get_daily_forecasts()
        return replace(
            observation,
            forecasts=forecasts,
            forecast_source_url=self.forecast_source_url,
        )

    async def async_get_latest_observation(self) -> BOMObservation:
        """Fetch and return the newest observation from the feed."""
        try:
            async with self._session.get(
                self.source_url,
                headers=REQUEST_HEADERS,
                timeout=20,
            ) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except ClientResponseError as err:
            raise BOMWeatherFeedError(
                f"BOM feed returned HTTP {err.status} for {self.source_url}"
            ) from err
        except (ClientError, TimeoutError) as err:
            raise BOMWeatherFeedError(f"Could not fetch BOM feed {self.source_url}") from err
        except ValueError as err:
            raise BOMWeatherFeedError(
                f"BOM feed did not return valid JSON: {self.source_url}"
            ) from err

        observations = payload.get("observations")
        if not isinstance(observations, dict):
            raise BOMWeatherFeedError("BOM feed JSON is missing observations")

        data = observations.get("data")
        if not isinstance(data, list) or not data:
            raise BOMWeatherFeedError("BOM feed JSON did not include observation data")

        header_rows = observations.get("header")
        header = header_rows[0] if isinstance(header_rows, list) and header_rows else {}
        if not isinstance(header, dict):
            header = {}

        latest = data[0]
        if not isinstance(latest, dict):
            raise BOMWeatherFeedError("BOM latest observation is malformed")

        return BOMObservation(header=header, data=latest, source_url=self.source_url)

    async def async_get_daily_forecasts(self) -> list[dict[str, Any]]:
        """Fetch and return daily forecasts from a BOM forecast XML feed."""
        if not self.forecast_source_url:
            return []

        try:
            async with self._session.get(
                self.forecast_source_url,
                headers=REQUEST_HEADERS,
                timeout=20,
            ) as response:
                response.raise_for_status()
                payload = await response.text()
        except ClientResponseError as err:
            raise BOMWeatherFeedError(
                f"BOM forecast returned HTTP {err.status} for {self.forecast_source_url}"
            ) from err
        except (ClientError, TimeoutError) as err:
            raise BOMWeatherFeedError(
                f"Could not fetch BOM forecast {self.forecast_source_url}"
            ) from err

        try:
            root = ET.fromstring(payload)
        except ET.ParseError as err:
            raise BOMWeatherFeedError(
                f"BOM forecast did not return valid XML: {self.forecast_source_url}"
            ) from err

        area = _find_forecast_area(root, self._forecast_area)
        if area is None:
            raise BOMWeatherFeedError(
                f"BOM forecast area '{self._forecast_area}' was not found"
            )

        forecasts: list[dict[str, Any]] = []
        for period in area.findall("forecast-period"):
            forecast = _parse_forecast_period(period)
            if forecast:
                forecasts.append(forecast)

        if not forecasts:
            raise BOMWeatherFeedError(
                f"BOM forecast area '{self._forecast_area}' did not include forecast data"
            )

        return forecasts


def _find_forecast_area(root: ET.Element, forecast_area: str) -> ET.Element | None:
    """Find a forecast area by description or AAC code."""
    wanted = forecast_area.casefold()
    for area in root.findall("./forecast/area"):
        description = area.attrib.get("description", "").casefold()
        aac = area.attrib.get("aac", "").casefold()
        if wanted in (description, aac):
            return area
    return None


def _parse_forecast_period(period: ET.Element) -> dict[str, Any] | None:
    """Parse one BOM forecast period into a Home Assistant forecast dict."""
    start_time = _parse_bom_forecast_time(period.attrib.get("start-time-utc"))
    if not start_time:
        return None

    values: dict[str, str] = {}
    for child in period:
        value_type = child.attrib.get("type")
        if value_type and child.text:
            values[value_type] = child.text.strip()

    forecast: dict[str, Any] = {"datetime": start_time}
    condition = _forecast_condition(values.get("precis"))
    if condition:
        forecast["condition"] = condition

    if (temperature := _as_float(values.get("air_temperature_maximum"))) is not None:
        forecast["native_temperature"] = temperature
    if (temperature_low := _as_float(values.get("air_temperature_minimum"))) is not None:
        forecast["native_templow"] = temperature_low
    rain_probability = _as_percentage(values.get("probability_of_precipitation"))
    if rain_probability is not None:
        forecast["precipitation_probability"] = rain_probability
    if (rain_amount := _as_precipitation(values.get("precipitation_range"))) is not None:
        forecast["native_precipitation"] = rain_amount

    if "native_temperature" not in forecast and "native_templow" not in forecast:
        return None
    return forecast


def _parse_bom_forecast_time(value: str | None) -> str | None:
    """Convert BOM forecast UTC time to ISO 8601."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return value


def _forecast_condition(value: str | None) -> str | None:
    """Map BOM forecast text to Home Assistant weather conditions."""
    if not value:
        return None

    lowered = value.lower()
    if "thunder" in lowered or "storm" in lowered:
        return "lightning-rainy" if _contains_rain(lowered) else "lightning"
    if "snow" in lowered:
        return "snowy-rainy" if _contains_rain(lowered) else "snowy"
    if "hail" in lowered:
        return "hail"
    if "fog" in lowered or "haze" in lowered:
        return "fog"
    if "heavy rain" in lowered:
        return "pouring"
    if _contains_rain(lowered):
        return "rainy"
    if "wind" in lowered:
        return "windy"
    if "partly cloudy" in lowered or "mostly cloudy" in lowered:
        return "partlycloudy"
    if "cloud" in lowered or "overcast" in lowered:
        return "cloudy"
    if "sunny" in lowered or "clear" in lowered:
        return "sunny"
    return None


def _contains_rain(value: str) -> bool:
    """Return true if forecast text suggests rain or showers."""
    return any(word in value for word in ("rain", "shower", "drizzle"))


def _as_float(value: str | None) -> float | None:
    """Convert text to float when possible."""
    if value in (None, "", "-"):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _as_percentage(value: str | None) -> int | None:
    """Convert BOM percentage text to an integer."""
    if not value:
        return None
    text = value.strip().rstrip("%")
    try:
        return round(float(text))
    except ValueError:
        return None


def _as_precipitation(value: str | None) -> float | None:
    """Convert BOM precipitation range text to the upper amount in mm."""
    if not value:
        return None
    numbers: list[float] = []
    for part in value.replace("<", "").replace("mm", "").split():
        try:
            numbers.append(float(part))
        except ValueError:
            continue
    return max(numbers) if numbers else None
