from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

PERCENT = "%"


SENSORS = [
    ("mode", "Tryb EMS", None, "mdi:state-machine"),
    ("reason", "Decyzja EMS", None, "mdi:text-box-check"),

    ("inverter_control_enabled", "Sterowanie falownikiem", None, "mdi:power-settings"),
    ("inverter_control_action", "Akcja falownika", None, "mdi:inverter"),
    ("inverter_control_last_result", "Wynik sterowania falownikiem", None, "mdi:check-network"),

    ("soc", "SOC magazynu", PERCENT, "mdi:battery"),
    ("battery_status", "Status baterii", None, "mdi:battery-sync"),
    ("battery_power", "Moc baterii", UnitOfPower.WATT, "mdi:battery-charging"),
    ("battery_discharge_w", "Rozładowanie baterii", UnitOfPower.WATT, "mdi:battery-arrow-down"),
    ("battery_charge_w", "Ładowanie baterii", UnitOfPower.WATT, "mdi:battery-arrow-up"),

    ("pv_power", "Moc PV", UnitOfPower.WATT, "mdi:solar-power"),
    ("load_power", "Moc domu", UnitOfPower.WATT, "mdi:home-lightning-bolt"),
    ("grid_power", "Moc sieci", UnitOfPower.WATT, "mdi:transmission-tower"),
    ("grid_status", "Status sieci", None, "mdi:transmission-tower-import"),
    ("grid_import_w", "Import z sieci", UnitOfPower.WATT, "mdi:transmission-tower-import"),
    ("grid_export_w", "Eksport do sieci", UnitOfPower.WATT, "mdi:transmission-tower-export"),
    ("deye_self_power", "Pobór własny falownika", UnitOfPower.WATT, "mdi:power-plug"),

    ("buy_price", "Cena zakupu", "PLN/kWh", "mdi:cash-plus"),
    ("sell_price", "Cena sprzedaży", "PLN/kWh", "mdi:cash-minus"),
    ("best_sell_price_24h", "Najlepsza cena sprzedaży 24h", "PLN/kWh", "mdi:cash-clock"),
    ("best_sell_time_24h", "Godzina najlepszej sprzedaży", None, "mdi:clock-star-four-points"),
    ("next_better_sell_price", "Następna lepsza cena sprzedaży", "PLN/kWh", "mdi:cash-clock"),
    ("next_better_sell_time", "Godzina następnej lepszej sprzedaży", None, "mdi:clock-fast"),
    ("sell_prices_found", "Liczba cen sprzedaży", None, "mdi:counter"),
    ("sell_now_best", "Sprzedaż teraz najlepsza", None, "mdi:check-decagram"),
    ("sell_price_delta_to_best", "Różnica do najlepszej ceny", "PLN/kWh", "mdi:delta"),

    ("pv_forecast_today", "Prognoza PV dziś", UnitOfEnergy.KILO_WATT_HOUR, "mdi:weather-sunny"),
    ("pv_forecast_tomorrow", "Prognoza PV jutro", UnitOfEnergy.KILO_WATT_HOUR, "mdi:weather-sunny-alert"),

    ("battery_capacity_kwh", "Pojemność magazynu", UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-high"),
    ("min_soc", "Minimalny SOC", PERCENT, "mdi:battery-lock"),
    ("emergency_soc", "Awaryjny SOC", PERCENT, "mdi:battery-alert"),
    ("night_reserve_soc", "Rezerwa nocna", PERCENT, "mdi:weather-night"),
    ("morning_target_soc", "Cel poranny", PERCENT, "mdi:weather-sunset-up"),
    ("charge_target_soc", "Cel ładowania", PERCENT, "mdi:battery-plus"),
    ("discharge_target_soc", "Cel rozładowania", PERCENT, "mdi:battery-minus"),

    ("available_to_sell_kwh", "Energia dostępna do sprzedaży", UnitOfEnergy.KILO_WATT_HOUR, "mdi:cash-fast"),
    ("free_space_kwh", "Wolne miejsce w magazynie", UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-outline"),
    ("energy_to_charge_target_kwh", "Energia do celu ładowania", UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-clock"),
    ("energy_above_morning_target_kwh", "Energia ponad cel poranny", UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-check"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        HomeOnSensor(coordinator, entry, key, name, unit, icon)
        for key, name, unit, icon in SENSORS
    )


class HomeOnSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, unit, icon):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = f"HomeOn {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "HomeOn Energy Manager",
            "manufacturer": "HomeOn",
            "model": "Energy Manager",
            "sw_version": "0.2.0",
        }

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)
