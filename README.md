# BOM Realtime Weather for Home Assistant

This repository contains a Home Assistant custom integration that creates a realtime weather entity and supporting sensor entities from the Australian Bureau of Meteorology (BOM) station observation data feeds.

The integration uses the BOM public 72-hour station observation JSON products documented from the BOM Weather Data Services catalogue. These products are state/territory feeds named `IDD60910`, `IDN60910`, `IDQ60910`, `IDS60910`, `IDT60910`, `IDV60910`, and `IDW60910`, with one JSON file per station WMO number.

## Installation

1. Copy `custom_components/bom_weather_realtime` into the `custom_components` directory of your Home Assistant configuration.
2. Restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration**.
4. Search for **BOM Realtime Weather**.
5. Select the state/territory feed and enter the station WMO number from BOM's observation station tables.

## Created entities

Each configured station creates:

- One `weather` entity with realtime temperature, apparent temperature, humidity, pressure, wind, visibility, cloud and rain-derived condition values.
- Sensor entities for air temperature, apparent temperature, dew point, relative humidity, mean sea level pressure, wind speed, wind gust, wind direction, rain since 9am, rain over the previous 10 minutes and visibility.

## Notes

- The integration polls every 10 minutes, matching the realtime station summary cadence described by BOM while avoiding unnecessary requests.
- Use of BOM data must comply with the BOM copyright notice, disclaimer and data-feed terms described in the BOM Weather Data Services catalogue.
- The 72-hour station products are observation-only feeds, so this integration does not create forecast data.
