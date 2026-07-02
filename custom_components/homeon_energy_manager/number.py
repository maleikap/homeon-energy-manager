from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


NUMBERS = [
    (
        "inverter_export_target_w",
        "Maksymalny eksport",
        0,
        24000,
        100,
        UnitOfPower.WATT,
        "mdi:transmission-tower-export",
        10000,
    ),
    (
        "inverter_charge_current_a",
        "Prąd ładowania",
        0,
        200,
        1,
        "A",
        "mdi:battery-arrow-up",
        80,
    ),
    (
        "inverter_discharge_current_a",
        "Prąd rozładowania",
        0,
        200,
        1,
        "A",
        "mdi:battery-arrow-down",
        120,
    ),
    (
        "inverter_safe_discharge_current_a",
        "Bezpieczny prąd rozładowania",
        0,
        200,
        1,
        "A",
        "mdi:battery-lock",
        20,
    ),
    (
        "inverter_block_discharge_current_a",
        "Prąd blokady rozładowania",
        0,
        50,
        1,
        "A",
        "mdi:battery-remove",
        5,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        HomeOnNumber(coordinator, entry, key, name, min_v, max_v, step, unit, icon, default)
        for key, name, min_v, max_v, step, unit, icon, default in NUMBERS
    )


class HomeOnNumber(CoordinatorEntity, NumberEntity):
    def __init__(
        self,
        coordinator,
        entry,
        key,
        name,
        min_v,
        max_v,
        step,
        unit,
        icon,
        default,
    ):
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._default = float(default)

        self._attr_name = f"HomeOn {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_min_value = float(min_v)
        self._attr_native_max_value = float(max_v)
        self._attr_native_step = float(step)
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_mode = NumberMode.BOX
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "HomeOn Energy Manager",
            "manufacturer": "HomeOn",
            "model": "Energy Manager",
            "sw_version": "0.2.6",
        }

    @property
    def native_value(self):
        value = self.hass.data[DOMAIN][self._entry.entry_id].get(
            self._key,
            self._entry.options.get(self._key, self._default),
        )

        try:
            return float(value)
        except Exception:
            return self._default

    async def async_set_native_value(self, value: float) -> None:
        final_value = float(value)

        final_value = max(final_value, float(self.native_min_value))
        final_value = min(final_value, float(self.native_max_value))

        self.hass.data[DOMAIN][self._entry.entry_id][self._key] = final_value

        options = dict(self._entry.options)
        options[self._key] = final_value
        self.hass.config_entries.async_update_entry(self._entry, options=options)

        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
