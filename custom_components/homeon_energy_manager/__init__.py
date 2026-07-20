from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import HomeOnEnergyCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH, Platform.NUMBER]

DEFAULT_RUNTIME_OPTIONS = {
    "enabled": True,
    "dry_run": True,
    "inverter_control": False,
    "inverter_export_target_w": 10000,
    "inverter_charge_current_a": 80,
    "inverter_discharge_current_a": 120,
    "inverter_safe_discharge_current_a": 20,
    "inverter_block_discharge_current_a": 5,
    "economic_good_sell_price": 0.55,
    "economic_cheap_charge_price": 0.30,
    "economic_negative_buy_price": 0.0,
    "economic_negative_sell_price": 0.0,
    "economic_expensive_buy_price": 0.55,
    "economic_min_sell_price_prepare": 0.05,
    "economic_min_energy_to_free_kwh": 0.5,
    "economic_negative_prepare_hours": 6.0,
    "economic_max_soc_after_negative_charge": 100.0,
    "economic_battery_cycle_cost": 0.15,
    "economic_min_arbitrage_profit": 1.0,
    "mode_min_hold_minutes": 10.0,
    "deye_min_command_interval_seconds": 120.0,
    "deye_max_changes_per_run": 6.0,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = HomeOnEnergyCoordinator(hass, entry)

    hass.data.setdefault(DOMAIN, {})

    runtime = {
        "coordinator": coordinator,
    }

    for key, default in DEFAULT_RUNTIME_OPTIONS.items():
        runtime[key] = entry.options.get(key, default)

    hass.data[DOMAIN][entry.entry_id] = runtime

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
