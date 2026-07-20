# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

## Version 0.2.42

This release adds EMS mode hysteresis and minimum mode hold time.

Changes:

- adds configurable minimum EMS mode hold time,
- adds mode candidate diagnostics,
- adds mode hysteresis diagnostics,
- prevents unnecessary rapid switching between EMS modes,
- urgent safety modes can still override hysteresis.

## Version 0.2.41

Version 0.2.41 connected economic threshold number entities to the EMS selling logic.

## Version 0.2.40

Version 0.2.40 added configurable economic threshold number entities.

## Version 0.2.39

Version 0.2.39 added data quality diagnostics and SAFE_MODE.

## Safety

The household has priority over energy trading.

Dry-run is enabled by default and inverter control is disabled by default. Battery trading must be enabled intentionally by the user.
