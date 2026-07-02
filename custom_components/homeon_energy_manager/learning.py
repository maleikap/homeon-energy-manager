from __future__ import annotations

from typing import Any

from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

STORE_VERSION = 1
SAVE_INTERVAL_SECONDS = 300


def _f(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, "", "unknown", "unavailable"):
            return default
        return float(str(value).replace(",", "."))
    except Exception:
        return default


def _round(value: Any, digits: int = 2) -> float:
    try:
        return round(float(value), digits)
    except Exception:
        return 0.0


def _ewma_dict(target: dict[str, Any], key: str, value: float, alpha: float = 0.05) -> None:
    old = target.get(key)

    if old is None:
        target[key] = float(value)
        return

    try:
        target[key] = float(old) * (1.0 - alpha) + float(value) * alpha
    except Exception:
        target[key] = float(value)


def _ewma(learn: dict[str, Any], key: str, value: float, alpha: float = 0.03) -> None:
    _ewma_dict(learn, key, value, alpha)


async def _ensure_learning_loaded(coordinator) -> dict[str, Any]:
    if not hasattr(coordinator, "_homeon_learning_store"):
        coordinator._homeon_learning_store = Store(
            coordinator.hass,
            STORE_VERSION,
            f"{DOMAIN}_learning_{coordinator.entry.entry_id}",
        )
        coordinator._homeon_learning_loaded = False
        coordinator._homeon_learning = {}

    if not coordinator._homeon_learning_loaded:
        loaded = await coordinator._homeon_learning_store.async_load()
        coordinator._homeon_learning = loaded if isinstance(loaded, dict) else {}
        coordinator._homeon_learning_loaded = True

    return coordinator._homeon_learning


async def update_learning(coordinator, data: dict[str, Any]) -> dict[str, Any]:
    learn = await _ensure_learning_loaded(coordinator)

    now = dt_util.now()
    now_iso = now.isoformat()

    last_ts_raw = learn.get("last_ts")
    dt_hours = 30.0 / 3600.0

    if last_ts_raw:
        try:
            last_dt = dt_util.parse_datetime(str(last_ts_raw))
            if last_dt is not None:
                seconds = max(0.0, min(900.0, (now - last_dt).total_seconds()))
                if seconds > 0:
                    dt_hours = seconds / 3600.0
        except Exception:
            pass

    learn["last_ts"] = now_iso
    learn["samples"] = int(learn.get("samples", 0)) + 1
    learn["runtime_hours"] = _f(learn.get("runtime_hours"), 0.0) + dt_hours

    load_w = max(0.0, _f(data.get("load_power"), 0.0))
    pv_w = max(0.0, _f(data.get("pv_power"), 0.0))
    grid_import_w = max(0.0, _f(data.get("grid_import_w"), 0.0))
    grid_export_w = max(0.0, _f(data.get("grid_export_w"), 0.0))
    battery_charge_w = max(0.0, _f(data.get("battery_charge_w"), 0.0))
    battery_discharge_w = max(0.0, _f(data.get("battery_discharge_w"), 0.0))
    deye_self_w = max(0.0, _f(data.get("deye_self_power"), 0.0))

    buy_price = _f(data.get("buy_price"), 0.0)
    sell_price = _f(data.get("sell_price"), 0.0)

    _ewma(learn, "avg_load_w", load_w)
    _ewma(learn, "avg_pv_w", pv_w)
    _ewma(learn, "avg_grid_import_w", grid_import_w)
    _ewma(learn, "avg_grid_export_w", grid_export_w)
    _ewma(learn, "avg_battery_charge_w", battery_charge_w)
    _ewma(learn, "avg_battery_discharge_w", battery_discharge_w)
    _ewma(learn, "avg_deye_self_power_w", deye_self_w)

    hour = now.hour
    hour_key = f"{hour:02d}"

    if 6 <= hour < 22:
        _ewma(learn, "avg_day_load_w", load_w)
    else:
        _ewma(learn, "avg_night_load_w", load_w)

    hourly = learn.get("hourly_profile")
    if not isinstance(hourly, dict):
        hourly = {}

    bucket = hourly.get(hour_key)
    if not isinstance(bucket, dict):
        bucket = {"samples": 0}

    bucket["samples"] = int(bucket.get("samples", 0)) + 1
    _ewma_dict(bucket, "avg_load_w", load_w, 0.08)
    _ewma_dict(bucket, "avg_pv_w", pv_w, 0.08)
    _ewma_dict(bucket, "avg_grid_import_w", grid_import_w, 0.08)
    _ewma_dict(bucket, "avg_grid_export_w", grid_export_w, 0.08)
    _ewma_dict(bucket, "avg_battery_charge_w", battery_charge_w, 0.08)
    _ewma_dict(bucket, "avg_battery_discharge_w", battery_discharge_w, 0.08)

    hourly[hour_key] = bucket
    learn["hourly_profile"] = hourly

    if buy_price != 0:
        _ewma(learn, "avg_buy_price", buy_price)

    if sell_price != 0:
        _ewma(learn, "avg_sell_price", sell_price)
        learn["best_sell_price_seen"] = max(
            _f(learn.get("best_sell_price_seen"), sell_price),
            sell_price,
        )

    learn["energy_load_kwh"] = _f(learn.get("energy_load_kwh"), 0.0) + load_w * dt_hours / 1000.0
    learn["energy_pv_kwh"] = _f(learn.get("energy_pv_kwh"), 0.0) + pv_w * dt_hours / 1000.0
    learn["energy_grid_import_kwh"] = _f(learn.get("energy_grid_import_kwh"), 0.0) + grid_import_w * dt_hours / 1000.0
    learn["energy_grid_export_kwh"] = _f(learn.get("energy_grid_export_kwh"), 0.0) + grid_export_w * dt_hours / 1000.0
    learn["energy_battery_charge_kwh"] = _f(learn.get("energy_battery_charge_kwh"), 0.0) + battery_charge_w * dt_hours / 1000.0
    learn["energy_battery_discharge_kwh"] = _f(learn.get("energy_battery_discharge_kwh"), 0.0) + battery_discharge_w * dt_hours / 1000.0
    learn["energy_deye_self_kwh"] = _f(learn.get("energy_deye_self_kwh"), 0.0) + deye_self_w * dt_hours / 1000.0

    mode = str(data.get("mode", "UNKNOWN"))
    mode_counts = learn.get("mode_counts")
    if not isinstance(mode_counts, dict):
        mode_counts = {}
    mode_counts[mode] = int(mode_counts.get(mode, 0)) + 1
    learn["mode_counts"] = mode_counts

    most_common_mode = "-"
    if mode_counts:
        most_common_mode = sorted(mode_counts.items(), key=lambda x: x[1], reverse=True)[0][0]

    runtime_hours = _f(learn.get("runtime_hours"), 0.0)
    confidence = min(100.0, runtime_hours / 24.0 * 100.0)

    avg_load_w = _f(learn.get("avg_load_w"), 0.0)
    avg_day_load_w = _f(learn.get("avg_day_load_w"), avg_load_w)
    avg_night_load_w = _f(learn.get("avg_night_load_w"), avg_load_w)

    peak_hour = "-"
    low_hour = "-"
    peak_load = 0.0
    low_load = 0.0

    hourly_loads = []

    for h in range(24):
        hk = f"{h:02d}"
        b = hourly.get(hk)
        if not isinstance(b, dict):
            continue

        samples = int(b.get("samples", 0))
        load = _f(b.get("avg_load_w"), 0.0)

        if samples > 0:
            hourly_loads.append((hk, load))

    if hourly_loads:
        peak_hour, peak_load = sorted(hourly_loads, key=lambda x: x[1], reverse=True)[0]
        low_hour, low_load = sorted(hourly_loads, key=lambda x: x[1])[0]

    data.update({
        "learn_samples": int(learn.get("samples", 0)),
        "learn_runtime_hours": _round(runtime_hours, 2),
        "learn_confidence": _round(confidence, 0),
        "learn_last_update": now.strftime("%Y-%m-%d %H:%M:%S"),

        "learn_avg_load_w": _round(avg_load_w, 0),
        "learn_avg_day_load_w": _round(avg_day_load_w, 0),
        "learn_avg_night_load_w": _round(avg_night_load_w, 0),
        "learn_estimated_daily_consumption_kwh": _round(avg_load_w * 24.0 / 1000.0, 2),
        "learn_estimated_night_consumption_kwh": _round(avg_night_load_w * 8.0 / 1000.0, 2),

        "learn_peak_load_hour": f"{peak_hour}:00" if peak_hour != "-" else "-",
        "learn_peak_load_w": _round(peak_load, 0),
        "learn_low_load_hour": f"{low_hour}:00" if low_hour != "-" else "-",
        "learn_low_load_w": _round(low_load, 0),

        "learn_avg_pv_w": _round(learn.get("avg_pv_w"), 0),
        "learn_avg_grid_import_w": _round(learn.get("avg_grid_import_w"), 0),
        "learn_avg_grid_export_w": _round(learn.get("avg_grid_export_w"), 0),
        "learn_avg_battery_charge_w": _round(learn.get("avg_battery_charge_w"), 0),
        "learn_avg_battery_discharge_w": _round(learn.get("avg_battery_discharge_w"), 0),
        "learn_avg_deye_self_power_w": _round(learn.get("avg_deye_self_power_w"), 0),

        "learn_energy_load_kwh": _round(learn.get("energy_load_kwh"), 2),
        "learn_energy_pv_kwh": _round(learn.get("energy_pv_kwh"), 2),
        "learn_energy_grid_import_kwh": _round(learn.get("energy_grid_import_kwh"), 2),
        "learn_energy_grid_export_kwh": _round(learn.get("energy_grid_export_kwh"), 2),
        "learn_energy_battery_charge_kwh": _round(learn.get("energy_battery_charge_kwh"), 2),
        "learn_energy_battery_discharge_kwh": _round(learn.get("energy_battery_discharge_kwh"), 2),
        "learn_energy_deye_self_kwh": _round(learn.get("energy_deye_self_kwh"), 2),

        "learn_avg_buy_price": _round(learn.get("avg_buy_price"), 3),
        "learn_avg_sell_price": _round(learn.get("avg_sell_price"), 3),
        "learn_best_sell_price_seen": _round(learn.get("best_sell_price_seen"), 3),
        "learn_most_common_mode": most_common_mode,
    })

    last_saved_raw = learn.get("last_saved_ts")
    should_save = True

    if last_saved_raw:
        try:
            last_saved = dt_util.parse_datetime(str(last_saved_raw))
            if last_saved is not None and (now - last_saved).total_seconds() < SAVE_INTERVAL_SECONDS:
                should_save = False
        except Exception:
            should_save = True

    if should_save:
        learn["last_saved_ts"] = now_iso
        await coordinator._homeon_learning_store.async_save(learn)

    return data
