# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

## Version 0.2.40.1

Hotfix for version 0.2.40.

This release fixes the economic threshold variables scope inside the EMS update cycle. The configurable economic number entities remain unchanged.

## Key features

- PV, battery, grid and household energy monitoring.
- Dynamic EMS decisions.
- PV Reality Check.
- Home Battery Priority.
- Negative Price Window Planner.
- Data quality diagnostics and SAFE_MODE.
- Configurable economic thresholds.
- Optional Deye inverter control with dry-run mode.

## Safety

Dry-run is enabled by default and inverter control is disabled by default. Battery trading must be enabled intentionally by the user.
