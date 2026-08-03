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


def _weather_label(pv_tomorrow_kwh: float, expected_24h_kwh: float) -> tuple[str, float]:
    expected = max(expected_24h_kwh, 0.1)
    ratio = pv_tomorrow_kwh / expected

    if ratio >= 1.15:
        return "Bardzo dobra produkcja PV", 0.15

    if ratio >= 0.80:
        return "Dobra produkcja PV", 0.35

    if ratio >= 0.45:
        return "Średnia produkcja PV", 0.65

    return "Słaba produkcja PV", 1.00


def build_planner_data(coordinator, data: dict[str, Any]) -> dict[str, Any]:
    now = dt_util.now()
    base = now.replace(minute=0, second=0, microsecond=0)

    buy_price_now = _f(data.get("buy_price"), 0.0)
    sell_price_now = _f(data.get("sell_price"), 0.0)
    soc = _f(data.get("soc"), 0.0)

    battery_capacity = _f(
        data.get(
            "battery_capacity_kwh",
            coordinator.entry.data.get(CONF_BATTERY_CAPACITY_KWH),
        ),
        DEFAULT_BATTERY_CAPACITY_KWH,
    )

    charge_target_soc = _f(data.get("charge_target_soc"), 75.0)
    discharge_target_soc = _f(data.get("discharge_target_soc"), 25.0)
    night_reserve_soc = _f(data.get("night_reserve_soc"), 30.0)
    morning_target_soc = _f(data.get("morning_target_soc"), 60.0)
    available_to_sell_kwh = _f(data.get("available_to_sell_kwh"), 0.0)
    pv_today_kwh = _f(
        data.get("pv_forecast_today_calibrated"),
        _f(data.get("pv_forecast_today"), 0.0),
    )
    pv_tomorrow_kwh = _f(
        data.get("pv_forecast_tomorrow_calibrated"),
        _f(data.get("pv_forecast_tomorrow"), 0.0),
    )
    charge_efficiency = min(1.0, max(0.50, coordinator._runtime_float("battery_charge_efficiency_percent", 94.0) / 100.0))
    discharge_efficiency = min(1.0, max(0.50, coordinator._runtime_float("battery_discharge_efficiency_percent", 94.0) / 100.0))
    battery_voltage_v = max(12.0, coordinator._runtime_float("battery_nominal_voltage_v", 51.2))
    max_export_w = max(0.0, coordinator._runtime_float("inverter_export_target_w", 10000.0))
    discharge_current_a = max(0.0, coordinator._runtime_float("inverter_discharge_current_a", 120.0))
    discharge_power_kw = min(max_export_w / 1000.0, discharge_current_a * battery_voltage_v / 1000.0)
    cycle_cost = max(0.0, coordinator._runtime_float("economic_battery_cycle_cost", 0.15))

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

    raw_pv_kwh = sum(max(0.0, _f(item.get("pv_w"), 0.0)) / 1000.0 for item in hours)
    forecast_24h_kwh = max(0.0, pv_today_kwh + pv_tomorrow_kwh)
    pv_profile_scale = 1.0

    if raw_pv_kwh > 0.2 and forecast_24h_kwh > 0:
        pv_profile_scale = min(5.0, max(0.20, forecast_24h_kwh / raw_pv_kwh))

    for item in hours:
        item["pv_w"] = max(0.0, _f(item.get("pv_w"), 0.0) * pv_profile_scale)
        item["load_kwh"] = max(0.0, _f(item.get("load_w"), 0.0) / 1000.0)
        item["pv_kwh"] = max(0.0, _f(item.get("pv_w"), 0.0) / 1000.0)
        item["pv_surplus_kwh"] = max(0.0, item["pv_kwh"] - item["load_kwh"])

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

    weather_tomorrow, weather_safety_factor = _weather_label(pv_tomorrow_kwh, day_need_kwh)

    next_day_energy_balance_kwh = pv_tomorrow_kwh - day_need_kwh
    tomorrow_deficit_kwh = max(0.0, day_need_kwh - pv_tomorrow_kwh)

    reasonable_buy_threshold = max(cheapest_buy + 0.08, 0.35)
    reasonable_buy_threshold = min(reasonable_buy_threshold, 0.55)

    reasonable_buy_hour = cheapest

    for item in hours:
        if _f(item.get("buy"), 9.0) <= reasonable_buy_threshold:
            reasonable_buy_hour = item
            break

    reasonable_buy_dt = reasonable_buy_hour.get("dt", cheapest.get("dt", base))
    reasonable_buy_window = f"{reasonable_buy_hour.get('hour', '-')} ({_f(reasonable_buy_hour.get('buy'), cheapest_buy):.3f} PLN/kWh)"

    load_until_reasonable_buy_kwh = 0.0

    for item in hours:
        dt = item.get("dt")
        if dt is None:
            continue

        if dt <= reasonable_buy_dt:
            load_until_reasonable_buy_kwh += _f(item.get("load_w"), avg_load_w) / 1000.0

    if load_until_reasonable_buy_kwh <= 0:
        load_until_reasonable_buy_kwh = night_need_kwh

    base_keep_kwh = max(night_need_kwh, load_until_reasonable_buy_kwh)
    weather_keep_kwh = tomorrow_deficit_kwh * weather_safety_factor

    energy_to_keep_kwh = base_keep_kwh + weather_keep_kwh + 1.0
    energy_to_keep_kwh = min(max(energy_to_keep_kwh, 0.0), battery_capacity)

    current_battery_energy_kwh = battery_capacity * soc / 100.0

    safe_to_sell_kwh = max(0.0, current_battery_energy_kwh - energy_to_keep_kwh)
    safe_to_sell_kwh = min(safe_to_sell_kwh, available_to_sell_kwh)

    safe_min_soc = 100.0 * energy_to_keep_kwh / max(battery_capacity, 0.1)
    safe_min_soc = min(100.0, max(night_reserve_soc, safe_min_soc))

    profitable_sell_floor = max(cycle_cost / max(discharge_efficiency, 0.01), best_sell_price * 0.90)
    sell_hours = [
        item for item in hours
        if _f(item.get("sell"), 0.0) >= profitable_sell_floor
        and _f(item.get("sell"), 0.0) > cycle_cost
    ]
    sell_window_hours = max(1.0, float(len(sell_hours))) if sell_hours else 0.0
    sell_window_capacity_kwh = max(0.0, discharge_power_kw * sell_window_hours * discharge_efficiency)
    feasible_sale_kwh = min(safe_to_sell_kwh, sell_window_capacity_kwh)
    required_sale_hours = (
        feasible_sale_kwh / max(discharge_power_kw * discharge_efficiency, 0.1)
        if feasible_sale_kwh > 0
        else 0.0
    )
    best_sell_dt = best_sell.get("dt", base)
    recommended_sell_start_dt = best_sell_dt - timedelta(hours=required_sale_hours)

    future_pv_surplus_kwh = sum(_f(item.get("pv_surplus_kwh"), 0.0) for item in hours)
    planned_market_energy_kwh = min(
        max(0.0, battery_capacity - energy_to_keep_kwh),
        max(feasible_sale_kwh, min(future_pv_surplus_kwh * charge_efficiency, battery_capacity)),
    )
    dynamic_target_energy_kwh = min(
        battery_capacity * 0.95,
        max(energy_to_keep_kwh, energy_to_keep_kwh + planned_market_energy_kwh),
    )
    dynamic_charge_target_soc = min(
        95.0,
        max(safe_min_soc, dynamic_target_energy_kwh / max(battery_capacity, 0.1) * 100.0),
    )
    required_charge_kwh = max(0.0, dynamic_target_energy_kwh - current_battery_energy_kwh)
    expected_trade_revenue = feasible_sale_kwh * best_sell_price
    expected_cycle_cost = feasible_sale_kwh * cycle_cost
    expected_trade_profit = max(0.0, expected_trade_revenue - expected_cycle_cost)

    selected_windows_completed = bool(data.get("pv_price_strategy_windows_completed", False))
    if selected_windows_completed and soc + 1.0 < dynamic_charge_target_soc:
        recovery_status = "NIEDOBÓR ENERGII"
        recovery_reason = (
            f"Po zakończeniu tanich okien brakuje około {required_charge_kwh:.2f} kWh do celu "
            f"{dynamic_charge_target_soc:.0f}%. Plan ograniczy późniejszą sprzedaż zamiast naruszać rezerwę."
        )
    else:
        recovery_status = "OK"
        recovery_reason = "Plan ładowania i rezerwy jest wykonalny."

    if safe_to_sell_kwh <= 0.2:
        safe_export_limit_w = 0.0
    else:
        safe_export_limit_w = min(10000.0, max(500.0, safe_to_sell_kwh * 1000.0))

    night_soc_need = min(100.0, max(0.0, night_need_kwh / max(battery_capacity, 0.1) * 100.0))
    recommended_soc = max(night_reserve_soc, night_soc_need + 8.0, safe_min_soc)

    current_phase = _phase(now.hour)
    current_mode = str(data.get("mode", "NORMAL"))

    if current_mode == "PV_LOW_PRICE_CHARGE" and soc >= dynamic_charge_target_soc:
        if sell_price_now > 0.0:
            data["mode"] = "PV_PRICE_EXPORT"
            current_mode = "PV_PRICE_EXPORT"
            data["reason"] = (
                f"Dynamiczny cel ładowania {dynamic_charge_target_soc:.0f}% został osiągnięty — "
                f"sprzedaję dalszą nadwyżkę PV po dodatniej cenie {sell_price_now:.3f} PLN/kWh"
            )
        else:
            data["mode"] = "NEGATIVE_PRICE_EXPORT_BLOCK"
            current_mode = "NEGATIVE_PRICE_EXPORT_BLOCK"
            data["reason"] = (
                f"Dynamiczny cel ładowania {dynamic_charge_target_soc:.0f}% został osiągnięty, "
                "ale cena sprzedaży jest zerowa lub ujemna — blokuję eksport"
            )

    if (
        current_mode == "WAIT_BETTER_SELL_PRICE"
        and feasible_sale_kwh > 0.3
        and required_sale_hours > 0.25
        and now >= recommended_sell_start_dt
        and sell_price_now > cycle_cost
    ):
        data["mode"] = "SELL_BATTERY_HIGH_PRICE"
        current_mode = "SELL_BATTERY_HIGH_PRICE"
        data["reason"] = (
            f"Rozpoczynam sprzedaż wcześniej, aby zdążyć oddać {feasible_sale_kwh:.2f} kWh "
            f"w dobrym oknie; wymagany czas około {required_sale_hours:.1f} h"
        )

    charge_window = f"{cheapest.get('hour', '-')} ({cheapest_buy:.3f} PLN/kWh)"
    sell_window = f"{best_sell.get('hour', '-')} ({best_sell_price:.3f} PLN/kWh)"

    next_action = "Normalna praca"
    next_time = "teraz"
    reason = "Brak mocniejszego sygnału z cen, PV lub profilu zużycia."
    hold_reason = "Brak potrzeby blokowania energii."

    weather_strategy = (
        f"Jutro: {weather_tomorrow}. Prognoza PV {pv_tomorrow_kwh:.2f} kWh, "
        f"prognoza zużycia {day_need_kwh:.2f} kWh. "
        f"Zostawiam {energy_to_keep_kwh:.2f} kWh, bezpiecznie do sprzedaży {safe_to_sell_kwh:.2f} kWh. "
        f"Najbliższe normalne/tanie dokupienie: {reasonable_buy_window}."
    )

    pv_export_opportunity = str(data.get("economic_pv_export_opportunity", "OFF")).upper() == "ON"

    if (
        current_mode in ("SELL_BATTERY_HIGH_PRICE", "WAIT_BETTER_SELL_PRICE")
        and safe_to_sell_kwh <= 0.2
        and not pv_export_opportunity
    ):
        data["mode"] = "WEATHER_HOLD_RESERVE"
        current_mode = "WEATHER_HOLD_RESERVE"
        data["reason"] = (
            "Blokuję sprzedaż, bo prognoza PV na jutro i profil zużycia wymagają zostawienia energii w magazynie"
        )

    if current_mode == "WEATHER_HOLD_RESERVE":
        next_action = "Nie sprzedawaj — rezerwa pod pogodę"
        next_time = "teraz"
        reason = weather_strategy
        hold_reason = "Energia w baterii jest potrzebna do kolejnego dnia lub do najbliższego taniego/normalnego zakupu."

    elif current_mode == "EMERGENCY_RESERVE":
        next_action = "Ładowanie awaryjne"
        next_time = "teraz"
        reason = "SOC jest poniżej poziomu awaryjnego."
        recommended_soc = max(recommended_soc, charge_target_soc)

    elif current_mode == "PV_LOW_PRICE_CHARGE":
        next_action = "Ładowanie PV w najgorszej godzinie sprzedaży"
        next_time = "teraz"
        reason = str(data.get("pv_price_strategy_reason", "Nadwyżka PV jest kierowana do magazynu."))
        recommended_soc = _f(data.get("pv_price_strategy_target_soc"), 95.0)

    elif current_mode == "PV_PRICE_EXPORT":
        next_action = "Sprzedaż PV przed najgorszymi godzinami"
        next_time = "teraz"
        reason = str(data.get("pv_price_strategy_reason", "Sprzedaję PV i zachowuję wolne miejsce w magazynie."))
        recommended_soc = min(soc, _f(data.get("pv_price_strategy_target_soc"), 95.0))

    elif current_mode == "SELL_BATTERY_HIGH_PRICE":
        next_action = "Sprzedaż bezpiecznej nadwyżki"
        next_time = "teraz"
        reason = (
            f"Aktualna cena osiągnęła ustawiony próg sprzedaży: {sell_price_now:.3f} PLN/kWh. "
            f"Sprzedaż obejmuje bieżącą nadwyżkę PV oraz bezpieczną nadwyżkę baterii {safe_to_sell_kwh:.2f} kWh."
        )
        recommended_soc = safe_min_soc

    elif best_sell_price > sell_price_now + 0.02 and (safe_to_sell_kwh > 0.3 or pv_export_opportunity):
        next_action = "Trzymaj energię do sprzedaży"
        next_time = str(best_sell.get("hour", "-"))
        reason = (
            f"Lepsza sprzedaż planowana o {best_sell.get('hour', '-')} przy cenie {best_sell_price:.3f} PLN/kWh. "
            f"Bezpieczna nadwyżka do sprzedaży: {safe_to_sell_kwh:.2f} kWh."
        )
        hold_reason = "Bateria ma wartość rynkową, ale EMS zostawia rezerwę pod pogodę i zużycie."

    elif buy_price_now <= cheapest_buy + 0.005 and soc < charge_target_soc:
        next_action = "Ładowanie z taniej energii"
        next_time = "teraz"
        reason = f"Aktualna cena zakupu jest w najtańszym oknie 24h: {buy_price_now:.3f} PLN/kWh."
        recommended_soc = max(recommended_soc, charge_target_soc)

    elif cheapest_buy + 0.04 < buy_price_now and soc < charge_target_soc:
        next_action = "Czekaj na tańsze ładowanie"
        next_time = str(cheapest.get("hour", "-"))
        reason = f"Najtańsze okno zakupu jest o {cheapest.get('hour', '-')} przy cenie {cheapest_buy:.3f} PLN/kWh."
        hold_reason = "Nie ładuję teraz, bo w planie jest tańsza energia."

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
        f"Sprzedaż: {sell_window}. Jutro PV: {pv_tomorrow_kwh:.2f} kWh. "
        f"Bezpiecznie do sprzedaży: {safe_to_sell_kwh:.2f} kWh."
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

        "plan_weather_tomorrow": weather_tomorrow,
        "plan_pv_tomorrow_kwh": round(pv_tomorrow_kwh, 2),
        "plan_next_day_energy_balance_kwh": round(next_day_energy_balance_kwh, 2),
        "plan_energy_to_keep_kwh": round(energy_to_keep_kwh, 2),
        "plan_safe_to_sell_kwh": round(safe_to_sell_kwh, 2),
        "plan_safe_export_limit_w": round(safe_export_limit_w, 0),
        "plan_weather_strategy": weather_strategy[:255],
        "plan_reasonable_buy_window": reasonable_buy_window,
        "optimizer_status": "ACTIVE",
        "optimizer_dynamic_charge_target_soc": round(dynamic_charge_target_soc, 1),
        "optimizer_required_charge_kwh": round(required_charge_kwh, 2),
        "optimizer_future_pv_surplus_kwh": round(future_pv_surplus_kwh, 2),
        "optimizer_charge_efficiency": round(charge_efficiency * 100.0, 1),
        "optimizer_discharge_efficiency": round(discharge_efficiency * 100.0, 1),
        "optimizer_discharge_power_kw": round(discharge_power_kw, 2),
        "optimizer_sell_window_hours": round(sell_window_hours, 1),
        "optimizer_sell_window_capacity_kwh": round(sell_window_capacity_kwh, 2),
        "optimizer_feasible_sale_kwh": round(feasible_sale_kwh, 2),
        "optimizer_required_sale_hours": round(required_sale_hours, 2),
        "optimizer_recommended_sell_start": _hour_label(recommended_sell_start_dt),
        "optimizer_expected_trade_profit": round(expected_trade_profit, 2),
        "optimizer_recovery_status": recovery_status,
        "optimizer_recovery_reason": recovery_reason[:240],
        "optimizer_plan_24h": " | ".join(
            f"{item['hour']} PV {item['pv_kwh']:.1f}kWh Dom {item['load_kwh']:.1f}kWh S {item['sell']:.2f}"
            for item in hours[:8]
        )[:240],
    })

    return data
