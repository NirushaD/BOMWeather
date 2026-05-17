"""Client for Bureau of Meteorology observation JSON feeds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

DEFAULT_BASE_URL = "https://reg.bom.gov.au/fwo"
REQUEST_HEADERS = {
    "Accept": "application/json,text/plain,*/*",
    "User-Agent": (
        "HomeAssistant-BOMWeather/0.1 "
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


class BOMWeatherClient:
    """Small async client for BOM public observation feeds."""

    def __init__(
        self,
        session: ClientSession,
        product_id: str,
        station_id: str,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._product_id = product_id.upper()
        self._station_id = station_id
        self._base_url = base_url.rstrip("/")

    @property
    def source_url(self) -> str:
        """Return the JSON feed URL."""
        return (
            f"{self._base_url}/{self._product_id}/"
            f"{self._product_id}.{self._station_id}.json"
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
