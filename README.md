# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in buildings equipped with photovoltaic generation, battery storage, hybrid inverters and dynamic electricity tariffs.

The integration analyses energy flow, battery state of charge, PV production, grid import/export, market prices and household consumption patterns. Based on this data it calculates safe operating targets for the battery and provides transparent diagnostics for supervised or automated energy management.

## Key features

- Real-time monitoring of PV production, household consumption, battery power and grid exchange.
- Dynamic battery target calculation based on consumption, PV forecast and learned household behaviour.
- Support for dynamic electricity prices and preferred charging or selling windows.
- Battery reserve planning for night consumption and next-day energy balance.
- PV Reality Check based on actual PV output, installed PV capacity, date and time of day.
- Home Battery Priority protection for household self-consumption.
- Optional inverter control with dry-run mode.
- Diagnostic sensors for planned actions, inverter state and EMS decision reasons.

## Safety philosophy

The household has priority over energy trading.

By default, HomeOn does not use the battery for active market trading. Battery trading must be enabled explicitly. When the battery is supplying the household, HomeOn can block inverter setting changes to avoid interrupting normal self-consumption.

## Version 0.2.37

This release fixes the Home Battery Priority execution guard introduced in the previous version.

Changes:

- Moved the protection guard to the inverter control stage, where EMS data is already available.
- Ensured Home Battery Priority is calculated after grid and battery flow values are available.
- Prevented `UnboundLocalError` during coordinator refresh.
- Kept battery trading protection and household-priority logic unchanged.

## Installation with HACS

Add this repository as a custom repository in HACS:

`maleikap/homeon-energy-manager`

Category:

`Integration`

Restart Home Assistant after installation or update.

## Disclaimer

This integration is intended for advanced Home Assistant energy management scenarios. Test all settings carefully before enabling real inverter control. Always verify inverter behaviour, local regulations, electrical installation requirements and warranty conditions.
