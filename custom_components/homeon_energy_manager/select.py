from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    CONF_INVERTER_GRID_CHARGING_SWITCH,
    CONF_INVERTER_EXPORT_SURPLUS_SWITCH,
    CONF_INVERTER_EXPORT_SURPLUS_POWER_NUMBER,
    CONF_INVERTER_MAX_CHARGE_CURRENT_NUMBER,
    CONF_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER,
    DEFAULT_INVERTER_GRID_CHARGING_SWITCH,
    DEFAULT_INVERTER_EXPORT_SURPLUS_SWITCH,
    DEFAULT_INVERTER_EXPORT_SURPLUS_POWER_NUMBER,
    DEFAULT_INVERTER_MAX_CHARGE_CURRENT_NUMBER,
    DEFAULT_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER,
)


SELECTS = [
    (
        CONF_INVERTER_GRID_CHARGING_SWITCH,
        "Encja ładowania z sieci",
        "switch",
        DEFAULT_INVERTER_GRID_CHARGING_SWITCH,
        "mdi:toggle-switch",
    ),
    (
        CONF_INVERTER_EXPORT_SURPLUS_SWITCH,
        "Encja eksportu nadwyżki",
        "switch",
        DEFAULT_INVERTER_EXPORT_SURPLUS_SWITCH,
        "mdi:toggle-switch",
    ),
    (
        CONF_INVERTER_EXPORT_SURPLUS_POWER_NUMBER,
        "Encja mocy eksportu",
        "number",
        DEFAULT_INVERTER_EXPORT_SURPLUS_POWER_NUMBER,
        "mdi:numeric",
    ),
    (
        CONF_INVERTER_MAX_CHARGE_CURRENT_NUMBER,
        "Encja prądu ładowania",
        "number",
        DEFAULT_INVERTER_MAX_CHARGE_CURRENT_NUMBER,
        "mdi:numeric",
    ),
    (
        CONF_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER,
        "Encja prądu rozładowania",
        "number",
        DEFAULT_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER,
        "mdi:numeric",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities(
        HomeOnInverterEntitySelect(coordinator, entry, key, name, domain, default, icon)
        for key, name, domain, default, icon in SELECTS
    )


class HomeOnInverterEntitySelect(CoordinatorEntity, SelectEntity):
    def __init__(self, coordinator, entry, key, name, domain, default, icon):
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._domain = domain
        self._default = default

        self._attr_name = f"HomeOn {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}_select"
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "HomeOn Energy Manager",
            "manufacturer": "HomeOn",
            "model": "Energy Manager",
            "sw_version": "0.2.11",
        }

    @property
    def current_option(self):
        store = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        value = store.get(
            self._key,
            self._entry.options.get(
                self._key,
                self._entry.data.get(self._key, self._default),
            ),
        )

        value = str(value or "").strip()
        return value if value else self._default

    @property
    def options(self):
        ids = []

        try:
            ids = list(self.hass.states.async_entity_ids(self._domain))
        except Exception:
            ids = [
                state.entity_id
                for state in self.hass.states.async_all()
                if state.entity_id.startswith(f"{self._domain}.")
            ]

        ids = sorted(set(ids))

        current = self.current_option
        if current and current not in ids:
            ids.insert(0, current)

        if self._default and self._default not in ids:
            ids.insert(0, self._default)

        return ids

    async def async_select_option(self, option: str) -> None:
        option = str(option or "").strip()
        if not option:
            return

        self.hass.data[DOMAIN][self._entry.entry_id][self._key] = option

        options = dict(self._entry.options)
        options[self._key] = option

        self.hass.config_entries.async_update_entry(
            self._entry,
            options=options,
        )

        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
