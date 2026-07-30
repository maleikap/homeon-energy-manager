# HomeOn Energy Manager

HomeOn Energy Manager is a custom Home Assistant integration for photovoltaic systems with battery storage and dynamic electricity prices. It evaluates current power flow, battery state of charge, price forecasts, PV forecasts and learned household consumption to plan charging, self-consumption and controlled energy export.

> [!IMPORTANT]
> HomeOn Energy Manager can send commands to an inverter. Start with **Dry run** enabled, verify all entity mappings and diagnostics, and only then enable inverter control.

## Features

- dynamic battery charging and energy export based on buy and sell prices,
- household consumption priority and minimum battery SOC protection,
- preparation of battery capacity for expected PV production,
- aggressive pre-PV export during favourable prices when storage headroom is required,
- negative-price charging and export blocking,
- learned hourly household load and PV profiles,
- data-quality checks and automatic SAFE_MODE,
- command throttling, confirmation and retry diagnostics for Deye control,
- Lovelace diagnostics through the optional HomeOn Energy Card.

## Required integrations and data

The manager itself is installed through HACS as a custom integration. Full control requires the following Home Assistant entities:

| Source | Required data/entities | Purpose |
| --- | --- | --- |
| Inverter integration | battery SOC, battery power, PV power, household load and grid power sensors | Current energy flow and battery state |
| Dynamic tariff integration | current buy and sell price sensors; hourly price attributes are strongly recommended | Charging, export and arbitrage planning |
| Inverter control integration | grid-charging switch, export switch, export-power number, maximum charge-current number and maximum discharge-current number | Applying manager decisions to the inverter |

For Deye systems, use a Home Assistant integration that exposes the corresponding Deye entities. Entity names vary between installations, so every mapping must be checked against the entities available in your system.

## PV forecast integrations

A PV forecast is strongly recommended for the complete planning functionality.

Supported data sources:

- **Forecast.Solar** — daily production today, remaining production today, production tomorrow, power now and power in one hour.
- **Solcast PV Forecast** — production today and tomorrow, remaining production today, current power, power in 30 minutes and one hour, and today's peak production time.
- another integration exposing compatible daily PV forecast sensors.

When both detailed sources are available, the manager can use their current and remaining-production data to improve storage headroom planning. If detailed sensors are unavailable, HomeOn continues to use the configured daily forecast and its learned hourly PV profile. A missing optional forecast source must not stop the integration.

Example entities commonly provided by Forecast.Solar:

```text
sensor.energy_production_today
sensor.energy_production_today_remaining
sensor.energy_production_tomorrow
sensor.power_production_now
sensor.power_production_next_hour
```

Example entities commonly provided by Solcast PV Forecast:

```text
sensor.solcast_pv_forecast_prognoza_na_dzisiaj
sensor.solcast_pv_forecast_pozostala_prognoza_na_dzis
sensor.solcast_pv_forecast_prognoza_na_jutro
sensor.solcast_pv_forecast_aktualna_moc
sensor.solcast_pv_forecast_moc_w_30_minut
sensor.solcast_pv_forecast_moc_w_1_godzine
sensor.solcast_pv_forecast_czas_szczytowej_mocy_dzisiaj
```

These are examples, not fixed requirements. Home Assistant may generate different entity IDs depending on language and existing entities.

## Optional companion card

[HomeOn Energy Card](https://github.com/maleikap/homeon-energy-card) provides a Lovelace dashboard for manager status, operating mode, energy targets, forecasts and diagnostics. The manager works without the card.

## Installation

1. Add this repository to HACS as a custom integration.
2. Install HomeOn Energy Manager.
3. Restart Home Assistant.
4. Add the integration from **Settings → Devices & services**.
5. Map the required measurement, tariff and inverter-control entities.
6. Keep **Dry run** enabled during initial observation.
7. Confirm sensor signs, power values, price series and proposed commands before enabling real control.

## Safety

- The household has priority over energy trading.
- Dry run is enabled by default.
- Real inverter control and battery trading must be enabled intentionally.
- Invalid or stale critical data activates SAFE_MODE.
- Always keep the inverter's own battery protection and minimum SOC safeguards configured.
- Test beta releases on a monitored system before using them unattended.

## Current test release

The `test/0.2.44-beta.1` branch currently contains the 0.2.44 beta series. Beta.12 also prevents battery microcycles around the safe SOC during a high-price PV window: the manager holds the battery at its safe target, supplies the household from PV, exports only current PV surplus, and postpones charging until the sell price drops clearly. Stable installations should remain on the latest stable HACS release until testing is complete.

## Support

Issues and test observations: [GitHub Issues](https://github.com/maleikap/homeon-energy-manager/issues)

Support the project: [BuyCoffee](https://buycoffee.to/homeon)
