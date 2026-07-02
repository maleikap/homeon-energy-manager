from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    CONF_BUY_PRICE_SENSOR,
    CONF_SELL_PRICE_SENSOR,
    CONF_BATTERY_CAPACITY_KWH,
    DEFAULT_BATTERY_CAPACITY_KWH,
)


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return default
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _hour_label(dt) -> str:
    return dt_util.as_local(dt).strftime("%H:00")


def _series_from_entity(coordinator, entity_id: str | None, fallback_price: float) -> dict[str, float]:
    now = dt_util.now()
    end = now + timedelta(hours=24)
    result: dict[str, float] = {}

    if entity_id:
        state = coordinator.hass.states.get(entity_id)

        if state is not None:
            points: list[dict[str, Any]] = []
            coordinator._extract_price_points(dict(state.attributes), points)

            for item in points:
                dt = item.get("dt")
                price = _f(item.get("price"), None)

                if dt is None or price is None:
                    continue

                local_dt = dt_util.as_local(dt)

                if local_dt < now - timedelta(minutes=30):
                    continue

                if local_dt > end:
                    continue

                if price < -5 or price > 5:
                    continue

                key = local_dt.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H")
                result[key] = float(price)

    if not result:
        base = now.replace(minute=0, second=0, microsecond=0)
        for i in range(24):
            dt = base + timedelta(hours=i)
            result[dt.strftime("%Y-%m-%d %H")] = float(fallback_price)

    return result


def _price_for(series: dict[str, float], dt, fallback: float) -> float:
    key = dt.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H")
    return float(series.get(key, fallback))


def _best_hour(hours: list[dict[str, Any]], key: str, reverse: bool) -> dict[str, Any]:
    if not hours:
        return {}
    return sorted(hours, key=lambda x: x.get(key, 0.0), reverse=reverse)[0]


def _phase(hour: int) -> str:
    if 0 <= hour < 6:
        return "Noc / rezerwa"
    if 6 <= hour < 10:
        return "Poranek"
    if 10 <= hour < 16:
        return "Okno PV"
    if 16 <= hour < 22:
        return "Szczyt wieczorny"
    return "Noc / rezerwa"


def build_planner_data(coordinator, data: dict[str, Any]) -> dict[str, Any]:
    now = dt_util.now()
    base = now.replace(minute=0, second=0, microsecond=0)

    buy_price_now = _f(data.get("buy_price"), 0.0)
    sell_price_now = _f(data.get("sell_price"), 0.0)
    soc = _f(data.get("soc"), 0.0)

    battery_capacity = _f(
        coordinator.entry.data.get(CONF_BATTERY_CAPACITY_KWH),
        DEFAULT_BATTERY_CAPACITY_KWH,
    )

    charge_target_soc = _f(data.get("charge_target_soc"), 75.0)
    discharge_target_soc = _f(data.get("discharge_target_soc"), 25.0)
    night_reserve_soc = _f(data.get("night_reserve_soc"), 30.0)
    morning_target_soc = _f(data.get("morning_target_soc"), 60.0)
    available_to_sell_kwh = _f(data.get("available_to_sell_kwh"), 0.0)

    buy_series = _series_from_entity(
        coordinator,
        coordinator.entry.data.get(CONF_BUY_PRICE_SENSOR),
        buy_price_now,
    )

    sell_series = _series_from_entity(
        coordinator,
        coordinator.entry.data.get(CONF_SELL_PRICE_SENSOR),
        sell_price_now,
    )

    learn = getattr(coordinator, "_homeon_learning", {})
    if not isinstance(learn, dict):
        learn = {}

    hourly_profile = learn.get("hourly_profile")
    if not isinstance(hourly_profile, dict):
        hourly_profile = {}

    avg_load_w = _f(learn.get("avg_load_w"), _f(data.get("load_power"), 0.0))
    avg_night_w = _f(learn.get("avg_night_load_w"), avg_load_w)

    hours: list[dict[str, Any]] = []

    for i in range(24):
        dt = base + timedelta(hours=i)
        hk = f"{dt.hour:02d}"

        bucket = hourly_profile.get(hk)
        if not isinstance(bucket, dict):
            bucket = {}

        expected_load_w = _f(bucket.get("avg_load_w"), avg_load_w)
        expected_pv_w = _f(bucket.get("avg_pv_w"), 0.0)

        buy = _price_for(buy_series, dt, buy_price_now)
        sell = _price_for(sell_series, dt, sell_price_now)

        hours.append({
            "dt": dt,
            "hour": _hour_label(dt),
            "clock_hour": dt.hour,
            "buy": buy,
            "sell": sell,
            "load_w": expected_load_w,
            "pv_w": expected_pv_w,
        })

    cheapest = _best_hour(hours, "buy", False)
    best_sell = _best_hour(hours, "sell", True)

    cheapest_buy = _f(cheapest.get("buy"), buy_price_now)
    best_sell_price = _f(best_sell.get("sell"), sell_price_now)

    night_need_kwh = 0.0
    day_need_kwh = 0.0

    for item in hours:
        h = int(item["clock_hour"])
        load_kwh = _f(item.get("load_w"), avg_load_w) / 1000.0

        day_need_kwh += load_kwh

        if h >= 22 or h < 6:
            night_need_kwh += load_kwh

    if night_need_kwh <= 0:
        night_need_kwh = avg_night_w * 8.0 / 1000.0

    night_soc_need = min(100.0, max(0.0, night_need_kwh / max(battery_capacity, 0.1) * 100.0))
    recommended_soc = max(night_reserve_soc, night_soc_need + 8.0)

    current_phase = _phase(now.hour)
    current_mode = str(data.get("mode", "NORMAL"))

    charge_window = f"{cheapest.get('hour', '-')} ({cheapest_buy:.3f} PLN/kWh)"
    sell_window = f"{best_sell.get('hour', '-')} ({best_sell_price:.3f} PLN/kWh)"

    next_action = "Normalna praca"
    next_time = "teraz"
    reason = "Brak mocniejszego sygnału z cen, PV lub profilu zużycia."
    hold_reason = "Brak potrzeby blokowania energii."

    if current_mode == "EMERGENCY_RESERVE":
        next_action = "Ładowanie awaryjne"
        next_time = "teraz"
        reason = "SOC jest poniżej poziomu awaryjnego."
        recommended_soc = max(recommended_soc, charge_target_soc)

    elif buy_price_now <= cheapest_buy + 0.005 and soc < charge_target_soc:
        next_action = "Ładowanie z taniej energii"
        next_time = "teraz"
        reason = f"Aktualna cena zakupu jest w najtańszym oknie 24h: {buy_price_now:.3f} PLN/kWh."
        recommended_soc = charge_target_soc

    elif cheapest_buy + 0.04 < buy_price_now and soc < charge_target_soc:
        next_action = "Czekaj na tańsze ładowanie"
        next_time = str(cheapest.get("hour", "-"))
        reason = f"Najtańsze okno zakupu jest o {cheapest.get('hour', '-')} przy cenie {cheapest_buy:.3f} PLN/kWh."
        hold_reason = "Nie ładuję teraz, bo w planie jest tańsza energia."

    elif sell_price_now >= best_sell_price - 0.005 and available_to_sell_kwh > 0.3 and soc > discharge_target_soc + 4:
        next_action = "Sprzedaż nadwyżki"
        next_time = "teraz"
        reason = f"Teraz jest najlepsza lub prawie najlepsza cena sprzedaży: {sell_price_now:.3f} PLN/kWh."
        recommended_soc = discharge_target_soc

    elif best_sell_price > sell_price_now + 0.02 and available_to_sell_kwh > 0.3:
        next_action = "Trzymaj energię do sprzedaży"
        next_time = str(best_sell.get("hour", "-"))
        reason = f"Lepsza sprzedaż planowana o {best_sell.get('hour', '-')} przy cenie {best_sell_price:.3f} PLN/kWh."
        hold_reason = "Bateria ma wartość rynkową — warto poczekać na wyższą cenę."

    elif current_phase == "Okno PV" and soc > morning_target_soc:
        next_action = "Zostaw miejsce na PV"
        next_time = "teraz"
        reason = "Jest okno produkcji PV, więc EMS pilnuje miejsca w magazynie."
        recommended_soc = min(soc, charge_target_soc)

    elif current_phase == "Noc / rezerwa":
        next_action = "Pilnuj rezerwy nocnej"
        next_time = "teraz"
        reason = f"Szacowane zużycie nocne: {night_need_kwh:.2f} kWh."
        recommended_soc = max(recommended_soc, night_reserve_soc)

    elif buy_price_now >= 0.55 and soc > discharge_target_soc:
        next_action = "Autokonsumpcja z baterii"
        next_time = "teraz"
        reason = "Zakup energii jest drogi, więc opłaca się używać baterii na dom."
        recommended_soc = max(discharge_target_soc, recommended_soc)

    plan_overview = (
        f"{next_action}. Tani zakup: {charge_window}. "
        f"Sprzedaż: {sell_window}. Noc: {night_need_kwh:.2f} kWh."
    )

    data.update({
        "plan_now_phase": current_phase,
        "plan_recommended_soc": round(min(100.0, max(0.0, recommended_soc)), 1),
        "plan_next_action": next_action,
        "plan_next_action_time": next_time,
        "plan_next_action_reason": reason,
        "plan_charge_window": charge_window,
        "plan_sell_window": sell_window,
        "plan_hold_reason": hold_reason,
        "plan_expected_night_consumption_kwh": round(night_need_kwh, 2),
        "plan_expected_day_consumption_kwh": round(day_need_kwh, 2),
        "plan_cheapest_buy_price": round(cheapest_buy, 3),
        "plan_best_sell_price": round(best_sell_price, 3),
        "plan_overview": plan_overview[:240],
    })

    return data
