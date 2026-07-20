# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

## Stable restore

This main branch was restored to the stable v0.2.38 integration after a broken release produced an empty coordinator.py file.

The restored version includes:

- PV, battery, grid and household monitoring,
- adaptive battery targets,
- PV Reality Check,
- Home Battery Priority,
- Negative Price Window Planner,
- Deye inverter diagnostics,
- optional inverter control with dry-run mode.

## Safety

Dry-run is enabled by default and inverter control is disabled by default. Battery trading must be enabled intentionally by the user.
