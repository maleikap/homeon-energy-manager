# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

## Version 0.2.40

This release adds configurable economic threshold number entities.

This is a safe numbers-only release. It does not yet change the EMS decision logic in coordinator.py.

New number entities include:

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

## Version 0.2.39

Version 0.2.39 added data quality diagnostics and SAFE_MODE.

## Safety

The household has priority over energy trading.

Dry-run is enabled by default and inverter control is disabled by default. Battery trading must be enabled intentionally by the user.
