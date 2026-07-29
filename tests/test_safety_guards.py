from __future__ import annotations

import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "homeon_energy_manager"


class TestHomeOnManagerBeta(unittest.TestCase):
    def test_all_python_files_compile(self) -> None:
        for path in COMPONENT.glob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_version_is_consistent(self) -> None:
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        const = (COMPONENT / "const.py").read_text(encoding="utf-8")
        self.assertEqual(manifest["version"], "0.2.44-beta.9")
        self.assertIn('VERSION = "0.2.44-beta.9"', const)

    def test_pv_installed_power_is_available_and_persistent(self) -> None:
        init_source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        number_source = (COMPONENT / "number.py").read_text(encoding="utf-8")
        coordinator_source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('"pv_installed_kwp": 0.0', init_source)
        self.assertIn('"pv_installed_kwp"', number_source)
        self.assertIn('"Moc paneli PV – suma kWp"', number_source)
        self.assertIn('options[self._key] = final_value', number_source)
        self.assertIn('self._runtime_float("pv_installed_kwp", 0.0)', coordinator_source)

    def test_discharge_target_protects_sale_not_home_consumption(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertNotIn('"DISCHARGE_TARGET_HOLD"', source)
        self.assertIn(
            "buy_price >= economic_expensive_buy_price and soc > min_soc",
            source,
        )
        self.assertIn("soc > discharge_target_soc + 8", source)
        self.assertIn(
            "available_to_sell_kwh = max(0.0, battery_capacity_kwh * (soc - discharge_target_soc) / 100.0)",
            source,
        )
        self.assertIn(
            "cel rozładowania ogranicza sprzedaż do sieci, nie zużycie domu",
            source,
        )

    def test_zero_pv_at_night_does_not_trigger_stale_safe_mode(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('self.hass.states.get("sun.sun")', source)
        self.assertIn('str(sun_state.state) == "below_horizon"', source)
        self.assertIn('getattr(state, "last_reported", None) or state.last_updated', source)
        self.assertIn("stale_zero_pv_is_expected", source)
        self.assertIn("age_seconds > max_age_seconds and not stale_zero_pv_is_expected", source)
        self.assertIn(
            '_check_required_number("Moc PV", CONF_PV_POWER_SENSOR, -1000.0, 200000.0, 600.0)',
            source,
        )

    def test_battery_trade_preference_survives_restart(self) -> None:
        init_source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        switch_source = (COMPONENT / "switch.py").read_text(encoding="utf-8")
        self.assertIn('"battery_trade": False', init_source)
        self.assertIn('options[self._key] = value', switch_source)
        self.assertIn('entry.options.get(key, default)', init_source)

    def test_morning_pv_headroom_sale_is_bounded_and_guarded(self) -> None:
        planner = (COMPONENT / "planner.py").read_text(encoding="utf-8")
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn("morning_window = 4.0 <= local_hour < 10.0", planner)
        self.assertIn('"economic_min_sell_price_prepare"', planner)
        self.assertIn("morning_headroom_sell_kwh = min(", planner)
        self.assertIn("morning_headroom_to_free_kwh,", planner)
        self.assertIn("morning_discharge_available_kwh,", planner)
        self.assertIn("morning_floor_soc", planner)
        self.assertIn('str(data.get("safe_mode", "OFF")).upper() != "ON"', planner)
        self.assertIn('current_mode = "MORNING_PV_HEADROOM"', planner)
        self.assertIn('elif mode == "MORNING_PV_HEADROOM"', coordinator)
        executor = coordinator.split('elif mode == "MORNING_PV_HEADROOM"', 1)[1].split(
            'elif mode == "SELL_BATTERY_HIGH_PRICE"', 1
        )[0]
        self.assertIn("sw(inverter_grid_charging, False)", executor)
        self.assertIn("sw(inverter_export_surplus, True)", executor)
        self.assertIn("safe_export_limit_w", executor)

    def test_stopping_trade_actively_turns_off_deye_export(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertNotIn("HOMEON_HOME_BATTERY_PRIORITY_EXEC_GUARD", source)
        self.assertIn('elif mode == "HOME_BATTERY_PRIORITY":', source)
        block = source.split('elif mode == "HOME_BATTERY_PRIORITY":', 1)[1].split(
            'elif mode == "PREPARE_NEGATIVE_PRICE_WINDOW":', 1
        )[0]
        self.assertIn("sw(inverter_export_surplus, False)", block)
        self.assertIn("num(inverter_export_surplus_power, 0)", block)
        normal = source.split('action = "Normalna praca — bez ładowania z sieci i bez wymuszonej sprzedaży"', 1)[1].split(
            'data["inverter_control_executor_mode"]', 1
        )[0]
        self.assertIn("sw(inverter_export_surplus, False)", normal)
        self.assertIn("num(inverter_export_surplus_power, 0)", normal)

    def test_best_price_sale_uses_full_configured_export_power(self) -> None:
        planner = (COMPONENT / "planner.py").read_text(encoding="utf-8")
        full_power_block = planner.split(
            "if safe_to_sell_kwh <= 0.2:", 1
        )[1].split("night_soc_need =", 1)[0]
        self.assertIn(
            'coordinator._runtime_float("inverter_export_target_w", 10000.0)',
            full_power_block,
        )
        self.assertNotIn("safe_to_sell_kwh * 1000.0", full_power_block)

    def test_pre_pv_headroom_is_aggressive_and_deadline_aware(self) -> None:
        planner = (COMPONENT / "planner.py").read_text(encoding="utf-8")
        self.assertIn("morning_window = 4.0 <= local_hour < 10.0", planner)
        self.assertIn("pv_power_now < 1000.0", planner)
        self.assertIn("morning_floor_soc = min(95.0, max(min_soc + 5.0, 10.0))", planner)
        self.assertIn("morning_discharge_available_kwh", planner)
        self.assertIn("export_hours_needed", planner)
        self.assertIn("hours_to_pv_start", planner)
        self.assertIn("must_start_for_headroom", planner)
        self.assertIn("(attractive_price_now or must_start_for_headroom)", planner)
        morning_override = planner.split(
            'current_mode = "MORNING_PV_HEADROOM"', 1
        )[1].split("charge_window =", 1)[0]
        self.assertIn("safe_export_limit_w = configured_export_limit_w", morning_override)
        self.assertNotIn("morning_headroom_sell_kwh * 1000.0", morning_override)

    def test_runtime_command_interval_is_used(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn(
            "now_ts - float(last_ts or 0.0) < deye_min_command_interval_seconds",
            source,
        )
        self.assertNotIn(
            "now_ts - float(last_ts or 0.0) < 120",
            source,
        )

    def test_failed_commands_are_not_marked_successful(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn("all_commands_ok = bool(command_results) and all(command_results)", source)
        self.assertIn("CZĘŚCIOWY BŁĄD", source)
        success_block = source.split("if all_commands_ok:", 1)[1].split("elif command_results:", 1)[0]
        self.assertIn("self._homeon_last_control_hash = control_hash", success_block)
        self.assertIn("self._homeon_last_control_ts = now_ts", success_block)

    def test_critical_inputs_have_freshness_limits(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn("max_age_seconds", source)
        self.assertIn("dane nieaktualne", source)

    def test_forbidden_platforms_are_absent(self) -> None:
        init_source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        config_flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        self.assertNotIn("Platform.SELECT", init_source)
        self.assertNotIn("OptionsFlow", config_flow)
        self.assertFalse((COMPONENT / "select.py").exists())


if __name__ == "__main__":
    unittest.main()
