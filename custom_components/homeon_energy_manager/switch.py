from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


SWITCHES = [
    ("enabled", "Włączony", "mdi:power", True),
    ("dry_run", "Tryb testowy dry-run", "mdi:test-tube", True),
    ("inverter_control", "Sterowanie falownikiem", "mdi:power-settings", False),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        HomeOnSwitch(coordinator, entry, key, name, icon, default)
        for key, name, icon, default in SWITCHES
    )


class HomeOnSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, entry, key, name, icon, default):
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._default = default
        self._attr_name = f"HomeOn {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "HomeOn Energy Manager",
            "manufacturer": "HomeOn",
            "model": "Energy Manager",
            "sw_version": "0.2.10",
        }

    @property
    def is_on(self):
        return bool(
            self.hass.data[DOMAIN][self._entry.entry_id].get(
                self._key,
                self._default,
            )
        )

    async def _set_state(self, value: bool):
        self.hass.data[DOMAIN][self._entry.entry_id][self._key] = value

        options = dict(self._entry.options)
        options[self._key] = value
        self.hass.config_entries.async_update_entry(self._entry, options=options)

        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs):
        await self._set_state(True)

    async def async_turn_off(self, **kwargs):
        await self._set_state(False)
