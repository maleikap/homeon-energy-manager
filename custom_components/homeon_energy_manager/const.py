DOMAIN = "homeon_energy_manager"

CONF_SOC_SENSOR = "soc_sensor"
CONF_BATTERY_POWER_SENSOR = "battery_power_sensor"
CONF_PV_POWER_SENSOR = "pv_power_sensor"
CONF_LOAD_POWER_SENSOR = "load_power_sensor"
CONF_GRID_POWER_SENSOR = "grid_power_sensor"
CONF_BUY_PRICE_SENSOR = "buy_price_sensor"
CONF_SELL_PRICE_SENSOR = "sell_price_sensor"
CONF_PV_FORECAST_TODAY_SENSOR = "pv_forecast_today_sensor"
CONF_PV_FORECAST_TOMORROW_SENSOR = "pv_forecast_tomorrow_sensor"

CONF_BATTERY_CAPACITY_KWH = "battery_capacity_kwh"
CONF_MIN_SOC = "min_soc"
CONF_EMERGENCY_SOC = "emergency_soc"
CONF_NIGHT_CONSUMPTION_KWH = "night_consumption_kwh"
CONF_NIGHT_SAFETY_MARGIN = "night_safety_margin"
CONF_MIN_NIGHT_RESERVE_SOC = "min_night_reserve_soc"

CONF_BATTERY_DISCHARGE_POSITIVE = "battery_discharge_positive"
CONF_GRID_IMPORT_POSITIVE = "grid_import_positive"

CONF_PV_MEDIUM_FORECAST_KWH = "pv_medium_forecast_kwh"
CONF_PV_GOOD_FORECAST_KWH = "pv_good_forecast_kwh"
CONF_PV_VERY_GOOD_FORECAST_KWH = "pv_very_good_forecast_kwh"

CONF_INVERTER_GRID_CHARGING_SWITCH = "inverter_grid_charging_switch"
CONF_INVERTER_EXPORT_SURPLUS_SWITCH = "inverter_export_surplus_switch"
CONF_INVERTER_EXPORT_SURPLUS_POWER_NUMBER = "inverter_export_surplus_power_number"
CONF_INVERTER_MAX_CHARGE_CURRENT_NUMBER = "inverter_max_charge_current_number"
CONF_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER = "inverter_max_discharge_current_number"

DEFAULT_BATTERY_CAPACITY_KWH = 30.0
DEFAULT_MIN_SOC = 15.0
DEFAULT_EMERGENCY_SOC = 10.0
DEFAULT_NIGHT_CONSUMPTION_KWH = 10.0
DEFAULT_NIGHT_SAFETY_MARGIN = 1.25
DEFAULT_MIN_NIGHT_RESERVE_SOC = 30.0

DEFAULT_PV_MEDIUM_FORECAST_KWH = 15.0
DEFAULT_PV_GOOD_FORECAST_KWH = 28.0
DEFAULT_PV_VERY_GOOD_FORECAST_KWH = 42.0

DEFAULT_INVERTER_GRID_CHARGING_SWITCH = "switch.inverter_battery_grid_charging"
DEFAULT_INVERTER_EXPORT_SURPLUS_SWITCH = "switch.inverter_export_surplus"
DEFAULT_INVERTER_EXPORT_SURPLUS_POWER_NUMBER = "number.inverter_export_surplus_power"
DEFAULT_INVERTER_MAX_CHARGE_CURRENT_NUMBER = "number.inverter_battery_max_charging_current"
DEFAULT_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER = "number.inverter_battery_max_discharging_current"
