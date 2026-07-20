# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant integration for advanced energy management in photovoltaic and battery storage systems using dynamic electricity tariffs.

## Version 0.2.41

This release connects the economic threshold number entities to the EMS selling logic.

Changes:

- battery selling readiness is now calculated from configurable economic thresholds,
- estimated selling profit is calculated from available sellable energy and battery cycle cost,
- battery trading remains blocked when household protection is active,
- selling is blocked when estimated profit is below the configured minimum arbitrage profit,
- new diagnostic sensors show estimated sell profit, sell readiness and sell reason.

## Version 0.2.40

Version 0.2.40 added configurable economic threshold number entities.

## Version 0.2.39

Version 0.2.39 added data quality diagnostics and SAFE_MODE.

## Safety

The household has priority over energy trading.

Dry-run is enabled by default and inverter control is disabled by default. Battery trading must be enabled intentionally by the user.
