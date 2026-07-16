# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration designed for advanced energy management in buildings equipped with photovoltaic generation, battery storage, hybrid inverters and dynamic electricity tariffs.

The integration continuously analyses current energy flow, battery state of charge, PV production, grid import/export, market prices and internal consumption patterns. Based on this data it calculates safe operating targets for the battery and provides clear diagnostics for automated or supervised energy management.

## Key features

- Real-time monitoring of PV production, household consumption, battery power and grid exchange.
- Dynamic battery target calculation based on consumption, forecasted PV production and learned household behaviour.
- Support for dynamic electricity prices, including buy/sell price evaluation and preferred operating windows.
- Battery reserve planning for night consumption and next-day energy balance.
- PV Reality Check: evaluation of real weather conditions based on actual PV output, installed PV capacity, date and time of day.
- Home Battery Priority protection to prevent unwanted battery trading while the battery is supplying the household.
- Optional inverter control with dry-run mode for safe testing before enabling real commands.
- Diagnostic sensors showing planned actions, current inverter state and the reason behind EMS decisions.
- Designed for Home Assistant and HACS custom repository installation.

## Safety philosophy

HomeOn Energy Manager follows a conservative control strategy. The household has priority over energy trading.

By default, the system does not use the battery for active market trading. Battery trading must be explicitly enabled by the user. When the battery is currently supplying the household, HomeOn can block changes to inverter and battery settings to avoid interrupting normal self-consumption.

The integration is intended to support energy optimisation, but the final responsibility for configuration, inverter compatibility and electrical safety remains with the installer or system owner.

## Home Battery Priority

Version 0.2.36 introduces Home Battery Priority protection.

This feature adds a dedicated switch:

`HomeOn Tryb handlu baterią`

Default state: `OFF`

When battery trading is disabled:

- HomeOn does not intentionally sell stored battery energy.
- HomeOn does not enable battery export logic for trading purposes.
- The battery remains reserved primarily for household self-consumption.

When the battery is actively supplying the household:

- HomeOn can block inverter setting changes.
- Export-oriented battery actions are skipped.
- Diagnostic sensors explain why control was blocked.

Additional diagnostic entities include:

- `HomeOn Tryb handlu baterią`
- `HomeOn Ochrona domu bateria zasila dom`
- `HomeOn Moc baterii dla domu`
- `HomeOn Powód ochrony domu`

## PV Reality Check

PV Reality Check reduces dependency on external weather forecasts.

Instead of relying only on forecasted PV production, HomeOn compares the current PV output with an expected value calculated from:

- installed PV system size,
- current date,
- time of day,
- sun position approximation,
- actual PV production.

This makes it possible to detect situations where the forecast predicted good production, but real conditions are worse due to clouds, fog, snow, inverter limitation or another issue.

When real PV production is significantly below expectation, HomeOn can increase battery protection and avoid aggressive discharge decisions.

## Typical use cases

- Residential PV installation with battery storage.
- Hybrid inverter systems with self-consumption priority.
- Dynamic electricity tariff optimisation.
- Battery reserve planning for night consumption.
- Controlled charging during low-price periods.
- Supervised export management when energy prices are favourable.
- Diagnostics for Deye/Solarman-based inverter control.

## Installation with HACS

Add this repository as a custom repository in HACS:

Repository:

`maleikap/homeon-energy-manager`

Category:

`Integration`

After installation, restart Home Assistant and add the integration from the Home Assistant integrations page.

## Configuration

The integration requires appropriate Home Assistant entities for:

- battery state of charge,
- battery power,
- PV power,
- household load,
- grid power,
- electricity buy price,
- electricity sell price,
- optional PV forecast sensors,
- optional inverter control entities.

The exact entity configuration depends on the inverter, meter and Home Assistant setup.

## Inverter control

Inverter control is optional.

Recommended commissioning procedure:

1. Configure all sensors and verify that the EMS calculations are correct.
2. Keep dry-run mode enabled.
3. Review diagnostic sensors and planned inverter actions.
4. Enable inverter control only after confirming that the planned actions match the intended behaviour.
5. Keep battery trading disabled unless active battery export is intentionally required.

Dry-run mode allows the integration to show what it would do without sending commands to the inverter.

## Version 0.2.36

Highlights:

- Added Home Battery Priority protection.
- Added battery trading enable switch.
- Added diagnostics for household battery protection.
- Prevented battery trading actions when battery trading is disabled.
- Prevented inverter setting changes while the battery is supplying the household.
- Preserved existing PV Reality Check and inverter diagnostics.

## Disclaimer

This integration is provided for advanced Home Assistant energy management scenarios. It should be configured and tested carefully before enabling real inverter control.

Always verify inverter behaviour, local regulations, electrical installation requirements and warranty conditions before using automated control functions.
