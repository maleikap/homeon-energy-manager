# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

## Version 0.2.39

This release adds data quality diagnostics and SAFE_MODE.

SAFE_MODE is activated when required sensors are missing, unavailable, invalid or outside safe operating ranges. In SAFE_MODE the integration blocks risky EMS decisions and allows only conservative inverter safety limits when real inverter control is enabled.

New diagnostics include:

- data quality status,
- data quality score,
- data errors,
- data warnings,
- last valid data timestamp,
- SAFE_MODE state,
- SAFE_MODE reason,
- SAFE_MODE action.

## Key features

- PV, battery, grid and household monitoring.
- Adaptive battery target calculation.
- PV Reality Check.
- Home Battery Priority.
- Negative Price Window Planner.
- Deye inverter diagnostics.
- Data quality diagnostics and SAFE_MODE.
- Optional inverter control with dry-run mode.

## Safety

The household has priority over energy trading.

Dry-run is enabled by default and inverter control is disabled by default. Battery trading must be enabled intentionally by the user.
