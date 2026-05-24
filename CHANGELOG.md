# Changelog

All notable changes to this project will be documented in this file.

This project uses semantic versioning where practical:

- Major version: breaking changes or migration steps.
- Minor version: new features or visible behavior changes.
- Patch version: bug fixes and documentation-only updates.

## 0.3.0 - 2026-05-24

### Added

- Added optional daily forecast support using BOM précis forecast XML products.
- Added setup fields for BOM forecast product ID and forecast area.
- Added Home Assistant `FORECAST_DAILY` support when forecast settings are
  configured.

## 0.2.1 - 2026-05-23

### Changed

- Updated `sunny` versus `clear-night` fallback logic to use Home Assistant's
  configured home location and the BOM observation timestamp, instead of a fixed
  6pm to 6am rule.

## 0.2.0 - 2026-05-23

### Added

- Added local Home Assistant brand assets:
  - `custom_components/bom_weather/brand/icon.png`
  - `custom_components/bom_weather/brand/icon@2x.png`
  - `custom_components/bom_weather/brand/logo.png`
  - `custom_components/bom_weather/brand/logo@2x.png`
- Added `tools/generate_brand_assets.ps1` so the icon and logo can be
  regenerated.
- Added README guidance explaining that BOM station detail IDs, such as
  `087185`, are not the same as the five digit JSON feed/WMO IDs used by this
  integration.
- Added README tables listing BOM observation product IDs and five digit
  station/WMO IDs by state and territory.

### Changed

- Switched feed requests to `https://reg.bom.gov.au/fwo`.
- Added explicit request headers for BOM feed requests to avoid HTTP 403
  responses from default HTTP clients.
- Updated README examples to use `reg.bom.gov.au`.
- Updated weather condition fallback behavior so blank BOM condition data returns
  `clear-night` between 6pm and 6am instead of always returning `sunny`.

## 0.1.0 - 2026-05-17

### Added

- Initial Home Assistant custom integration scaffold.
- Added config flow for integration setup from the Home Assistant UI.
- Added support for configurable BOM product ID, station/WMO ID, and polling
  interval.
- Added a weather entity backed by BOM real-time observation JSON feeds.
- Added current observation fields for temperature, apparent temperature, dew
  point, humidity, pressure, wind speed, wind gust, wind bearing, visibility,
  rain since 9am, observation time, and source URL.
- Added README installation and setup documentation.
