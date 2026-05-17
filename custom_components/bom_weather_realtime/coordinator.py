"""Coordinator and API client for BOM realtime observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from aiohttp import ClientError, ClientSession

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import BOM_BASE_URL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class BOMApiError(Exception):
    """Raised when BOM observation data cannot be retrieved or parsed."""


@dataclass(slots=True)
class BOMObservation:
    """Latest observation for one BOM weather station."""

    product_id: str
    wmo: str
    station_name: str
    raw: dict[str, Any]
    header: dict[str, Any]

    @property
    def unique_id(self) -> str:
        """Return a stable unique id for this station."""
        return f"{self.product_id}_{self.wmo}".lower()

    def value(self, key: str) -> Any:
        """Return an observation value by BOM key."""
        return self.raw.get(key)

    @property
    def observed_at(self) -> datetime | None:
        """Return the observation timestamp in UTC when available."""
        value = self.raw.get("aifstime_utc")
        if not value:
            return None
        try:
            return dt_util.as_utc(datetime.strptime(str(value), "%Y%m%d%H%M%S"))
        except ValueError:
            _LOGGER.debug("Could not parse BOM observation time %s", value)
            return None


class BOMClient:
    """Small client for the public BOM JSON observation feed."""

    def __init__(self, session: ClientSession, product_id: str, wmo: str) -> None:
        """Initialise the client."""
        self._session = session
        self.product_id = product_id.upper()
        self.wmo = str(wmo)

    @property
    def url(self) -> str:
        """Return the BOM JSON URL for this station."""
        return f"{BOM_BASE_URL}/{self.product_id}/{self.product_id}.{self.wmo}.json"

    async def async_get_latest_observation(self) -> BOMObservation:
        """Fetch and parse the latest station observation."""
        try:
            async with self._session.get(self.url) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
        except (ClientError, TimeoutError) as err:
            raise BOMApiError(f"Unable to fetch BOM data from {self.url}: {err}") from err

        try:
            observations = payload["observations"]
            rows = observations["data"]
            latest = rows[0]
        except (KeyError, IndexError, TypeError) as err:
            raise BOMApiError("BOM response did not contain observation data") from err

        header = {}
        headers = observations.get("header")
        if isinstance(headers, list) and headers:
            header = headers[0]

        station_name = str(latest.get("name") or self.wmo)
        return BOMObservation(
            product_id=self.product_id,
            wmo=self.wmo,
            station_name=station_name,
            raw=latest,
            header=header,
        )


class BOMDataUpdateCoordinator(DataUpdateCoordinator[BOMObservation]):
    """DataUpdateCoordinator for BOM observations."""

    def __init__(self, hass, client: BOMClient) -> None:  # noqa: ANN001
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{client.product_id}_{client.wmo}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> BOMObservation:
        """Fetch data from BOM."""
        try:
            return await self.client.async_get_latest_observation()
        except BOMApiError as err:
            raise UpdateFailed(str(err)) from err
