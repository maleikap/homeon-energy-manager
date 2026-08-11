from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_SOC_SENSOR,
    CONF_BATTERY_POWER_SENSOR,
    CONF_PV_POWER_SENSOR,
    CONF_LOAD_POWER_SENSOR,
    CONF_GRID_POWER_SENSOR,
    CONF_BUY_PRICE_SENSOR,
    CONF_SELL_PRICE_SENSOR,
    CONF_PV_FORECAST_TODAY_SENSOR,
    CONF_PV_FORECAST_TOMORROW_SENSOR,
    CONF_BATTERY_CAPACITY_KWH,
    CONF_MIN_SOC,
    CONF_EMERGENCY_SOC,
    CONF_NIGHT_CONSUMPTION_KWH,
    CONF_NIGHT_SAFETY_MARGIN,
    CONF_MIN_NIGHT_RESERVE_SOC,
    CONF_BATTERY_DISCHARGE_POSITIVE,
    CONF_GRID_IMPORT_POSITIVE,
    CONF_PV_MEDIUM_FORECAST_KWH,
    CONF_PV_GOOD_FORECAST_KWH,
    CONF_PV_VERY_GOOD_FORECAST_KWH,
    CONF_INVERTER_GRID_CHARGING_SWITCH,
    CONF_INVERTER_EXPORT_SURPLUS_SWITCH,
    CONF_INVERTER_MAX_CHARGE_CURRENT_NUMBER,
    CONF_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER,
    CONF_INVERTER_WORK_MODE_SELECT,
    CONF_INVERTER_WORK_MODE_SELL_OPTION,
    CONF_INVERTER_WORK_MODE_PV_CHARGE_OPTION,
    DEFAULT_BATTERY_CAPACITY_KWH,
    DEFAULT_MIN_SOC,
    DEFAULT_EMERGENCY_SOC,
    DEFAULT_NIGHT_CONSUMPTION_KWH,
    DEFAULT_NIGHT_SAFETY_MARGIN,
    DEFAULT_MIN_NIGHT_RESERVE_SOC,
    DEFAULT_PV_MEDIUM_FORECAST_KWH,
    DEFAULT_PV_GOOD_FORECAST_KWH,
    DEFAULT_PV_VERY_GOOD_FORECAST_KWH,
    DEFAULT_INVERTER_GRID_CHARGING_SWITCH,
    DEFAULT_INVERTER_EXPORT_SURPLUS_SWITCH,
    DEFAULT_INVERTER_MAX_CHARGE_CURRENT_NUMBER,
    DEFAULT_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER,
    DEFAULT_INVERTER_WORK_MODE_SELECT,
    DEFAULT_INVERTER_WORK_MODE_SELL_OPTION,
    DEFAULT_INVERTER_WORK_MODE_PV_CHARGE_OPTION,
)


SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
)

SWITCH_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="switch")
)

NUMBER_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="number")
)

SELECT_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="select")
)


def _schema(defaults: dict | None = None) -> vol.Schema:
    values = defaults or {}

    def value(key, default=None):
        return values.get(key, default)

    def optional_entity(key):
        configured = value(key)
        return vol.Optional(key, default=configured) if configured else vol.Optional(key)

    def required_entity(key):
        configured = value(key)
        return vol.Required(key, default=configured) if configured else vol.Required(key)

    return vol.Schema(
        {
            required_entity(CONF_SOC_SENSOR): SENSOR_SELECTOR,
            required_entity(CONF_BATTERY_POWER_SENSOR): SENSOR_SELECTOR,
            required_entity(CONF_PV_POWER_SENSOR): SENSOR_SELECTOR,
            required_entity(CONF_LOAD_POWER_SENSOR): SENSOR_SELECTOR,
            required_entity(CONF_GRID_POWER_SENSOR): SENSOR_SELECTOR,
            required_entity(CONF_BUY_PRICE_SENSOR): SENSOR_SELECTOR,
            required_entity(CONF_SELL_PRICE_SENSOR): SENSOR_SELECTOR,
            optional_entity(CONF_PV_FORECAST_TODAY_SENSOR): SENSOR_SELECTOR,
            optional_entity(CONF_PV_FORECAST_TOMORROW_SENSOR): SENSOR_SELECTOR,
            vol.Required(CONF_BATTERY_CAPACITY_KWH, default=value(CONF_BATTERY_CAPACITY_KWH, DEFAULT_BATTERY_CAPACITY_KWH)): vol.Coerce(float),
            vol.Required(CONF_MIN_SOC, default=value(CONF_MIN_SOC, DEFAULT_MIN_SOC)): vol.Coerce(float),
            vol.Required(CONF_EMERGENCY_SOC, default=value(CONF_EMERGENCY_SOC, DEFAULT_EMERGENCY_SOC)): vol.Coerce(float),
            vol.Required(CONF_NIGHT_CONSUMPTION_KWH, default=value(CONF_NIGHT_CONSUMPTION_KWH, DEFAULT_NIGHT_CONSUMPTION_KWH)): vol.Coerce(float),
            vol.Required(CONF_NIGHT_SAFETY_MARGIN, default=value(CONF_NIGHT_SAFETY_MARGIN, DEFAULT_NIGHT_SAFETY_MARGIN)): vol.Coerce(float),
            vol.Required(CONF_MIN_NIGHT_RESERVE_SOC, default=value(CONF_MIN_NIGHT_RESERVE_SOC, DEFAULT_MIN_NIGHT_RESERVE_SOC)): vol.Coerce(float),
            vol.Required(CONF_BATTERY_DISCHARGE_POSITIVE, default=value(CONF_BATTERY_DISCHARGE_POSITIVE, True)): selector.BooleanSelector(),
            vol.Required(CONF_GRID_IMPORT_POSITIVE, default=value(CONF_GRID_IMPORT_POSITIVE, True)): selector.BooleanSelector(),
            vol.Required(CONF_PV_MEDIUM_FORECAST_KWH, default=value(CONF_PV_MEDIUM_FORECAST_KWH, DEFAULT_PV_MEDIUM_FORECAST_KWH)): vol.Coerce(float),
            vol.Required(CONF_PV_GOOD_FORECAST_KWH, default=value(CONF_PV_GOOD_FORECAST_KWH, DEFAULT_PV_GOOD_FORECAST_KWH)): vol.Coerce(float),
            vol.Required(CONF_PV_VERY_GOOD_FORECAST_KWH, default=value(CONF_PV_VERY_GOOD_FORECAST_KWH, DEFAULT_PV_VERY_GOOD_FORECAST_KWH)): vol.Coerce(float),
            vol.Required(CONF_INVERTER_GRID_CHARGING_SWITCH, default=value(CONF_INVERTER_GRID_CHARGING_SWITCH, DEFAULT_INVERTER_GRID_CHARGING_SWITCH)): SWITCH_SELECTOR,
            vol.Required(CONF_INVERTER_EXPORT_SURPLUS_SWITCH, default=value(CONF_INVERTER_EXPORT_SURPLUS_SWITCH, DEFAULT_INVERTER_EXPORT_SURPLUS_SWITCH)): SWITCH_SELECTOR,
            vol.Required(CONF_INVERTER_MAX_CHARGE_CURRENT_NUMBER, default=value(CONF_INVERTER_MAX_CHARGE_CURRENT_NUMBER, DEFAULT_INVERTER_MAX_CHARGE_CURRENT_NUMBER)): NUMBER_SELECTOR,
            vol.Required(CONF_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER, default=value(CONF_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER, DEFAULT_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER)): NUMBER_SELECTOR,
            vol.Required(CONF_INVERTER_WORK_MODE_SELECT, default=value(CONF_INVERTER_WORK_MODE_SELECT, DEFAULT_INVERTER_WORK_MODE_SELECT)): SELECT_SELECTOR,
            vol.Required(CONF_INVERTER_WORK_MODE_SELL_OPTION, default=value(CONF_INVERTER_WORK_MODE_SELL_OPTION, DEFAULT_INVERTER_WORK_MODE_SELL_OPTION)): str,
            vol.Required(CONF_INVERTER_WORK_MODE_PV_CHARGE_OPTION, default=value(CONF_INVERTER_WORK_MODE_PV_CHARGE_OPTION, DEFAULT_INVERTER_WORK_MODE_PV_CHARGE_OPTION)): str,
        }
    )


class HomeOnEnergyManagerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id("homeon_energy_manager_default")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title="HomeOn Energy Manager",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return HomeOnEnergyManagerOptionsFlow(config_entry)


class HomeOnEnergyManagerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            updated = dict(self._config_entry.options)
            updated.update(user_input)
            return self.async_create_entry(title="", data=updated)

        current = dict(self._config_entry.data)
        current.update(self._config_entry.options)
        return self.async_show_form(step_id="init", data_schema=_schema(current))
