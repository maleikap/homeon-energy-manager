from __future__ import annotations

from datetime import datetime, timedelta
import logging
import math
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
INVERTER_WORK_MODE_SELECT = "select.inverter_work_mode"
INVERTER_WORK_MODE_SELL_OPTION = "Export First"

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


    async def _async_set_select(self, entity_id: str, option: str, actions: list[str]) -> None:
        state = self.hass.states.get(entity_id)
        if state is None:
            actions.append(f"{entity_id}: brak encji")
            return

        wanted = str(option or "").strip()
        options = state.attributes.get("options") or []

        final_option = wanted
        for opt in options:
            if str(opt).strip().lower() == wanted.lower():
                final_option = str(opt)
                break

        if options and final_option not in [str(x) for x in options]:
            actions.append(f"{entity_id}: BŁĄD opcja '{wanted}' nie istnieje. Dostępne: {', '.join(map(str, options))}")
            return

        try:
            await self.hass.services.async_call(
                "select",
                "select_option",
                {
                    "entity_id": entity_id,
                    "option": final_option,
                },
                blocking=True,
            )
            actions.append(f"{entity_id}: {final_option}")
        except Exception as err:
            _LOGGER.exception("HomeOn inverter select control failed: %s", entity_id)
            actions.append(f"{entity_id}: BŁĄD {err}")


    def _price_points_for_entity(
        self,
        entity_id: str | None,
        current_price: float,
        horizon_hours: int = 24,
    ) -> list[dict[str, Any]]:
        now = dt_util.now()
        horizon_end = now + timedelta(hours=horizon_hours)

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

        if current_price is not None:
            key = now.strftime("%Y-%m-%d %H:%M")
            by_minute[key] = {"dt": now, "price": float(current_price)}

        return sorted(by_minute.values(), key=lambda x: x["dt"])

    def _negative_price_plan(
        self,
        buy_price_entity: str | None,
        buy_price: float,
        sell_price: float,
        soc: float,
        battery_capacity_kwh: float,
        load_power_w: float,
        avg_load_w: float,
        pv_reality: dict[str, Any],
        battery_trade_enabled: bool,
        sell_stats: dict[str, Any],
    ) -> dict[str, Any]:
        now = dt_util.now()
        points = self._price_points_for_entity(buy_price_entity, buy_price, horizon_hours=12)

        negative_points = [
            p for p in points
            if self._as_float(p.get("price"), 999.0) is not None
            and float(p.get("price")) <= 0.0
        ]

        result = {
            "status": "BRAK",
            "start": "-",
            "end": "-",
            "min_price": 0.0,
            "required_free_kwh": 0.0,
            "energy_to_free_kwh": 0.0,
            "target_soc_before": 100.0,
            "prepare_export_w": 0.0,
            "strategy": "Brak ceny ujemnej w najbliższym oknie albo brak harmonogramu cen.",
            "reason": "Nie znaleziono nadchodzącego okna ceny ujemnej w atrybutach ceny zakupu.",
            "prepare": False,
            "now": False,
            "sell_block": bool(sell_price <= 0.0),
        }

        if not negative_points:
            if buy_price <= 0.0:
                result.update({
                    "status": "TERAZ",
                    "start": "teraz",
                    "end": "-",
                    "min_price": round(buy_price, 3),
                    "strategy": "Ładuj magazyn przy cenie ujemnej i blokuj eksport.",
                    "reason": "Aktualna cena zakupu jest ujemna lub zerowa — priorytetem jest ładowanie magazynu i brak sprzedaży.",
                    "now": True,
                })
            elif sell_price <= 0.0:
                result.update({
                    "status": "BLOKUJ EKSPORT",
                    "strategy": "Cena sprzedaży jest ujemna — blokuj oddawanie energii do sieci.",
                    "reason": "Cena sprzedaży jest ujemna lub zerowa. HomeOn nie powinien sprzedawać energii z baterii ani wymuszać eksportu.",
                })
            return result

        first = negative_points[0]
        group = [first]
        last = first

        for item in negative_points[1:]:
            try:
                if item["dt"] <= last["dt"] + timedelta(minutes=90):
                    group.append(item)
                    last = item
                else:
                    break
            except Exception:
                break

        start_dt = group[0]["dt"]
        end_dt = group[-1]["dt"] + timedelta(hours=1)
        min_price = min(float(x["price"]) for x in group)

        now_active = bool((buy_price <= 0.0) or (start_dt <= now + timedelta(minutes=10) and end_dt > now))
        hours_to_start = max(0.0, (start_dt - now).total_seconds() / 3600.0)
        duration_h = max(1.0, (end_dt - start_dt).total_seconds() / 3600.0)

        pv_score = max(0.0, min(100.0, self._as_float(pv_reality.get("score"), 0.0) or 0.0)) / 100.0
        pv_kwp = max(0.0, self._as_float(pv_reality.get("installed_kwp"), 0.0) or 0.0)

        expected_pv_window_kwh = max(0.0, pv_kwp * 0.35 * duration_h * max(0.25, pv_score))
        expected_load_window_kwh = max(0.0, max(load_power_w, avg_load_w, 250.0) * duration_h / 1000.0)
        negative_grid_charge_room_kwh = max(0.0, battery_capacity_kwh * 0.18)

        required_free_kwh = expected_pv_window_kwh + negative_grid_charge_room_kwh - expected_load_window_kwh
        required_free_kwh = max(1.0, required_free_kwh)
        required_free_kwh = min(required_free_kwh, max(1.0, battery_capacity_kwh * 0.65))

        current_free_kwh = max(0.0, battery_capacity_kwh * (100.0 - soc) / 100.0)
        energy_to_free_kwh = max(0.0, required_free_kwh - current_free_kwh)

        target_soc_before = 100.0 - (required_free_kwh / max(battery_capacity_kwh, 0.1) * 100.0)
        target_soc_before = max(15.0, min(95.0, target_soc_before))

        prepare_export_w = 0.0
        if hours_to_start > 0.1 and energy_to_free_kwh > 0:
            prepare_export_w = energy_to_free_kwh * 1000.0 / max(0.5, hours_to_start)
            prepare_export_w = max(500.0, min(float(HOMEON_EXPORT_TARGET_W), prepare_export_w))

        best_sell_price = self._as_float(sell_stats.get("best_sell_price_24h"), sell_price) or sell_price
        sell_is_reasonable_now = bool(sell_price > 0.05 and sell_price >= min(best_sell_price, sell_price) - 0.20)

        prepare = bool(
            not now_active
            and battery_trade_enabled
            and hours_to_start <= 6.0
            and energy_to_free_kwh >= 0.5
            and soc > target_soc_before + 3.0
            and sell_is_reasonable_now
        )

        if now_active:
            status = "TERAZ"
            strategy = "Cena ujemna trwa teraz — ładuj magazyn i blokuj eksport."
            reason = (
                f"Cena zakupu {buy_price:.3f} PLN/kWh. "
                "HomeOn powinien ładować magazyn, blokować sprzedaż i zatrzymać eksport baterii."
            )
        elif prepare:
            status = "PRZYGOTUJ"
            strategy = "Przed ceną ujemną zwolnij miejsce w magazynie, potem ładuj przy cenie ujemnej."
            reason = (
                f"Cena ujemna startuje o {self._fmt_dt_hour(start_dt)}. "
                f"Warto zwolnić około {energy_to_free_kwh:.1f} kWh, cel SOC przed oknem {target_soc_before:.0f}%. "
                "Potem magazyn może przyjąć PV i tanią energię zamiast oddawać ją przy złej cenie."
            )
        else:
            status = "NADCHODZI"
            strategy = "Wykryto cenę ujemną, ale nie ma warunków do wcześniejszej sprzedaży z magazynu."
            if not battery_trade_enabled:
                reason = "Cena ujemna jest w planie, ale tryb handlu baterią jest OFF — HomeOn nie opróżnia magazynu handlowo."
            elif energy_to_free_kwh < 0.5:
                reason = "Cena ujemna jest w planie, ale w magazynie jest już wystarczająco wolnego miejsca."
            elif sell_price <= 0.05:
                reason = "Cena ujemna jest w planie, ale obecna cena sprzedaży jest za niska na opłacalne zwalnianie magazynu."
            else:
                reason = "Cena ujemna jest w planie, ale okno jest za daleko albo SOC nie pozwala na sensowne zwolnienie magazynu."

        result.update({
            "status": status,
            "start": self._fmt_dt_hour(start_dt),
            "end": self._fmt_dt_hour(end_dt),
            "min_price": round(min_price, 3),
            "required_free_kwh": round(required_free_kwh, 2),
            "energy_to_free_kwh": round(energy_to_free_kwh, 2),
            "target_soc_before": round(target_soc_before, 1),
            "prepare_export_w": round(prepare_export_w, 0),
            "strategy": strategy[:240],
            "reason": reason[:240],
            "prepare": prepare,
            "now": now_active,
            "sell_block": bool(sell_price <= 0.0),
        })

        return result

    def _pv_reality_data(self, pv_power_w: float) -> dict[str, Any]:
        pv_kwp = self._runtime_float("pv_installed_kwp", 0.0)

        if pv_kwp <= 0:
            return {
                "installed_kwp": 0.0,
                "expected_w": 0.0,
                "score": 0.0,
                "status": "WYŁĄCZONE",
                "lock": False,
                "reason": "Ustaw moc instalacji PV kWp, aby HomeOn oceniał pogodę z realnej produkcji",
            }

        now = dt_util.now()
        lat = self._as_float(getattr(self.hass.config, "latitude", 52.0), 52.0) or 52.0

        day = int(now.timetuple().tm_yday)
        hour = float(now.hour) + float(now.minute) / 60.0

        lat_rad = math.radians(lat)
        decl_rad = math.radians(23.45 * math.sin(math.radians(360.0 * (284.0 + day) / 365.0)))
        hour_angle_rad = math.radians(15.0 * (hour - 12.0))

        sin_elevation = (
            math.sin(lat_rad) * math.sin(decl_rad)
            + math.cos(lat_rad) * math.cos(decl_rad) * math.cos(hour_angle_rad)
        )

        sun_factor = max(0.0, float(sin_elevation))
        expected_w = max(0.0, pv_kwp * 1000.0 * (sun_factor ** 1.25) * 0.88)

        min_eval_w = max(350.0, pv_kwp * 1000.0 * 0.08)

        if expected_w < min_eval_w:
            return {
                "installed_kwp": round(pv_kwp, 2),
                "expected_w": round(expected_w, 0),
                "score": 0.0,
                "status": "NIE OCENIAM",
                "lock": False,
                "reason": f"Słońce jest za nisko albo jest noc. Oczekiwane PV tylko {expected_w:.0f} W",
            }

        ratio = max(0.0, min(1.5, float(pv_power_w or 0.0) / max(expected_w, 1.0)))
        score = max(0.0, min(100.0, ratio * 100.0))

        if score >= 75.0:
            status = "POGODNIE"
            lock = False
            reason = f"PV pracuje bardzo dobrze: {pv_power_w:.0f} W z oczekiwanych {expected_w:.0f} W"
        elif score >= 50.0:
            status = "DOŚĆ DOBRZE"
            lock = False
            reason = f"PV jest OK: {pv_power_w:.0f} W z oczekiwanych {expected_w:.0f} W"
        elif score >= 35.0:
            status = "SŁABIEJ"
            lock = False
            reason = f"PV słabsze od pogody: {pv_power_w:.0f} W z oczekiwanych {expected_w:.0f} W — ostrożnie"
        else:
            status = "SŁABO / ZACHMURZENIE"
            lock = True
            reason = f"PV dużo poniżej oczekiwań: {pv_power_w:.0f} W z oczekiwanych {expected_w:.0f} W — blokuję agresywne rozładowanie"

        return {
            "installed_kwp": round(pv_kwp, 2),
            "expected_w": round(expected_w, 0),
            "score": round(score, 0),
            "status": status,
            "lock": bool(lock),
            "reason": reason[:240],
        }

    async def _async_apply_inverter_control(self, data: dict[str, Any]) -> dict[str, Any]:
        store = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id, {})

        enabled = bool(store.get("enabled", True))
        dry_run = bool(store.get("dry_run", True))

        # HOMEON_HOME_BATTERY_PRIORITY_EXEC_GUARD
        if str(data.get("home_battery_protection", "OFF")).upper() == "ON" and not bool(store.get("battery_trade", False)):
            data["inverter_control_action"] = "Ochrona domu — bateria zasila gospodarstwo, nie zmieniam nastaw Deye"
            data["inverter_control_executor_mode"] = "BLOCKED_HOME_PRIORITY"
            data["inverter_control_last_result"] = (
                "Pominięto sterowanie: bateria zasila gospodarstwo domowe. "
                "HomeOn nie zmienia trybu Deye ani limitów baterii."
            )
            data["inverter_control_last_run"] = dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
            data["inverter_deye_plan"] = "Zablokowane przez ochronę domu"
            data["inverter_deye_current_states"] = "Bateria zasila gospodarstwo"
            data["inverter_deye_changes"] = "Brak zmian — ochrona domu"
            data["inverter_deye_changed_only"] = "Brak realnych zmian — ochrona domu"
            data["inverter_deye_services"] = "Nie wykonano usług HA"
            data["inverter_deye_command_count"] = 0
            data["inverter_deye_changed_count"] = 0
            data["inverter_deye_unchanged_count"] = 0
            data["inverter_deye_test_mode"] = "BLOCKED — bateria zasila dom"
            return data

        if str(data.get("mode", "")).upper() == "HOME_BATTERY_PRIORITY":
            data["inverter_control_action"] = "Ochrona domu — tryb handlu baterią wyłączony, nie ustawiam Export First"
            data["inverter_control_executor_mode"] = "BLOCKED_BATTERY_TRADE_OFF"
            data["inverter_control_last_result"] = (
                "Pominięto sterowanie: handel baterią jest wyłączony. "
                "HomeOn nie ustawia Export First ani sprzedaży z magazynu."
            )
            data["inverter_control_last_run"] = dt_util.now().strftime("%Y-%m-%d %H:%M:%S")
            data["inverter_deye_plan"] = "Zablokowane — handel baterią OFF"
            data["inverter_deye_current_states"] = "Handel baterią wyłączony"
            data["inverter_deye_changes"] = "Brak zmian — handel baterią OFF"
            data["inverter_deye_changed_only"] = "Brak realnych zmian — handel baterią OFF"
            data["inverter_deye_services"] = "Nie wykonano usług HA"
            data["inverter_deye_command_count"] = 0
            data["inverter_deye_changed_count"] = 0
            data["inverter_deye_unchanged_count"] = 0
            data["inverter_deye_test_mode"] = "BLOCKED — handel baterią OFF"
            return data

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
        inverter_work_mode_select = INVERTER_WORK_MODE_SELECT
        inverter_work_mode_sell_option = INVERTER_WORK_MODE_SELL_OPTION
        inverter_work_mode_state = self.hass.states.get(inverter_work_mode_select)
        inverter_work_mode_current = str(inverter_work_mode_state.state) if inverter_work_mode_state is not None else "BRAK_ENCJI"

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
        data["inverter_entity_work_mode"] = inverter_work_mode_select
        data["inverter_work_mode_current"] = inverter_work_mode_current
        data["inverter_work_mode_target"] = "bez zmiany"
        data["inverter_work_mode_sell_option"] = inverter_work_mode_sell_option

        data["inverter_deye_command_count"] = 0
        data["inverter_deye_changed_count"] = 0
        data["inverter_deye_unchanged_count"] = 0
        data["inverter_deye_plan"] = "Brak komend"
        data["inverter_deye_current_states"] = "Brak komend"
        data["inverter_deye_changes"] = "Brak komend"
        data["inverter_deye_changed_only"] = "Brak realnych zmian"
        data["inverter_deye_services"] = "Brak usług HA"
        data["inverter_deye_test_mode"] = "OFF"

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

        def sel(entity_id: str, option: str) -> None:
            desired.append(("select", str(entity_id), str(option)))

        if mode == "SAFE_MODE":
            executor_mode = "SAFE_MODE"
            action = "SAFE_MODE — błąd danych, blokuję handel i ustawiam bezpieczne ograniczenia"
            sw(inverter_export_surplus, False)
            sw(inverter_grid_charging, False)
            num(inverter_export_surplus_power, 0)
            num(inverter_max_discharge_current, inverter_safe_discharge_current_a)

        elif weather_lock:
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

        elif mode == "PREPARE_NEGATIVE_PRICE_WINDOW":
            neg_energy_to_free_kwh = self._as_float(data.get("negative_price_energy_to_free_kwh"), 0.0) or 0.0
            neg_export_w = self._as_float(data.get("negative_price_prepare_export_w"), inverter_export_target_w) or inverter_export_target_w
            neg_export_w = min(inverter_export_target_w, max(500.0, float(neg_export_w)))
            action = "Przygotowanie przed ceną ujemną — zwalniam %.2f kWh w magazynie, limit eksportu %.0f W" % (neg_energy_to_free_kwh, neg_export_w)
            data["inverter_work_mode_target"] = inverter_work_mode_sell_option
            sel(inverter_work_mode_select, inverter_work_mode_sell_option)
            sw(inverter_grid_charging, False)
            num(inverter_export_surplus_power, neg_export_w)
            num(inverter_max_discharge_current, inverter_discharge_current_a)
            sw(inverter_export_surplus, True)

        elif mode == "NEGATIVE_PRICE_EXPORT_BLOCK":
            executor_mode = "NEGATIVE_PRICE_EXPORT_BLOCK"
            action = "Cena sprzedaży ujemna — blokuję sprzedaż i eksport z baterii"
            sw(inverter_export_surplus, False)
            sw(inverter_grid_charging, False)
            num(inverter_export_surplus_power, 0)
            num(inverter_max_discharge_current, inverter_safe_discharge_current_a)

        elif mode in ("NEGATIVE_IMPORT", "CHEAP_CHARGE"):
            action = "Tania energia — ładuję magazyn z sieci, eksport baterii zablokowany"
            sw(inverter_export_surplus, False)
            sw(inverter_grid_charging, True)
            num(inverter_max_charge_current, inverter_charge_current_a)
            num(inverter_max_discharge_current, inverter_block_discharge_current_a)

        elif mode == "SELL_BATTERY_HIGH_PRICE" and safe_export_limit_w > 0 and plan_safe_to_sell_kwh > 0.3:
            action = "Sprzedaż tylko bezpiecznej nadwyżki: %.2f kWh, limit eksportu %.0f W" % (plan_safe_to_sell_kwh, safe_export_limit_w)
            data["inverter_work_mode_target"] = inverter_work_mode_sell_option
            sel(inverter_work_mode_select, inverter_work_mode_sell_option)
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

        elif mode == "PV_REALITY_HOLD":
            action = "Realna produkcja PV jest słaba — blokuję sprzedaż i ograniczam rozładowanie magazynu"
            sw(inverter_grid_charging, False)
            sw(inverter_export_surplus, False)
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
        change_preview = []
        changed_preview = []
        unchanged_preview = []
        service_preview = []
        current_preview = []

        def _short(text: str, limit: int = 240) -> str:
            text = str(text or "")
            return text if len(text) <= limit else text[: limit - 3] + "..."

        def _current_state(entity_id: str) -> str:
            state = self.hass.states.get(entity_id)
            if state is None:
                return "BRAK_ENCJI"
            return str(state.state)

        def _target_state(domain: str, value: Any) -> str:
            if domain == "switch":
                return "on" if bool(value) else "off"
            if domain == "select":
                return str(value)
            try:
                return "%g" % float(value)
            except Exception:
                return str(value)

        def _display_target(domain: str, value: Any) -> str:
            if domain == "switch":
                return "ON" if bool(value) else "OFF"
            if domain == "select":
                return str(value)
            try:
                return "%g" % float(value)
            except Exception:
                return str(value)

        def _same_state(domain: str, current: str, value: Any) -> bool:
            if current == "BRAK_ENCJI":
                return False
            if domain == "switch":
                wanted = bool(value)
                current_bool = str(current).lower() in ("on", "true", "1")
                return current_bool == wanted
            if domain == "select":
                return str(current).strip().lower() == str(value).strip().lower()
            if domain == "number":
                try:
                    return abs(float(str(current).replace(",", ".")) - float(value)) <= 0.05
                except Exception:
                    return False
            return False

        for domain, entity_id, value in desired:
            current = _current_state(entity_id)
            target = _target_state(domain, value)
            target_display = _display_target(domain, value)
            same = _same_state(domain, current, value)

            preview.append(entity_id + ": " + target_display)
            current_preview.append(entity_id + "=" + current)

            flag = "BEZ ZMIAN" if same else "ZMIANA"
            line = entity_id + ": " + current + " -> " + target + " (" + flag + ")"
            change_preview.append(line)

            if same:
                unchanged_preview.append(line)
            else:
                changed_preview.append(line)

            if domain == "switch":
                service = "switch." + ("turn_on" if bool(value) else "turn_off") + " entity_id=" + entity_id
            elif domain == "number":
                service = "number.set_value entity_id=" + entity_id + " value=" + target
            elif domain == "select":
                service = "select.select_option entity_id=" + entity_id + " option=" + target
            else:
                service = domain + " " + entity_id + " " + target

            service_preview.append(service)

        data["inverter_deye_command_count"] = len(desired)
        data["inverter_deye_changed_count"] = len(changed_preview)
        data["inverter_deye_unchanged_count"] = len(unchanged_preview)

        data["inverter_deye_plan"] = _short(" | ".join(preview))
        data["inverter_deye_current_states"] = _short(" | ".join(current_preview))
        data["inverter_deye_changes"] = _short(" | ".join(change_preview))
        data["inverter_deye_changed_only"] = _short(
            " | ".join(changed_preview)
            if changed_preview
            else "Brak realnych zmian - Deye ma już takie nastawy"
        )
        data["inverter_deye_services"] = _short(" | ".join(service_preview))

        if dry_run:
            data["inverter_deye_test_mode"] = "DRY-RUN - tylko pokazuje, nic nie zapisuje do Deye"
        else:
            data["inverter_deye_test_mode"] = "REAL - komendy moga byc zapisane do Deye"
        if dry_run:
            data["inverter_deye_test_mode"] = "DRY-RUN — tylko pokazuję, nic nie zapisuję do Deye"
        else:
            data["inverter_deye_test_mode"] = "REAL — komendy mogą być zapisane do Deye"
        if dry_run:
            data["inverter_control_last_result"] = "DRY-RUN: " + str(data.get("inverter_deye_changes", " | ".join(preview)))
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
            elif domain == "select":
                await self._async_set_select(entity_id, str(value), actions)

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

        # HOMEON_DATA_QUALITY_START
        data_quality_errors: list[str] = []
        data_quality_warnings: list[str] = []

        def _check_required_number(label: str, key: str, min_v: float | None = None, max_v: float | None = None) -> float | None:
            entity_id = self.entry.data.get(key)

            if not entity_id:
                data_quality_errors.append(f"{label}: brak konfiguracji encji")
                return None

            state = self.hass.states.get(entity_id)

            if state is None:
                data_quality_errors.append(f"{label}: brak encji {entity_id}")
                return None

            raw = state.state

            if raw in (None, "", "unknown", "unavailable", "none", "None", "null"):
                data_quality_errors.append(f"{label}: stan {raw}")
                return None

            value = self._as_float(raw, None)

            if value is None:
                data_quality_errors.append(f"{label}: nie jest liczbą ({raw})")
                return None

            if min_v is not None and value < min_v:
                data_quality_errors.append(f"{label}: za mało {value:g} < {min_v:g}")
                return value

            if max_v is not None and value > max_v:
                data_quality_errors.append(f"{label}: za dużo {value:g} > {max_v:g}")
                return value

            return value

        _check_required_number("SOC", CONF_SOC_SENSOR, 0.0, 100.0)
        _check_required_number("Moc baterii", CONF_BATTERY_POWER_SENSOR, -200000.0, 200000.0)
        _check_required_number("Moc PV", CONF_PV_POWER_SENSOR, -1000.0, 200000.0)
        _check_required_number("Moc domu", CONF_LOAD_POWER_SENSOR, 0.0, 200000.0)
        _check_required_number("Moc sieci", CONF_GRID_POWER_SENSOR, -200000.0, 200000.0)
        _check_required_number("Cena zakupu", CONF_BUY_PRICE_SENSOR, -5.0, 5.0)
        _check_required_number("Cena sprzedaży", CONF_SELL_PRICE_SENSOR, -5.0, 5.0)

        if battery_capacity_kwh <= 0:
            data_quality_errors.append(f"Pojemność magazynu jest niepoprawna: {battery_capacity_kwh:g} kWh")

        if min_soc < 0 or min_soc > 100:
            data_quality_errors.append(f"Minimalny SOC poza zakresem: {min_soc:g}%")

        if emergency_soc < 0 or emergency_soc > 100:
            data_quality_errors.append(f"Awaryjny SOC poza zakresem: {emergency_soc:g}%")

        if emergency_soc > min_soc:
            data_quality_warnings.append("Awaryjny SOC jest wyższy niż minimalny SOC")

        if abs(pv_power) > 100 and pv_power < 0:
            data_quality_warnings.append(f"Moc PV jest ujemna: {pv_power:.0f} W")

        if buy_price == 0 and sell_price == 0:
            data_quality_warnings.append("Cena zakupu i sprzedaży wynosi 0 — sprawdź sensor taryfy")

        data_quality_score = max(
            0.0,
            min(
                100.0,
                100.0 - len(data_quality_errors) * 25.0 - len(data_quality_warnings) * 8.0,
            ),
        )

        safe_mode_active = bool(data_quality_errors)

        if safe_mode_active:
            data_quality_status = "BŁĄD"
            safe_mode_reason = " | ".join(data_quality_errors)[:240]
            safe_mode_action = "Blokuję handel baterią i wymuszone sterowanie. Dozwolone tylko bezpieczne ograniczenia falownika."
        elif data_quality_warnings:
            data_quality_status = "OSTRZEŻENIE"
            safe_mode_reason = "Brak aktywnego SAFE_MODE"
            safe_mode_action = "Dane działają, ale wymagają kontroli: " + " | ".join(data_quality_warnings)[:180]
        else:
            data_quality_status = "OK"
            safe_mode_reason = "Brak błędów danych"
            safe_mode_action = "Normalna praca EMS"

        if not safe_mode_active:
            self._homeon_last_data_ok = dt_util.now().strftime("%Y-%m-%d %H:%M:%S")

        data_quality_last_ok = getattr(self, "_homeon_last_data_ok", "-")
        # HOMEON_DATA_QUALITY_END

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



        # HOMEON_HOME_BATTERY_PRIORITY_START
        battery_trade_enabled = bool(store.get("battery_trade", False))
        home_battery_load_w = min(max(load_power, 0.0), max(battery_discharge_w, 0.0))
        home_battery_protection_active = bool(home_battery_load_w > 250.0 and load_power > 300.0)

        if home_battery_protection_active:
            home_battery_protection_reason = (
                f"Bateria aktualnie zasila gospodarstwo domowe: około {home_battery_load_w:.0f} W. "
                "HomeOn nie zmienia nastaw baterii ani trybu Deye, aby nie zaburzyć autokonsumpcji."
            )
        elif not battery_trade_enabled:
            home_battery_protection_reason = (
                "Tryb handlu baterią jest wyłączony — HomeOn nie będzie sprzedawał energii z magazynu."
            )
        else:
            home_battery_protection_reason = (
                "Ochrona domu nie blokuje sterowania — bateria nie zasila teraz istotnie gospodarstwa "
                "albo handel baterią jest świadomie włączony."
            )
        # HOMEON_HOME_BATTERY_PRIORITY_END
        night_reserve_soc = max(
            min_night_reserve_soc,
            min(100.0, (night_consumption_kwh * night_safety_margin / max(battery_capacity_kwh, 0.1)) * 100.0),
        )

        # HOMEON_ADAPTIVE_TARGETS_START
        learn = getattr(self, "_homeon_learning", {})
        if not isinstance(learn, dict):
            learn = {}

        learning_hours = self._as_float(learn.get("runtime_hours"), 0.0) or 0.0
        learning_weight = min(1.0, max(0.0, learning_hours / 24.0))

        avg_load_w = self._as_float(learn.get("avg_load_w"), load_power) or load_power
        avg_night_load_w = self._as_float(learn.get("avg_night_load_w"), avg_load_w) or avg_load_w

        configured_night_kwh = max(0.0, night_consumption_kwh * night_safety_margin)
        learned_night_kwh = max(0.0, avg_night_load_w * 8.0 / 1000.0 * night_safety_margin)

        target_expected_night_consumption_kwh = (
            configured_night_kwh * (1.0 - learning_weight)
            + learned_night_kwh * learning_weight
        )

        fallback_daily_kwh = max(
            night_consumption_kwh * 2.4,
            max(0.0, load_power) * 24.0 / 1000.0,
        )

        learned_daily_kwh = max(0.0, avg_load_w * 24.0 / 1000.0)

        target_expected_24h_consumption_kwh = (
            fallback_daily_kwh * (1.0 - learning_weight)
            + learned_daily_kwh * learning_weight
        )

        pv_coverage_ratio = pv_tomorrow / max(target_expected_24h_consumption_kwh, 0.1)

        if pv_coverage_ratio >= 1.15:
            target_weather_class = "PV bardzo dobre"
            weather_factor = 0.10
            pv_target_soc = 58.0
        elif pv_coverage_ratio >= 0.80:
            target_weather_class = "PV dobre"
            weather_factor = 0.30
            pv_target_soc = 68.0
        elif pv_coverage_ratio >= 0.45:
            target_weather_class = "PV średnie"
            weather_factor = 0.60
            pv_target_soc = 80.0
        else:
            target_weather_class = "PV słabe"
            weather_factor = 1.00
            pv_target_soc = 90.0

        tomorrow_deficit_kwh = max(0.0, target_expected_24h_consumption_kwh - pv_tomorrow)

        target_required_reserve_kwh = (
            target_expected_night_consumption_kwh
            + tomorrow_deficit_kwh * weather_factor
            + 1.0
        )

        target_required_reserve_kwh = min(
            max(target_required_reserve_kwh, 0.0),
            battery_capacity_kwh,
        )

        night_reserve_soc = max(
            min_night_reserve_soc,
            target_expected_night_consumption_kwh / max(battery_capacity_kwh, 0.1) * 100.0,
        )

        night_reserve_soc = min(
            95.0,
            max(min_soc, night_reserve_soc),
        )

        target_required_reserve_soc = target_required_reserve_kwh / max(battery_capacity_kwh, 0.1) * 100.0

        discharge_target_soc = min(
            95.0,
            max(min_soc, night_reserve_soc, target_required_reserve_soc),
        )

        morning_target_soc = min(
            95.0,
            max(night_reserve_soc, discharge_target_soc),
        )

        charge_target_soc = min(
            95.0,
            max(morning_target_soc + 5.0, pv_target_soc),
        )

        target_pv_coverage_percent = min(300.0, max(0.0, pv_coverage_ratio * 100.0))

        if learning_weight >= 0.80:
            target_source = "Nauka EMS"
        elif learning_weight > 0.05:
            target_source = "Nauka EMS + konfiguracja"
        else:
            target_source = "Konfiguracja startowa"

        target_reason = (
            f"{target_weather_class}: PV jutro {pv_tomorrow:.1f} kWh, "
            f"prognoza zużycia {target_expected_24h_consumption_kwh:.1f} kWh, "
            f"noc {target_expected_night_consumption_kwh:.1f} kWh, "
            f"rezerwa {target_required_reserve_kwh:.1f} kWh, "
            f"cel ładowania {charge_target_soc:.0f}%"
        )[:240]
        # HOMEON_ADAPTIVE_TARGETS_END

        # HOMEON_PV_REALITY_START
        pv_reality = self._pv_reality_data(pv_power)
        pv_reality_lock = bool(pv_reality.get("lock", False))

        if pv_reality_lock:
            discharge_target_soc = min(
                95.0,
                max(discharge_target_soc, night_reserve_soc, 75.0),
            )
            morning_target_soc = min(
                95.0,
                max(morning_target_soc, discharge_target_soc),
            )
            charge_target_soc = min(
                95.0,
                max(charge_target_soc, morning_target_soc + 5.0, 85.0),
            )
            target_reason = (
                target_reason
                + " | Korekta z realnej produkcji PV: "
                + str(pv_reality.get("reason", "PV słabe"))
            )[:240]
        # HOMEON_PV_REALITY_END

        # HOMEON_NEGATIVE_PRICE_WINDOW_START
        negative_price_plan = self._negative_price_plan(
            self.entry.data.get(CONF_BUY_PRICE_SENSOR),
            buy_price,
            sell_price,
            soc,
            battery_capacity_kwh,
            load_power,
            avg_load_w,
            pv_reality,
            battery_trade_enabled,
            sell_stats,
        )
        # HOMEON_NEGATIVE_PRICE_WINDOW_END

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

        sell_ready = sell_price >= 0.55 and soc > discharge_target_soc + 8 and not pv_reality_lock and battery_trade_enabled and not negative_price_plan.get("now", False) and sell_price > 0.0

        if not enabled:
            mode = "DISABLED"
            reason = "HomeOn EMS jest wyłączony"
        elif safe_mode_active:
            mode = "SAFE_MODE"
            reason = safe_mode_reason
        elif soc <= emergency_soc:
            mode = "EMERGENCY_RESERVE"
            reason = "SOC jest poniżej poziomu awaryjnego"
        elif negative_price_plan.get("now", False) and soc < 100:
            mode = "NEGATIVE_IMPORT"
            reason = str(negative_price_plan.get("reason", "Cena ujemna — ładuję magazyn i blokuję eksport"))
        elif negative_price_plan.get("prepare", False):
            mode = "PREPARE_NEGATIVE_PRICE_WINDOW"
            reason = str(negative_price_plan.get("reason", "Przygotowuję magazyn przed ceną ujemną"))
        elif negative_price_plan.get("sell_block", False):
            mode = "NEGATIVE_PRICE_EXPORT_BLOCK"
            reason = str(negative_price_plan.get("reason", "Cena sprzedaży ujemna — blokuję eksport"))
        elif buy_price <= 0 and soc < 100:
            mode = "NEGATIVE_IMPORT"
            reason = "Cena zakupu jest ujemna lub zerowa — opłaca się ładować"
        elif buy_price < 0.30 and soc < charge_target_soc:
            mode = "CHEAP_CHARGE"
            reason = "Tania energia — można ładować magazyn"
        elif home_battery_protection_active:
            mode = "HOME_BATTERY_PRIORITY"
            reason = home_battery_protection_reason
        elif not battery_trade_enabled and sell_price >= 0.55 and soc > discharge_target_soc + 8:
            mode = "HOME_BATTERY_PRIORITY"
            reason = "Tryb handlu baterią jest wyłączony — nie sprzedaję energii z magazynu, bateria zostaje dla domu"
        elif pv_reality_lock and soc > min_soc:
            mode = "PV_REALITY_HOLD"
            reason = str(pv_reality.get("reason", "PV realnie słabe — chronię magazyn"))
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

            "data_quality_status": data_quality_status,
            "data_quality_score": round(data_quality_score, 0),
            "data_quality_errors": " | ".join(data_quality_errors)[:240] if data_quality_errors else "Brak",
            "data_quality_warnings": " | ".join(data_quality_warnings)[:240] if data_quality_warnings else "Brak",
            "data_quality_last_ok": data_quality_last_ok,
            "safe_mode": "ON" if safe_mode_active else "OFF",
            "safe_mode_reason": safe_mode_reason,
            "safe_mode_action": safe_mode_action,

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

            "target_source": target_source,
            "target_learning_weight": round(learning_weight * 100.0, 0),
            "target_expected_night_consumption_kwh": round(target_expected_night_consumption_kwh, 2),
            "target_expected_24h_consumption_kwh": round(target_expected_24h_consumption_kwh, 2),
            "target_pv_coverage_percent": round(target_pv_coverage_percent, 0),
            "target_required_reserve_kwh": round(target_required_reserve_kwh, 2),
            "target_reason": target_reason,

            "pv_reality_status": pv_reality.get("status", "—"),
            "pv_reality_score": pv_reality.get("score", 0),
            "pv_reality_expected_w": pv_reality.get("expected_w", 0),
            "pv_reality_lock": "ON" if pv_reality_lock else "OFF",
            "pv_reality_reason": pv_reality.get("reason", "—"),
            "pv_reality_installed_kwp": pv_reality.get("installed_kwp", 0),

            "available_to_sell_kwh": round(available_to_sell_kwh, 2),
            "free_space_kwh": round(free_space_kwh, 2),
            "energy_to_charge_target_kwh": round(energy_to_charge_target_kwh, 2),
            "energy_above_morning_target_kwh": round(energy_above_morning_target_kwh, 2),

            "deye_self_power": round(deye_self_power, 0),
            "battery_discharge_w": round(battery_discharge_w, 0),
            "battery_charge_w": round(battery_charge_w, 0),
            "grid_import_w": round(grid_import_w, 0),
            "grid_export_w": round(grid_export_w, 0),

            "battery_trade_enabled": "ON" if battery_trade_enabled else "OFF",
            "home_battery_protection": "ON" if home_battery_protection_active else "OFF",
            "home_battery_load_w": round(home_battery_load_w, 0),
            "home_battery_protection_reason": home_battery_protection_reason[:240],

            "negative_price_window_status": negative_price_plan.get("status", "BRAK"),
            "negative_price_window_start": negative_price_plan.get("start", "-"),
            "negative_price_window_end": negative_price_plan.get("end", "-"),
            "negative_price_min_buy_price": negative_price_plan.get("min_price", 0.0),
            "negative_price_energy_to_free_kwh": negative_price_plan.get("energy_to_free_kwh", 0.0),
            "negative_price_required_free_kwh": negative_price_plan.get("required_free_kwh", 0.0),
            "negative_price_target_soc_before": negative_price_plan.get("target_soc_before", 100.0),
            "negative_price_prepare_export_w": negative_price_plan.get("prepare_export_w", 0.0),
            "negative_price_strategy": negative_price_plan.get("strategy", "—"),
            "negative_price_reason": negative_price_plan.get("reason", "—"),
        }

        data.update(sell_stats)
        data = await update_learning(self, data)
        data = build_planner_data(self, data)
        data = await self._async_apply_inverter_control(data)
        return data
