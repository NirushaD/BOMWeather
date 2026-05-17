# BOM Weather for Home Assistant

Custom Home Assistant integration that creates a `weather` entity from Bureau of
Meteorology real-time observation JSON feeds.

The integration uses BOM feed URLs in this form:

```text
https://www.bom.gov.au/fwo/<product_id>/<product_id>.<station_id>.json
```

Example:

```text
https://www.bom.gov.au/fwo/IDN60801/IDN60801.94768.json
```

## Install

1. Copy `custom_components/bom_weather` into your Home Assistant
   `config/custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings > Devices & services > Add integration**.
4. Search for **BOM Weather**.
5. Enter the BOM product ID and five digit station/WMO ID.

## Finding BOM product and station IDs

BOM documents its public data feeds here:

https://reg.bom.gov.au/catalogue/data-feeds.shtml

Observation products are grouped by state. The default product ID is `IDN60801`
for New South Wales observations. Use the matching product for your state and
the five digit station/WMO ID for your nearest observation station.

## Entity data

The weather entity exposes current temperature, apparent temperature, dew point,
humidity, pressure, wind speed, wind bearing, condition, and additional BOM
attributes such as rain since 9am, gust speed, observation time, and source URL.
