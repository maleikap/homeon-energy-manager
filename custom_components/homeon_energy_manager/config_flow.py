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
    DEFAULT_BATTERY_CAPACITY_KWH,
    DEFAULT_MIN_SOC,
    DEFAULT_EMERGENCY_SOC,
    DEFAULT_NIGHT_CONSUMPTION_KWH,
    DEFAULT_NIGHT_SAFETY_MARGIN,
    DEFAULT_MIN_NIGHT_RESERVE_SOC,
    DEFAULT_PV_MEDIUM_FORECAST_KWH,
    DEFAULT_PV_GOOD_FORECAST_KWH,
    DEFAULT_PV_VERY_GOOD_FORECAST_KWH,
)


SENSOR_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain="sensor")
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

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SOC_SENSOR): SENSOR_SELECTOR,
                vol.Required(CONF_BATTERY_POWER_SENSOR): SENSOR_SELECTOR,
                vol.Required(CONF_PV_POWER_SENSOR): SENSOR_SELECTOR,
                vol.Required(CONF_LOAD_POWER_SENSOR): SENSOR_SELECTOR,
                vol.Required(CONF_GRID_POWER_SENSOR): SENSOR_SELECTOR,
                vol.Required(CONF_BUY_PRICE_SENSOR): SENSOR_SELECTOR,
                vol.Required(CONF_SELL_PRICE_SENSOR): SENSOR_SELECTOR,

                vol.Optional(CONF_PV_FORECAST_TODAY_SENSOR): SENSOR_SELECTOR,
                vol.Optional(CONF_PV_FORECAST_TOMORROW_SENSOR): SENSOR_SELECTOR,

                vol.Required(CONF_BATTERY_CAPACITY_KWH, default=DEFAULT_BATTERY_CAPACITY_KWH): vol.Coerce(float),
                vol.Required(CONF_MIN_SOC, default=DEFAULT_MIN_SOC): vol.Coerce(float),
                vol.Required(CONF_EMERGENCY_SOC, default=DEFAULT_EMERGENCY_SOC): vol.Coerce(float),
                vol.Required(CONF_NIGHT_CONSUMPTION_KWH, default=DEFAULT_NIGHT_CONSUMPTION_KWH): vol.Coerce(float),
                vol.Required(CONF_NIGHT_SAFETY_MARGIN, default=DEFAULT_NIGHT_SAFETY_MARGIN): vol.Coerce(float),
                vol.Required(CONF_MIN_NIGHT_RESERVE_SOC, default=DEFAULT_MIN_NIGHT_RESERVE_SOC): vol.Coerce(float),

                vol.Required(CONF_BATTERY_DISCHARGE_POSITIVE, default=True): selector.BooleanSelector(),
                vol.Required(CONF_GRID_IMPORT_POSITIVE, default=True): selector.BooleanSelector(),

                vol.Required(CONF_PV_MEDIUM_FORECAST_KWH, default=DEFAULT_PV_MEDIUM_FORECAST_KWH): vol.Coerce(float),
                vol.Required(CONF_PV_GOOD_FORECAST_KWH, default=DEFAULT_PV_GOOD_FORECAST_KWH): vol.Coerce(float),
                vol.Required(CONF_PV_VERY_GOOD_FORECAST_KWH, default=DEFAULT_PV_VERY_GOOD_FORECAST_KWH): vol.Coerce(float),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
