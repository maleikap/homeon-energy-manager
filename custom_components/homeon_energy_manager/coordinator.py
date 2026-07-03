from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from .learning import update_learning
from .planner import build_planner_data

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
    CONF_INVERTER_EXPORT_SURPLUS_POWER_NUMBER,
    CONF_INVERTER_MAX_CHARGE_CURRENT_NUMBER,
    CONF_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER,
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

_LOGGER = logging.getLogger(__name__)

INVERTER_GRID_CHARGING = "switch.inverter_battery_grid_charging"
INVERTER_EXPORT_SURPLUS = "switch.inverter_export_surplus"
INVERTER_EXPORT_SURPLUS_POWER = "number.inverter_export_surplus_power"
INVERTER_MAX_CHARGE_CURRENT = "number.inverter_battery_max_charging_current"
INVERTER_MAX_DISCHARGE_CURRENT = "number.inverter_battery_max_discharging_current"

HOMEON_EXPORT_TARGET_W = 10000
HOMEON_CHARGE_CURRENT_A = 80
HOMEON_DISCHARGE_CURRENT_A = 120
HOMEON_SAFE_DISCHARGE_CURRENT_A = 20
HOMEON_BLOCK_DISCHARGE_CURRENT_A = 5


class HomeOnEnergyCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry

        super().__init__(
            hass,
            _LOGGER,
            name="HomeOn Energy Manager",
            update_interval=timedelta(seconds=30),
            config_entry=entry,
        )

    def _runtime_float(self, key: str, default: float) -> float:
        store = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {})
        value = store.get(key, self.entry.options.get(key, default))
        try:
            return float(value)
        except Exception:
            return float(default)

    def _conf_float(self, key: str, default: float) -> float:
        try:
            return float(self.entry.data.get(key, default))
        except Exception:
            return default

    def _conf_bool(self, key: str, default: bool) -> bool:
        value = self.entry.data.get(key, default)
        return bool(value)

    def _state_float_by_entity(self, entity_id: str | None, default: float = 0.0) -> float:
        if not entity_id:
            return default

        state = self.hass.states.get(entity_id)
        if state is None:
            return default

        raw = state.state
        if raw in (None, "", "unknown", "unavailable"):
            return default

        return self._as_float(raw, default)

    def _state_float_by_key(self, key: str, default: float = 0.0) -> float:
        return self._state_float_by_entity(self.entry.data.get(key), default)

    def _state_text_by_entity(self, entity_id: str, default: str) -> str:
        state = self.hass.states.get(entity_id)
        if state is None:
            return default

        text = str(state.state or "").strip()
        if not text or text.lower() in ("unknown", "unavailable", "none", "null"):
            return default

        return text

    def _as_float(self, value: Any, default: float | None = None) -> float | None:
        if isinstance(value, bool):
            return default

        if isinstance(value, (int, float)):
            return float(value)

        try:
            text = str(value).strip()
            text = text.replace(",", ".")
            text = text.replace("PLN/kWh", "")
            text = text.replace("zł/kWh", "")
            text = text.replace("zl/kWh", "")
            text = text.replace("PLN", "")
            text = text.replace("zł", "")
            text = text.replace(" ", "")
            return float(text)
        except Exception:
            return default

    def _parse_dt(self, value: Any) -> datetime | None:
        if value is None:
            return None

        if isinstance(value, datetime):
            dt = value
        else:
            if isinstance(value, (int, float)):
                try:
                    if value > 1000000000:
                        dt = datetime.fromtimestamp(value, dt_util.DEFAULT_TIME_ZONE)
                    else:
                        return None
                except Exception:
                    return None
            else:
                text = str(value).strip()
                dt = dt_util.parse_datetime(text)
                if dt is None:
                    return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

        return dt_util.as_local(dt)

    def _fmt_dt_hour(self, dt: datetime | None) -> str:
        if dt is None:
            return "-"
        try:
            return dt_util.as_local(dt).strftime("%H:%M")
        except Exception:
            return "-"

    def _extract_price_points(self, obj: Any, points: list[dict[str, Any]]) -> None:
        if isinstance(obj, dict):
            for key, val in obj.items():
                dt_from_key = self._parse_dt(key)
                price_from_val = self._as_float(val, None)

                if dt_from_key is not None and price_from_val is not None:
                    points.append({"dt": dt_from_key, "price": price_from_val})

            dt_candidate = None
            price_candidate = None

            for key, val in obj.items():
                key_l = str(key).lower()

                if (
                    key_l in ("time", "datetime", "date", "start", "start_time", "from", "valid_from", "hour", "timestamp")
                    or "time" in key_l
                    or "date" in key_l
                    or "start" in key_l
                    or "from" == key_l
                ):
                    parsed = self._parse_dt(val)
                    if parsed is not None:
                        dt_candidate = parsed

                if (
                    key_l in ("price", "value", "total", "rate", "amount", "cena")
                    or "price" in key_l
                    or "cena" in key_l
                ):
                    parsed_price = self._as_float(val, None)
                    if parsed_price is not None:
                        price_candidate = parsed_price

            if dt_candidate is not None and price_candidate is not None:
                points.append({"dt": dt_candidate, "price": price_candidate})

            for val in obj.values():
                self._extract_price_points(val, points)

        elif isinstance(obj, list):
            for item in obj:
                self._extract_price_points(item, points)

    def _price_stats_from_entity(self, entity_id: str | None, current_price: float) -> dict[str, Any]:
        now = dt_util.now()
        horizon_end = now + timedelta(hours=24)

        raw_points: list[dict[str, Any]] = []

        if entity_id:
            state = self.hass.states.get(entity_id)
            if state is not None:
                self._extract_price_points(dict(state.attributes), raw_points)

        by_minute: dict[str, dict[str, Any]] = {}

        for item in raw_points:
            dt = item.get("dt")
            price = self._as_float(item.get("price"), None)

            if dt is None or price is None:
                continue

            if price < -5 or price > 5:
                continue

            if dt < now - timedelta(minutes=20):
                continue

            if dt > horizon_end:
                continue

            key = dt.strftime("%Y-%m-%d %H:%M")
            by_minute[key] = {"dt": dt, "price": float(price)}

        points = sorted(by_minute.values(), key=lambda x: x["dt"])

        if not points:
            return {
                "sell_prices_found": 0,
                "best_sell_price_24h": round(current_price, 3),
                "best_sell_time_24h": "teraz",
                "next_better_sell_price": 0,
                "next_better_sell_time": "-",
                "sell_now_best": True,
                "sell_price_delta_to_best": 0,
                "sell_wait_reason": "Brak harmonogramu cen w atrybutach — używam ceny aktualnej",
            }

        best = max(points, key=lambda x: x["price"])
        best_price = float(best["price"])
        best_time = self._fmt_dt_hour(best["dt"])

        better_later = [
            x for x in points
            if x["dt"] > now + timedelta(minutes=15)
            and float(x["price"]) > float(current_price) + 0.005
        ]

        if better_later:
            next_better = sorted(better_later, key=lambda x: x["dt"])[0]
            next_better_price = float(next_better["price"])
            next_better_time = self._fmt_dt_hour(next_better["dt"])
        else:
            next_better_price = 0
            next_better_time = "-"

        tolerance = 0.01
        sell_now_best = current_price >= best_price - tolerance

        if sell_now_best:
            wait_reason = "Aktualna cena jest najlepsza lub prawie najlepsza w oknie 24h"
        elif next_better_price > 0:
            wait_reason = f"Za chwilę będzie lepsza cena sprzedaży: {next_better_price:.2f} PLN/kWh o {next_better_time}"
        else:
            wait_reason = f"Najlepsza cena sprzedaży w 24h to {best_price:.2f} PLN/kWh o {best_time}"

        return {
            "sell_prices_found": len(points),
            "best_sell_price_24h": round(best_price, 3),
            "best_sell_time_24h": best_time,
            "next_better_sell_price": round(next_better_price, 3),
            "next_better_sell_time": next_better_time,
            "sell_now_best": bool(sell_now_best),
            "sell_price_delta_to_best": round(max(0.0, best_price - current_price), 3),
            "sell_wait_reason": wait_reason,
        }

    async def _async_set_switch(self, entity_id: str, turn_on: bool, actions: list[str]) -> None:
        state = self.hass.states.get(entity_id)
        if state is None:
            actions.append(f"{entity_id}: brak encji")
            return

        service = "turn_on" if turn_on else "turn_off"

        try:
            await self.hass.services.async_call(
                "switch",
                service,
                {"entity_id": entity_id},
                blocking=True,
            )
            actions.append(f"{entity_id}: {'ON' if turn_on else 'OFF'}")
        except Exception as err:
            _LOGGER.exception("HomeOn inverter switch control failed: %s", entity_id)
            actions.append(f"{entity_id}: BŁĄD {err}")

    async def _async_set_number(self, entity_id: str, value: float, actions: list[str]) -> None:
        state = self.hass.states.get(entity_id)
        if state is None:
            actions.append(f"{entity_id}: brak encji")
            return

        min_v = self._as_float(state.attributes.get("min"), None)
        max_v = self._as_float(state.attributes.get("max"), None)

        final_value = float(value)

        if min_v is not None:
            final_value = max(final_value, float(min_v))

        if max_v is not None:
            final_value = min(final_value, float(max_v))

        try:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {
                    "entity_id": entity_id,
                    "value": final_value,
                },
                blocking=True,
            )
            actions.append(f"{entity_id}: {final_value:g}")
        except Exception as err:
            _LOGGER.exception("HomeOn inverter number control failed: %s", entity_id)
            actions.append(f"{entity_id}: BŁĄD {err}")

    async def _async_apply_inverter_control(self, data: dict[str, Any]) -> dict[str, Any]:
        store = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {})

        enabled = bool(store.get("enabled", True))
        dry_run = bool(store.get("dry_run", True))
        inverter_control = bool(store.get("inverter_control", False))
        mode = str(data.get("mode", "NORMAL"))

        def conf_entity(key: str, default: str) -> str:
            text = str(self.entry.data.get(key, default) or "").strip()
            return text if text else default

        inverter_grid_charging = conf_entity(CONF_INVERTER_GRID_CHARGING_SWITCH, INVERTER_GRID_CHARGING)
        inverter_export_surplus = conf_entity(CONF_INVERTER_EXPORT_SURPLUS_SWITCH, INVERTER_EXPORT_SURPLUS)
        inverter_export_surplus_power = conf_entity(CONF_INVERTER_EXPORT_SURPLUS_POWER_NUMBER, INVERTER_EXPORT_SURPLUS_POWER)
        inverter_max_charge_current = conf_entity(CONF_INVERTER_MAX_CHARGE_CURRENT_NUMBER, INVERTER_MAX_CHARGE_CURRENT)
        inverter_max_discharge_current = conf_entity(CONF_INVERTER_MAX_DISCHARGE_CURRENT_NUMBER, INVERTER_MAX_DISCHARGE_CURRENT)

        inverter_export_target_w = self._runtime_float("inverter_export_target_w", HOMEON_EXPORT_TARGET_W)
        inverter_charge_current_a = self._runtime_float("inverter_charge_current_a", HOMEON_CHARGE_CURRENT_A)
        inverter_discharge_current_a = self._runtime_float("inverter_discharge_current_a", HOMEON_DISCHARGE_CURRENT_A)
        inverter_safe_discharge_current_a = self._runtime_float("inverter_safe_discharge_current_a", HOMEON_SAFE_DISCHARGE_CURRENT_A)
        inverter_block_discharge_current_a = self._runtime_float("inverter_block_discharge_current_a", HOMEON_BLOCK_DISCHARGE_CURRENT_A)

        plan_safe_export_limit_w = self._as_float(data.get("plan_safe_export_limit_w"), inverter_export_target_w)
        plan_safe_to_sell_kwh = self._as_float(data.get("plan_safe_to_sell_kwh"), 0.0)
        safe_export_limit_w = min(inverter_export_target_w, max(0.0, float(plan_safe_export_limit_w or 0.0)))

        weather_lock = bool(
            mode == "WEATHER_HOLD_RESERVE"
            or (mode in ("SELL_BATTERY_HIGH_PRICE", "WAIT_BETTER_SELL_PRICE") and plan_safe_to_sell_kwh <= 0.2)
        )

        data["inverter_control_enabled"] = inverter_control
        data["inverter_control_dry_run"] = "ON" if dry_run else "OFF"
        data["inverter_control_config_source"] = "Konfiguracja integracji"
        data["inverter_control_executor_mode"] = mode
        data["inverter_control_safe_export_limit_w"] = round(safe_export_limit_w, 0)
        data["inverter_control_safe_to_sell_kwh"] = round(plan_safe_to_sell_kwh, 2)
        data["inverter_control_weather_lock"] = "ON" if weather_lock else "OFF"

        data["inverter_entity_grid_charging"] = inverter_grid_charging
        data["inverter_entity_export_surplus"] = inverter_export_surplus
        data["inverter_entity_export_surplus_power"] = inverter_export_surplus_power
        data["inverter_entity_max_charge_current"] = inverter_max_charge_current
        data["inverter_entity_max_discharge_current"] = inverter_max_discharge_current

        if not enabled:
            data["inverter_control_action"] = "HomeOn wyłączony — nie steruję falownikiem"
            data["inverter_control_last_result"] = "OFF"
            data["inverter_control_last_run"] = dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
            return data

        if not inverter_control:
            data["inverter_control_action"] = "Sterowanie falownikiem wyłączone"
            data["inverter_control_last_result"] = "OFF"
            data["inverter_control_last_run"] = dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
            return data

        desired: list[tuple[str, str, Any]] = []
        action = ""
        executor_mode = mode

        def sw(entity_id: str, value: bool) -> None:
            desired.append(("switch", entity_id, bool(value)))

        def num(entity_id: str, value: float) -> None:
            desired.append(("number", entity_id, float(value)))

        if weather_lock:
            executor_mode = "WEATHER_HOLD_RESERVE"
            action = "Pogoda/PV: blokuję sprzedaż baterii i zostawiam energię na kolejny dzień"
            sw(inverter_export_surplus, False)
            sw(inverter_grid_charging, False)
            num(inverter_max_discharge_current, inverter_safe_discharge_current_a)

        elif mode == "EMERGENCY_RESERVE":
            action = "Awaryjny SOC — włączam ładowanie z sieci i blokuję eksport"
            sw(inverter_export_surplus, False)
            sw(inverter_grid_charging, True)
            num(inverter_max_charge_current, inverter_charge_current_a)
            num(inverter_max_discharge_current, inverter_block_discharge_current_a)

        elif mode in ("NEGATIVE_IMPORT", "CHEAP_CHARGE"):
            action = "Tania energia — ładuję magazyn z sieci, eksport baterii zablokowany"
            sw(inverter_export_surplus, False)
            sw(inverter_grid_charging, True)
            num(inverter_max_charge_current, inverter_charge_current_a)
            num(inverter_max_discharge_current, inverter_block_discharge_current_a)

        elif mode == "SELL_BATTERY_HIGH_PRICE" and safe_export_limit_w > 0 and plan_safe_to_sell_kwh > 0.3:
            action = "Sprzedaż tylko bezpiecznej nadwyżki: %.2f kWh, limit eksportu %.0f W" % (plan_safe_to_sell_kwh, safe_export_limit_w)
            sw(inverter_grid_charging, False)
            num(inverter_export_surplus_power, safe_export_limit_w)
            num(inverter_max_discharge_current, inverter_discharge_current_a)
            sw(inverter_export_surplus, True)

        elif mode == "SELL_BATTERY_HIGH_PRICE":
            executor_mode = "SELL_BLOCKED_NO_SAFE_SURPLUS"
            action = "Cena sprzedaży dobra, ale brak bezpiecznej nadwyżki — blokuję eksport baterii"
            sw(inverter_export_surplus, False)
            sw(inverter_grid_charging, False)
            num(inverter_max_discharge_current, inverter_safe_discharge_current_a)

        elif mode == "WAIT_BETTER_SELL_PRICE":
            action = "Czekam na lepszą cenę sprzedaży — blokuję sprzedaż baterii"
            sw(inverter_grid_charging, False)
            sw(inverter_export_surplus, False)
            num(inverter_max_discharge_current, inverter_safe_discharge_current_a)

        elif mode == "PV_CHARGE":
            action = "Ładowanie z PV — ładowanie z sieci wyłączone, eksport baterii zablokowany"
            sw(inverter_grid_charging, False)
            sw(inverter_export_surplus, False)
            num(inverter_max_charge_current, inverter_charge_current_a)
            num(inverter_max_discharge_current, inverter_safe_discharge_current_a)

        elif mode == "EXPENSIVE_SELF_USE":
            action = "Droga energia — bateria pracuje na dom, bez sprzedaży do sieci"
            sw(inverter_grid_charging, False)
            sw(inverter_export_surplus, False)
            num(inverter_max_discharge_current, inverter_discharge_current_a)

        else:
            executor_mode = "NORMAL_SAFE"
            action = "Normalna praca — bez ładowania z sieci i bez wymuszonej sprzedaży"
            sw(inverter_grid_charging, False)
            sw(inverter_export_surplus, False)
            num(inverter_max_charge_current, inverter_charge_current_a)
            num(inverter_max_discharge_current, inverter_safe_discharge_current_a)

        data["inverter_control_executor_mode"] = executor_mode
        data["inverter_control_action"] = action

        preview = []
        for domain, entity_id, value in desired:
            if domain == "switch":
                preview.append(entity_id + ": " + ("ON" if bool(value) else "OFF"))
            else:
                preview.append(entity_id + ": " + ("%g" % float(value)))

        if dry_run:
            data["inverter_control_last_result"] = "DRY-RUN: " + " | ".join(preview)
            data["inverter_control_last_run"] = dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
            return data

        control_hash = "|".join(preview)
        now_ts = dt_util.now().timestamp()
        last_hash = getattr(self, "_homeon_last_control_hash", None)
        last_ts = getattr(self, "_homeon_last_control_ts", 0.0)

        if control_hash == last_hash and now_ts - float(last_ts or 0.0) < 120:
            data["inverter_control_last_result"] = "Bez zmian — ostatnie komendy były już wysłane mniej niż 120 s temu: " + control_hash
            data["inverter_control_last_run"] = dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
            return data

        actions: list[str] = []

        for domain, entity_id, value in desired:
            if domain == "switch":
                await self._async_set_switch(entity_id, bool(value), actions)
            elif domain == "number":
                await self._async_set_number(entity_id, float(value), actions)

        self._homeon_last_control_hash = control_hash
        self._homeon_last_control_ts = now_ts

        data["inverter_control_last_result"] = " | ".join(actions) if actions else "Brak wykonanych akcji"
        data["inverter_control_last_run"] = dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
        return data

    async def _async_update_data(self) -> dict:
        store = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {})
        enabled = bool(store.get("enabled", True))
        dry_run = bool(store.get("dry_run", True))

        battery_capacity_kwh = self._conf_float(CONF_BATTERY_CAPACITY_KWH, DEFAULT_BATTERY_CAPACITY_KWH)
        min_soc = self._conf_float(CONF_MIN_SOC, DEFAULT_MIN_SOC)
        emergency_soc = self._conf_float(CONF_EMERGENCY_SOC, DEFAULT_EMERGENCY_SOC)
        night_consumption_kwh = self._conf_float(CONF_NIGHT_CONSUMPTION_KWH, DEFAULT_NIGHT_CONSUMPTION_KWH)
        night_safety_margin = self._conf_float(CONF_NIGHT_SAFETY_MARGIN, DEFAULT_NIGHT_SAFETY_MARGIN)
        min_night_reserve_soc = self._conf_float(CONF_MIN_NIGHT_RESERVE_SOC, DEFAULT_MIN_NIGHT_RESERVE_SOC)

        pv_medium = self._conf_float(CONF_PV_MEDIUM_FORECAST_KWH, DEFAULT_PV_MEDIUM_FORECAST_KWH)
        pv_good = self._conf_float(CONF_PV_GOOD_FORECAST_KWH, DEFAULT_PV_GOOD_FORECAST_KWH)
        pv_very_good = self._conf_float(CONF_PV_VERY_GOOD_FORECAST_KWH, DEFAULT_PV_VERY_GOOD_FORECAST_KWH)

        battery_discharge_positive = self._conf_bool(CONF_BATTERY_DISCHARGE_POSITIVE, True)
        grid_import_positive = self._conf_bool(CONF_GRID_IMPORT_POSITIVE, True)

        soc = self._state_float_by_key(CONF_SOC_SENSOR)
        battery_power = self._state_float_by_key(CONF_BATTERY_POWER_SENSOR)
        pv_power = self._state_float_by_key(CONF_PV_POWER_SENSOR)
        load_power = self._state_float_by_key(CONF_LOAD_POWER_SENSOR)
        grid_power = self._state_float_by_key(CONF_GRID_POWER_SENSOR)
        buy_price = self._state_float_by_key(CONF_BUY_PRICE_SENSOR)
        sell_price = self._state_float_by_key(CONF_SELL_PRICE_SENSOR)

        pv_today = self._state_float_by_key(CONF_PV_FORECAST_TODAY_SENSOR)
        pv_tomorrow = self._state_float_by_key(CONF_PV_FORECAST_TOMORROW_SENSOR)

        sell_stats = self._price_stats_from_entity(
            self.entry.data.get(CONF_SELL_PRICE_SENSOR),
            sell_price,
        )

        if battery_discharge_positive:
            battery_discharge_w = max(battery_power, 0.0)
            battery_charge_w = max(-battery_power, 0.0)
            battery_status = "Rozładowanie" if battery_power > 20 else "Ładowanie" if battery_power < -20 else "Postój"
        else:
            battery_discharge_w = max(-battery_power, 0.0)
            battery_charge_w = max(battery_power, 0.0)
            battery_status = "Rozładowanie" if battery_power < -20 else "Ładowanie" if battery_power > 20 else "Postój"

        if grid_import_positive:
            grid_import_w = max(grid_power, 0.0)
            grid_export_w = max(-grid_power, 0.0)
            grid_status = "Import" if grid_power > 20 else "Eksport" if grid_power < -20 else "Zero"
        else:
            grid_import_w = max(-grid_power, 0.0)
            grid_export_w = max(grid_power, 0.0)
            grid_status = "Import" if grid_power < -20 else "Eksport" if grid_power > 20 else "Zero"

        night_reserve_soc = max(
            min_night_reserve_soc,
            min(100.0, (night_consumption_kwh * night_safety_margin / max(battery_capacity_kwh, 0.1)) * 100.0),
        )

        if pv_tomorrow >= pv_very_good:
            morning_target_soc = 50.0
            charge_target_soc = 55.0
        elif pv_tomorrow >= pv_good:
            morning_target_soc = 60.0
            charge_target_soc = 65.0
        elif pv_tomorrow >= pv_medium:
            morning_target_soc = 72.0
            charge_target_soc = 78.0
        else:
            morning_target_soc = 90.0
            charge_target_soc = 92.0

        discharge_target_soc = night_reserve_soc

        available_to_sell_kwh = max(0.0, battery_capacity_kwh * (soc - discharge_target_soc) / 100.0)
        free_space_kwh = max(0.0, battery_capacity_kwh * (100.0 - soc) / 100.0)
        energy_to_charge_target_kwh = max(0.0, battery_capacity_kwh * (charge_target_soc - soc) / 100.0)
        energy_above_morning_target_kwh = max(0.0, battery_capacity_kwh * (soc - morning_target_soc) / 100.0)

        deye_self_power = (
            pv_power
            + grid_import_w
            + battery_discharge_w
            - load_power
            - grid_export_w
            - battery_charge_w
        )

        if abs(deye_self_power) < 8:
            deye_self_power = 0.0

        deye_self_power = max(deye_self_power, 0.0)

        sell_ready = sell_price >= 0.55 and soc > discharge_target_soc + 8

        if not enabled:
            mode = "DISABLED"
            reason = "HomeOn EMS jest wyłączony"
        elif soc <= emergency_soc:
            mode = "EMERGENCY_RESERVE"
            reason = "SOC jest poniżej poziomu awaryjnego"
        elif buy_price <= 0 and soc < 100:
            mode = "NEGATIVE_IMPORT"
            reason = "Cena zakupu jest ujemna lub zerowa — opłaca się ładować"
        elif buy_price < 0.30 and soc < charge_target_soc:
            mode = "CHEAP_CHARGE"
            reason = "Tania energia — można ładować magazyn"
        elif sell_ready and not sell_stats["sell_now_best"]:
            mode = "WAIT_BETTER_SELL_PRICE"
            reason = sell_stats["sell_wait_reason"]
        elif sell_ready and sell_stats["sell_now_best"]:
            mode = "SELL_BATTERY_HIGH_PRICE"
            reason = f"Sprzedaż teraz ma sens — cena {sell_price:.2f} PLN/kWh jest najlepsza lub prawie najlepsza"
        elif pv_power > 1000 and soc < charge_target_soc:
            mode = "PV_CHARGE"
            reason = "Produkcja PV ładuje magazyn"
        elif buy_price >= 0.55 and soc > min_soc:
            mode = "EXPENSIVE_SELF_USE"
            reason = "Droga energia — używam baterii na dom"
        else:
            mode = "NORMAL"
            reason = "Normalna praca systemu"

        data = {
            "enabled": enabled,
            "dry_run": dry_run,
            "mode": mode,
            "reason": reason,

            "soc": round(soc, 1),
            "battery_power": round(battery_power, 0),
            "battery_status": battery_status,
            "pv_power": round(pv_power, 0),
            "load_power": round(load_power, 0),
            "grid_power": round(grid_power, 0),
            "grid_status": grid_status,

            "buy_price": round(buy_price, 3),
            "sell_price": round(sell_price, 3),

            "pv_forecast_today": round(pv_today, 1),
            "pv_forecast_tomorrow": round(pv_tomorrow, 1),

            "battery_capacity_kwh": round(battery_capacity_kwh, 1),
            "min_soc": round(min_soc, 1),
            "emergency_soc": round(emergency_soc, 1),
            "night_reserve_soc": round(night_reserve_soc, 1),
            "morning_target_soc": round(morning_target_soc, 1),
            "charge_target_soc": round(charge_target_soc, 1),
            "discharge_target_soc": round(discharge_target_soc, 1),

            "available_to_sell_kwh": round(available_to_sell_kwh, 2),
            "free_space_kwh": round(free_space_kwh, 2),
            "energy_to_charge_target_kwh": round(energy_to_charge_target_kwh, 2),
            "energy_above_morning_target_kwh": round(energy_above_morning_target_kwh, 2),

            "deye_self_power": round(deye_self_power, 0),
            "battery_discharge_w": round(battery_discharge_w, 0),
            "battery_charge_w": round(battery_charge_w, 0),
            "grid_import_w": round(grid_import_w, 0),
            "grid_export_w": round(grid_export_w, 0),
        }

        data.update(sell_stats)
        data = await update_learning(self, data)
        data = build_planner_data(self, data)
        data = await self._async_apply_inverter_control(data)
        return data
