# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

The integration analyses PV production, household consumption, battery state of charge, grid import/export, market prices and learned consumption patterns. It calculates battery targets, reserve levels and inverter actions with a conservative household-priority strategy.

## Key features

- Real-time monitoring of PV production, household load, battery power and grid exchange.
- Dynamic battery target calculation based on consumption, PV forecast and learned household behaviour.
- PV Reality Check based on actual PV output, installed PV capacity, date and time of day.
- Home Battery Priority protection for household self-consumption.
- Negative Price Window Planner for preparing battery capacity before negative-price periods.
- Optional inverter control with dry-run mode.
- Diagnostic sensors for strategy, planned actions and inverter state.

## Negative Price Window Planner

Version 0.2.38 adds planning for negative electricity price windows.

The planner detects upcoming negative buy-price periods from the price sensor attributes. When conditions are favourable, HomeOn can prepare the battery before the negative-price window by freeing storage capacity. During the negative-price period, the system prioritises charging the battery and blocking export-oriented battery actions. After the negative-price period, stored energy can be used by the household or sold later when market conditions are favourable.

Typical sequence:

1. Detect an upcoming negative buy-price window.
2. If PV conditions are good and battery trading is enabled, free part of the battery before the window.
3. During the negative-price window, charge the battery and block export-oriented battery actions.
4. After the window, hold or sell energy depending on price, reserve and household demand.

Battery trading remains disabled by default. The user must explicitly enable battery trading before HomeOn is allowed to free storage capacity for market optimisation.

## Safety philosophy

The household has priority over energy trading.

By default, HomeOn does not use the battery for active market trading. Battery trading must be enabled intentionally by the user. When household protection is active and battery trading is disabled, HomeOn blocks inverter setting changes related to battery export.

## Installation with HACS

Add this repository as a custom repository in HACS:

`maleikap/homeon-energy-manager`

Category:

`Integration`

Restart Home Assistant after installation or update.

## Disclaimer

This integration is intended for advanced Home Assistant energy management scenarios. Test all settings carefully before enabling real inverter control. Always verify inverter behaviour, local regulations, electrical installation requirements and warranty conditions.
