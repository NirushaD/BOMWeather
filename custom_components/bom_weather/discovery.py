"""Discovery helpers for BOM Weather config flows."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re
import xml.etree.ElementTree as ET

from aiohttp import ClientError, ClientResponseError, ClientSession

from .api import DEFAULT_BASE_URL, REQUEST_HEADERS

OBSERVATION_REGIONS: dict[str, tuple[str, str]] = {
    "ACT": ("ACT - Canberra area", "https://reg.bom.gov.au/act/observations/canberra.shtml"),
    "NSW": ("NSW", "https://reg.bom.gov.au/nsw/observations/nswall.shtml"),
    "NT": ("NT", "https://reg.bom.gov.au/nt/observations/ntall.shtml"),
    "QLD": ("QLD", "https://reg.bom.gov.au/qld/observations/qldall.shtml"),
    "SA": ("SA", "https://reg.bom.gov.au/sa/observations/saall.shtml"),
    "TAS": ("TAS", "https://reg.bom.gov.au/tas/observations/tasall.shtml"),
    "VIC": ("VIC", "https://reg.bom.gov.au/vic/observations/vicall.shtml"),
    "WA": ("WA", "https://reg.bom.gov.au/wa/observations/waall.shtml"),
}

FORECAST_PRODUCTS: dict[str, str] = {
    "ACT": "IDN11060",
    "NSW": "IDN11060",
    "NT": "IDD10207",
    "QLD": "IDQ11295",
    "SA": "IDS10044",
    "TAS": "IDT16710",
    "VIC": "IDV10753",
    "WA": "IDW14199",
}

STATION_LINK_RE = re.compile(
    r"/products/(ID[A-Z]\d{5})/(ID[A-Z]\d{5})\.(\d{5})\.shtml[^>]*>([^<]+)<"
)


class BOMDiscoveryError(Exception):
    """Raised when discovery data cannot be loaded."""


@dataclass(frozen=True)
class ObservationStation:
    """A BOM observation station option."""

    product_id: str
    station_id: str
    name: str

    @property
    def option_value(self) -> str:
        """Return stable select value."""
        return f"{self.product_id}|{self.station_id}"

    @property
    def option_label(self) -> str:
        """Return friendly select label."""
        return f"{self.name} ({self.station_id})"


@dataclass(frozen=True)
class ForecastArea:
    """A BOM forecast area option."""

    product_id: str
    area: str
    label: str

    @property
    def option_value(self) -> str:
        """Return stable select value."""
        return f"{self.product_id}|{self.area}"

    @property
    def option_label(self) -> str:
        """Return friendly select label."""
        return self.label


async def async_get_observation_stations(
    session: ClientSession,
    region: str,
) -> list[ObservationStation]:
    """Return current observation station options for a region."""
    try:
        region_name, url = OBSERVATION_REGIONS[region]
    except KeyError as err:
        raise BOMDiscoveryError(f"Unknown BOM region: {region}") from err

    try:
        async with session.get(url, headers=REQUEST_HEADERS, timeout=20) as response:
            response.raise_for_status()
            html = await response.text()
    except ClientResponseError as err:
        raise BOMDiscoveryError(
            f"BOM returned HTTP {err.status} for {region_name} observations"
        ) from err
    except (ClientError, TimeoutError) as err:
        raise BOMDiscoveryError(
            f"Could not fetch BOM observations for {region_name}"
        ) from err

    stations: dict[tuple[str, str], ObservationStation] = {}
    for match in STATION_LINK_RE.finditer(html):
        product_id = match.group(1)
        station_id = match.group(3)
        name = re.sub(r"\s+", " ", unescape(match.group(4))).strip()
        stations[(product_id, station_id)] = ObservationStation(
            product_id=product_id,
            station_id=station_id,
            name=name,
        )

    if not stations:
        raise BOMDiscoveryError(f"BOM did not return station options for {region_name}")

    return sorted(stations.values(), key=lambda station: station.name.casefold())


async def async_get_forecast_areas(
    session: ClientSession,
    region: str,
) -> list[ForecastArea]:
    """Return current forecast area options for a region."""
    try:
        product_id = FORECAST_PRODUCTS[region]
    except KeyError as err:
        raise BOMDiscoveryError(f"Unknown BOM forecast region: {region}") from err

    url = f"{DEFAULT_BASE_URL}/{product_id}.xml"
    try:
        async with session.get(url, headers=REQUEST_HEADERS, timeout=20) as response:
            response.raise_for_status()
            payload = await response.text()
    except ClientResponseError as err:
        raise BOMDiscoveryError(
            f"BOM forecast returned HTTP {err.status} for {product_id}"
        ) from err
    except (ClientError, TimeoutError) as err:
        raise BOMDiscoveryError(f"Could not fetch BOM forecast {product_id}") from err

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as err:
        raise BOMDiscoveryError(f"BOM forecast {product_id} returned invalid XML") from err

    areas: list[ForecastArea] = [
        ForecastArea(
            product_id=product_id,
            area=area.attrib["description"],
            label=_forecast_label(area),
        )
        for area in root.findall("./forecast/area")
        if area.attrib.get("description")
    ]

    if not areas:
        raise BOMDiscoveryError(f"BOM did not return forecast areas for {product_id}")

    return sorted(areas, key=lambda area: area.label.casefold())


def infer_region(product_id: str | None) -> str:
    """Infer a BOM region from a product ID."""
    if not product_id or len(product_id) < 3:
        return "VIC"

    state_code = product_id[2]
    return {
        "D": "NT",
        "N": "NSW",
        "Q": "QLD",
        "S": "SA",
        "T": "TAS",
        "V": "VIC",
        "W": "WA",
    }.get(state_code, "VIC")


def split_option_value(value: str) -> tuple[str, str]:
    """Split a select option value into product and item IDs."""
    product_id, item_id = value.split("|", 1)
    return product_id, item_id


def _forecast_label(area: ET.Element) -> str:
    """Return a forecast option label."""
    description = area.attrib["description"]
    aac = area.attrib.get("aac")
    if aac:
        return f"{description} ({aac})"
    return description
