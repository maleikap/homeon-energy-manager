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
    ("learn_samples", "EMS próbki nauki", None, "mdi:counter"),
    ("learn_runtime_hours", "EMS czas nauki", "h", "mdi:clock-outline"),
    ("learn_confidence", "EMS pewność nauki", PERCENT, "mdi:brain"),
    ("learn_last_update", "EMS ostatnia nauka", None, "mdi:update"),

    ("learn_avg_load_w", "EMS średnie zużycie domu", UnitOfPower.WATT, "mdi:home-lightning-bolt"),
    ("learn_avg_day_load_w", "EMS średnie zużycie dzień", UnitOfPower.WATT, "mdi:white-balance-sunny"),
    ("learn_avg_night_load_w", "EMS średnie zużycie noc", UnitOfPower.WATT, "mdi:weather-night"),
    ("learn_estimated_daily_consumption_kwh", "EMS szacowane zużycie dobowe", UnitOfEnergy.KILO_WATT_HOUR, "mdi:calendar-today"),
    ("learn_estimated_night_consumption_kwh", "EMS szacowane zużycie nocne", UnitOfEnergy.KILO_WATT_HOUR, "mdi:weather-night"),

    ("learn_avg_pv_w", "EMS średnia produkcja PV", UnitOfPower.WATT, "mdi:solar-power"),
    ("learn_avg_grid_import_w", "EMS średni import", UnitOfPower.WATT, "mdi:transmission-tower-import"),
    ("learn_avg_grid_export_w", "EMS średni eksport", UnitOfPower.WATT, "mdi:transmission-tower-export"),
    ("learn_avg_battery_charge_w", "EMS średnie ładowanie baterii", UnitOfPower.WATT, "mdi:battery-arrow-up"),
    ("learn_avg_battery_discharge_w", "EMS średnie rozładowanie baterii", UnitOfPower.WATT, "mdi:battery-arrow-down"),
    ("learn_avg_deye_self_power_w", "EMS średni pobór falownika", UnitOfPower.WATT, "mdi:power-plug"),

    ("learn_energy_load_kwh", "EMS energia domu", UnitOfEnergy.KILO_WATT_HOUR, "mdi:home-lightning-bolt"),
    ("learn_energy_pv_kwh", "EMS energia PV", UnitOfEnergy.KILO_WATT_HOUR, "mdi:solar-power"),
    ("learn_energy_grid_import_kwh", "EMS energia import", UnitOfEnergy.KILO_WATT_HOUR, "mdi:transmission-tower-import"),
    ("learn_energy_grid_export_kwh", "EMS energia eksport", UnitOfEnergy.KILO_WATT_HOUR, "mdi:transmission-tower-export"),
    ("learn_energy_battery_charge_kwh", "EMS energia ładowania baterii", UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-arrow-up"),
    ("learn_energy_battery_discharge_kwh", "EMS energia rozładowania baterii", UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-arrow-down"),
    ("learn_energy_deye_self_kwh", "EMS energia poboru falownika", UnitOfEnergy.KILO_WATT_HOUR, "mdi:power-plug"),

    ("learn_avg_buy_price", "EMS średnia cena zakupu", "PLN/kWh", "mdi:cash-plus"),
    ("learn_avg_sell_price", "EMS średnia cena sprzedaży", "PLN/kWh", "mdi:cash-minus"),
    ("learn_best_sell_price_seen", "EMS najlepsza zauważona cena sprzedaży", "PLN/kWh", "mdi:cash-star"),
    ("learn_most_common_mode", "EMS najczęstszy tryb", None, "mdi:state-machine"),
    ("plan_now_phase", "Plan faza dnia", None, "mdi:weather-partly-clock"),
    ("plan_recommended_soc", "Plan zalecany SOC", PERCENT, "mdi:battery-check"),
    ("plan_next_action", "Plan następna akcja", None, "mdi:calendar-arrow-right"),
    ("plan_next_action_time", "Plan godzina następnej akcji", None, "mdi:clock-outline"),
    ("plan_next_action_reason", "Plan powód następnej akcji", None, "mdi:text-box-check"),
    ("plan_charge_window", "Plan okno taniego ładowania", None, "mdi:battery-clock"),
    ("plan_sell_window", "Plan okno najlepszej sprzedaży", None, "mdi:cash-clock"),
    ("plan_hold_reason", "Plan powód trzymania energii", None, "mdi:battery-lock"),
    ("plan_expected_night_consumption_kwh", "Plan prognoza zużycia nocnego", UnitOfEnergy.KILO_WATT_HOUR, "mdi:weather-night"),
    ("plan_expected_day_consumption_kwh", "Plan prognoza zużycia 24h", UnitOfEnergy.KILO_WATT_HOUR, "mdi:calendar-today"),
    ("plan_cheapest_buy_price", "Plan najtańsza cena zakupu", "PLN/kWh", "mdi:cash-plus"),
    ("plan_best_sell_price", "Plan najlepsza cena sprzedaży", "PLN/kWh", "mdi:cash-minus"),
    ("plan_overview", "Plan 24h podsumowanie", None, "mdi:clipboard-text-clock"),
    ("learn_peak_load_hour", "EMS godzina największego zużycia", None, "mdi:chart-bell-curve"),
    ("learn_peak_load_w", "EMS największe godzinowe zużycie", UnitOfPower.WATT, "mdi:home-lightning-bolt"),
    ("learn_low_load_hour", "EMS godzina najniższego zużycia", None, "mdi:chart-bell-curve-cumulative"),
    ("learn_low_load_w", "EMS najniższe godzinowe zużycie", UnitOfPower.WATT, "mdi:home-lightning-bolt-outline"),
    ("plan_weather_tomorrow", "Plan pogoda jutro", None, "mdi:weather-partly-cloudy"),
    ("plan_pv_tomorrow_kwh", "Plan prognoza PV jutro", UnitOfEnergy.KILO_WATT_HOUR, "mdi:solar-power"),
    ("plan_next_day_energy_balance_kwh", "Plan bilans energii jutro", UnitOfEnergy.KILO_WATT_HOUR, "mdi:scale-balance"),
    ("plan_energy_to_keep_kwh", "Plan energia do zostawienia", UnitOfEnergy.KILO_WATT_HOUR, "mdi:battery-lock"),
    ("plan_safe_to_sell_kwh", "Plan bezpieczna energia do sprzedaży", UnitOfEnergy.KILO_WATT_HOUR, "mdi:cash-check"),
    ("plan_safe_export_limit_w", "Plan bezpieczny limit eksportu", UnitOfPower.WATT, "mdi:transmission-tower-export"),
    ("plan_weather_strategy", "Plan strategia pogoda", None, "mdi:weather-cloudy-clock"),
    ("plan_reasonable_buy_window", "Plan okno normalnego zakupu", None, "mdi:cash-clock"),
    ("inverter_control_executor_mode", "Sterowanie tryb wykonawczy", None, "mdi:state-machine"),
    ("inverter_control_safe_export_limit_w", "Sterowanie bezpieczny limit eksportu", UnitOfPower.WATT, "mdi:transmission-tower-export"),
    ("inverter_control_safe_to_sell_kwh", "Sterowanie bezpieczna energia do sprzedaży", UnitOfEnergy.KILO_WATT_HOUR, "mdi:cash-check"),
    ("inverter_control_weather_lock", "Sterowanie blokada pogodowa", None, "mdi:weather-cloudy-alert"),
    ("inverter_control_last_run", "Sterowanie ostatnie wykonanie", None, "mdi:clock-check"),
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
            "sw_version": "0.2.15",
        }

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._key)
