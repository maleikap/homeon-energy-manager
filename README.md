# HomeOn Energy Manager

HomeOn Energy Manager is a Home Assistant custom integration for PV, battery storage, dynamic energy prices and EMS decision logic.

## Features

- Battery SOC targets
- Night reserve SOC
- Morning SOC target based on PV forecast
- Dynamic buy and sell price logic
- Best sell price detection from energy price attributes
- Battery available-to-sell calculation
- Inverter self-consumption estimation
- Dry-run switch
- Local polling

## Installation with HACS

1. Open HACS.
2. Add this repository as a custom repository.
3. Category: Integration.
4. Install HomeOn Energy Manager.
5. Restart Home Assistant.
6. Add integration from Settings -> Devices and services.

## Required entities

During setup select:

- Battery SOC sensor
- Battery power sensor
- PV power sensor
- House/load power sensor
- Grid power sensor
- Buy price sensor
- Sell price sensor
- Optional PV forecast sensors

## Companion card

Use HomeOn Energy Card for the Lovelace dashboard.

## Status

Early development version.
