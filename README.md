# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

The integration analyses PV production, household consumption, battery state of charge, grid import/export, market prices and learned consumption patterns. It calculates battery targets, reserve levels and inverter actions with a conservative household-priority strategy.

## Key features

- Real-time monitoring of PV production, household load, battery power and grid exchange.
- Dynamic battery target calculation based on consumption, PV forecast and learned household behaviour.
- PV Reality Check based on actual PV output, installed PV capacity, date and time of day.
- Home Battery Priority protection for household self-consumption.
- Negative Price Window Planner for preparing battery capacity before negative-price periods.
- Data quality diagnostics and SAFE_MODE protection.
- Optional inverter control with dry-run mode.
- Diagnostic sensors for strategy, planned actions and inverter state.

## Version 0.2.39

This release adds data quality diagnostics and SAFE_MODE.

SAFE_MODE is activated when required sensors are missing, unavailable, invalid or outside safe operating ranges. In SAFE_MODE the integration blocks battery trading decisions and only allows conservative inverter limits when real inverter control is enabled.

New diagnostics include:

- data quality status,
- data quality score,
- data errors,
- data warnings,
- last valid data timestamp,
- SAFE_MODE state,
- SAFE_MODE reason,
- SAFE_MODE action.

## Safety philosophy

The household has priority over energy trading.

By default, HomeOn does not use the battery for active market trading. Battery trading must be enabled intentionally by the user. Dry-run mode is enabled by default and inverter control is disabled by default.

## Installation with HACS

Add this repository as a custom repository in HACS:

`maleikap/homeon-energy-manager`

Category:

`Integration`

Restart Home Assistant after installation or update.

## Disclaimer

This integration is intended for advanced Home Assistant energy management scenarios. Test all settings carefully before enabling real inverter control. Always verify inverter behaviour, local regulations, electrical installation requirements and warranty conditions.
