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
- Configurable economic thresholds as Home Assistant number entities.
- Optional inverter control with dry-run mode.
- Diagnostic sensors for strategy, planned actions and inverter state.

## Version 0.2.40

This release moves economic decision thresholds from hard-coded values to configurable Home Assistant number entities.

New configurable thresholds include:

- good selling price,
- cheap charging price,
- negative buy-price threshold,
- negative sell-price threshold,
- expensive buy-price threshold,
- minimum selling price for preparing battery space,
- minimum energy to free before a negative-price window,
- maximum preparation time before a negative-price window,
- maximum SOC after charging during negative-price periods,
- battery cycle cost,
- minimum arbitrage profit.

These values allow the EMS strategy to be tuned to the actual tariff, battery cost and user preference without modifying the code.

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
