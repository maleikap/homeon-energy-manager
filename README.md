# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

## Version 0.2.43

This release adds a safer Deye execution layer.

Changes:

- adds configurable minimum interval between Deye command runs,
- adds configurable maximum number of real Deye changes per cycle,
- adds Deye driver safety diagnostics,
- blocks real execution if too many inverter changes would be sent in one cycle,
- keeps dry-run and household protection safety behaviour.

## Version 0.2.42

Version 0.2.42 added EMS mode hysteresis and minimum mode hold time.

## Version 0.2.41

Version 0.2.41 connected economic threshold number entities to the EMS selling logic.

## Version 0.2.40

Version 0.2.40 added configurable economic threshold number entities.

## Version 0.2.39

Version 0.2.39 added data quality diagnostics and SAFE_MODE.

## Safety

The household has priority over energy trading.

Dry-run is enabled by default and inverter control is disabled by default. Battery trading must be enabled intentionally by the user.
