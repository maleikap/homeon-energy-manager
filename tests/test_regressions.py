from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "homeon_energy_manager"


class SimulatorReportRegressionTests(unittest.TestCase):
    def test_deye_diagnostics_are_initialized_before_early_guards(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        function_start = source.index("async def _async_apply_inverter_control")
        first_guard = source.index("# HOMEON_HOME_BATTERY_PRIORITY_EXEC_GUARD", function_start)
        initialization = source.index('data["deye_driver_min_interval_seconds"]', function_start)

        self.assertLess(initialization, first_guard)
        for key in (
            "deye_driver_safety_status",
            "deye_driver_block_reason",
            "deye_driver_min_interval_seconds",
            "deye_driver_max_changes_per_run",
            "deye_driver_changed_count_runtime",
            "deye_driver_last_control_hash",
            "deye_command_confirmation",
            "deye_command_confirmation_reason",
        ):
            self.assertIn(f'data["{key}"]', source[function_start:first_guard])

    def test_setting_entities_are_configuration_entities(self) -> None:
        for filename in ("number.py", "switch.py"):
            source = (COMPONENT / filename).read_text(encoding="utf-8")
            self.assertIn("EntityCategory.CONFIG", source)

    def test_power_unit_normalization_remains_enabled(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('{"w": 1.0, "kw": 1000.0, "mw": 1_000_000.0}', source)

    def test_release_version_is_consistent(self) -> None:
        manifest = json.loads((COMPONENT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("1.2.34", manifest["version"])
        for filename in ("sensor.py", "number.py", "switch.py"):
            source = (COMPONENT / filename).read_text(encoding="utf-8")
            self.assertIn('"sw_version": "1.2.34"', source)

    def test_profit_mode_accounts_for_repurchase_losses_and_cycle_cost(self) -> None:
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        switches = (COMPONENT / "switch.py").read_text(encoding="utf-8")
        sensors = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        planner = (COMPONENT / "planner.py").read_text(encoding="utf-8")

        self.assertIn('("profit_mode", "Tryb zarabiania"', switches)
        self.assertIn("def _profit_mode_plan(", coordinator)
        self.assertIn("purchase_cost_per_sold_kwh", coordinator)
        self.assertIn("charge_efficiency * discharge_efficiency", coordinator)
        self.assertIn("expected_revenue - expected_purchase_cost - expected_cycle_cost", coordinator)
        self.assertIn('soc >= 94.0', coordinator)
        self.assertIn('"profit_mode_expected_net_profit"', sensors)
        self.assertIn("and not profit_mode_enabled", planner)

    def test_daily_financial_stats_are_calculated_live(self) -> None:
        learning = (COMPONENT / "learning.py").read_text(encoding="utf-8")
        sensors = (COMPONENT / "sensor.py").read_text(encoding="utf-8")

        self.assertIn('learn["financial_daily_key"] = day_key', learning)
        self.assertIn("interval_import_kwh * buy_price", learning)
        self.assertIn("interval_export_kwh * sell_price", learning)
        self.assertIn('"learn_daily_purchase_cost_pln"', learning)
        self.assertIn('"learn_daily_sale_value_pln"', learning)
        self.assertIn('"learn_daily_financial_balance_pln"', learning)
        self.assertIn('"learn_daily_grid_import_kwh"', sensors)
        self.assertIn('"learn_daily_grid_export_kwh"', sensors)

    def test_evening_sale_waits_only_for_next_morning(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        stats_start = source.index("def _price_stats_from_entity(")
        stats_end = source.index("def _pv_low_price_window_plan(", stats_start)
        stats = source[stats_start:stats_end]

        self.assertIn("morning_deadline = current_hour_start.replace(hour=10)", stats)
        self.assertIn("morning_deadline += timedelta(days=1)", stats)
        self.assertIn('"best_sell_price_before_morning"', stats)
        self.assertIn('"sell_now_best_before_morning"', stats)

        self.assertIn('sell_stats.get("best_sell_price_before_morning")', source)
        self.assertIn('sell_stats.get("best_sell_minutes_before_morning")', source)
        self.assertIn('not sell_stats.get("sell_now_best_before_morning", False)', source)

    def test_pstryk_daily_average_is_not_parsed_as_hourly_price(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        extractor_start = source.index("def _extract_price_points(")
        extractor_end = source.index("def _price_stats_from_entity(", extractor_start)
        extractor = source[extractor_start:extractor_end]

        self.assertIn('"average"', extractor)
        self.assertIn('"srednia"', extractor)
        self.assertIn('"średnia"', extractor)
        self.assertIn("continue", extractor)

    def test_grid_charge_uses_only_cheapest_required_hours(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        helper_start = source.index("def _cheap_grid_charge_plan(")
        helper_end = source.index("def _negative_price_plan(", helper_start)
        helper = source[helper_start:helper_end]
        self.assertIn("math.ceil(missing_kwh / estimated_charge_kw)", helper)
        self.assertNotIn("min(3, max(1", helper)
        self.assertIn('self._runtime_float("inverter_rated_power_kw", 20.0)', helper)
        self.assertIn('self._runtime_float("battery_max_charge_c_rate", 0.5)', helper)
        self.assertIn("min(inverter_power_kw, battery_charge_limit_kw)", helper)
        self.assertIn("schedule_available", helper)
        self.assertIn('"charge_now": charge_now', helper)

        self.assertIn('cheap_grid_charge_plan.get("charge_now", False)', source)
        self.assertIn('not cheap_grid_charge_plan.get("schedule_available", False)', source)
        self.assertIn('"cheap_charge_windows"', source)

        cheap_mode = source.index('mode = "CHEAP_CHARGE"')
        home_protection = source.index('elif home_battery_protection_active:', cheap_mode)
        self.assertLess(cheap_mode, home_protection)

    def test_required_charging_bypasses_home_priority_guard(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        executor_start = source.index("async def _async_apply_inverter_control")
        executor_end = source.index("async def _async_update_data", executor_start)
        executor = source[executor_start:executor_end]

        self.assertIn('charging_override_modes = {"CHEAP_CHARGE", "NEGATIVE_IMPORT", "EMERGENCY_RESERVE"}', executor)
        self.assertIn("requested_mode not in charging_override_modes", executor)

    def test_control_target_uses_calibrated_pv_forecast(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('learn.get("pv_forecast_factor")', source)
        self.assertIn("pv_tomorrow_for_control = max(0.0, pv_tomorrow * pv_forecast_factor)", source)
        self.assertIn("target_expected_24h_consumption_kwh - pv_tomorrow_for_control", source)
        self.assertIn('"pv_forecast_tomorrow_control"', source)

    def test_night_reserve_is_consumed_down_to_minimum_soc(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        self.assertIn('self_use_reserve_soc = min(', source)
        self.assertIn('night_self_use_active = bool(local_hour >= 20 or local_hour < 9)', source)
        self.assertIn('mode = "MORNING_RESERVE_HOLD"', source)
        self.assertIn('soc > self_use_reserve_soc + 1.0', source)

        decision_start = source.index('elif soc <= min_soc + 1.0')
        decision_end = source.index('elif buy_price >= economic_expensive_buy_price', decision_start)
        decision = source[decision_start:decision_end]
        self.assertIn('mode = "MORNING_RESERVE_HOLD"', decision)
        self.assertIn('dolna granica magazynu', decision)

        branch_start = source.index('elif mode == "MORNING_RESERVE_HOLD":')
        branch_end = source.index('\n        else:', branch_start)
        branch = source[branch_start:branch_end]
        self.assertIn("inverter_block_discharge_current_a", branch)
        self.assertIn("sw(inverter_grid_charging, False)", branch)

        normal_start = source.index('else:\n            executor_mode = "NORMAL_SAFE"', branch_end)
        normal_end = source.index('\n        if full_soc_charge_lock:', normal_start)
        normal = source[normal_start:normal_end]
        self.assertIn('night_self_use_active and current_soc > minimum_soc + 1.0', normal)
        self.assertIn('discharge_current = inverter_discharge_current_a', normal)
        self.assertIn('num(inverter_max_discharge_current, discharge_current)', normal)

        sensors = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        self.assertIn('"self_use_reserve_soc"', sensors)

    def test_grid_side_ct_load_is_included_in_night_reserve(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        self.assertIn("ct_balanced_load_power = max(", source)
        self.assertIn("load_power = max(inverter_load_power_raw, ct_balanced_load_power)", source)
        self.assertIn('"inverter_load_power_raw"', source)
        self.assertIn('"ct_balanced_load_power"', source)
        self.assertIn('hourly_profile.get(f"{hour:02d}")', source)
        self.assertIn("learned_night_profile_kwh * night_safety_margin", source)
        self.assertIn("profile_ct_balance_w = max(", source)
        self.assertIn('bucket.get("avg_grid_import_w")', source)
        self.assertIn('bucket.get("avg_battery_discharge_w")', source)

    def test_load_installation_uses_load_reading_and_matching_deye_mode(self) -> None:
        constants = (COMPONENT / "const.py").read_text(encoding="utf-8")
        config_flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        self.assertIn('CONF_INSTALLATION_TYPE = "installation_type"', constants)
        self.assertIn('DEFAULT_INVERTER_WORK_MODE_LOAD_OPTION = "Zero Export To Load"', constants)
        self.assertIn("INSTALLATION_TYPE_SELECTOR", config_flow)
        self.assertIn("installation_type == INSTALLATION_TYPE_LOAD", coordinator)
        self.assertIn("load_power = max(0.0, inverter_load_power_raw)", coordinator)
        self.assertIn("load_power_minimum = -100.0", coordinator)
        self.assertIn("DEFAULT_INVERTER_WORK_MODE_LOAD_OPTION", coordinator)

    def test_pstryk_aio_is_the_automatic_price_source(self) -> None:
        constants = (COMPONENT / "const.py").read_text(encoding="utf-8")
        config_flow = (COMPONENT / "config_flow.py").read_text(encoding="utf-8")
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        self.assertIn("sensor.pstryk_aio_obecna_cena_zakupu_pradu", constants)
        self.assertIn("sensor.pstryk_aio_cena_zakupu_pradu_jutro", constants)
        self.assertIn("sensor.pstryk_aio_obecna_cena_sprzedazy_pradu", constants)
        self.assertIn("sensor.pstryk_aio_cena_sprzedazy_pradu_jutro", constants)
        self.assertIn("sensor.pstryk_current_buy_price", constants)
        self.assertIn("sensor.pstryk_current_sell_price", constants)
        self.assertIn("DEFAULT_PSTRYK_BUY_PRICE_SENSOR", config_flow)
        self.assertIn("DEFAULT_PSTRYK_SELL_PRICE_SENSOR", config_flow)
        self.assertIn("buy_price_entities = self._price_entity_ids(", coordinator)
        self.assertIn("sell_price_entities = self._price_entity_ids(", coordinator)
        self.assertIn("for price_entity_id in self._entity_id_list(entity_id):", coordinator)
        self.assertIn("buy_price_entities,\n            buy_price,\n            sell_price,", coordinator)
        self.assertIn("elif usable(modern_current):", coordinator)

    def test_pstryk_tomorrow_average_is_never_the_current_price(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        helper_start = source.index("def _price_entity_ids(")
        helper_end = source.index("@staticmethod", helper_start)
        helper = source[helper_start:helper_end]

        self.assertIn("if configured_text == pstryk_tomorrow:", helper)
        self.assertIn("configured_text = pstryk_current", helper)
        self.assertIn("if explicit_text == pstryk_tomorrow:", helper)
        self.assertIn("explicit_text = pstryk_current", helper)
        self.assertIn("entities.append(pstryk_tomorrow)", helper)

    def test_planner_uses_today_and_tomorrow_price_schedules(self) -> None:
        source = (COMPONENT / "planner.py").read_text(encoding="utf-8")

        self.assertIn("buy_price_entities = coordinator._price_entity_ids(", source)
        self.assertIn("sell_price_entities = coordinator._price_entity_ids(", source)
        self.assertIn("DEFAULT_PSTRYK_BUY_PRICE_TOMORROW_SENSOR", source)
        self.assertIn("DEFAULT_PSTRYK_SELL_PRICE_TOMORROW_SENSOR", source)
        self.assertIn("for price_entity_id in coordinator._entity_id_list(entity_id):", source)

    def test_completed_charge_windows_do_not_export_below_soc_target(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        branch_start = source.index('pv_low_price_plan.get("windows_completed", False)')
        branch_end = source.index('elif soc <= min_soc + 1.0', branch_start)
        branch = source[branch_start:branch_end]

        self.assertIn("soc >= charge_target_soc - 1.0", branch)
        self.assertIn('mode = "PV_CHARGE"', branch)
        self.assertIn("kontynuuję ładowanie z PV", branch)

    def test_wait_for_better_price_charges_pv_instead_of_exporting(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        branch_start = source.index('elif mode == "WAIT_BETTER_SELL_PRICE":')
        branch_end = source.index('elif mode == "PV_CHARGE":', branch_start)
        branch = source[branch_start:branch_end]

        self.assertIn("inverter_work_mode_pv_charge_option", branch)
        self.assertIn("sw(inverter_export_surplus, False)", branch)
        self.assertIn("num(inverter_max_charge_current, inverter_charge_current_a)", branch)
        self.assertIn("num(inverter_max_discharge_current, inverter_discharge_current_a)", branch)
        self.assertNotIn("inverter_work_mode_sell_option", branch)

    def test_wait_for_better_price_also_applies_below_good_sell_threshold(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        condition_start = source.index("wait_for_better_sell = bool(")
        condition_end = source.index("\n        )", condition_start)
        condition = source[condition_start:condition_end]

        self.assertIn("best_sell_price >= sell_price + better_price_margin", condition)
        self.assertIn("available_to_sell_kwh > 0.3", condition)
        self.assertNotIn("sell_price_trigger", condition)

    def test_full_battery_exports_pv_without_battery_discharge(self) -> None:
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        planner = (COMPONENT / "planner.py").read_text(encoding="utf-8")
        branch_start = coordinator.index("elif (\n            full_soc_charge_lock")
        branch_end = coordinator.index("elif weather_lock:", branch_start)
        branch = coordinator[branch_start:branch_end]

        self.assertIn('executor_mode = "FULL_BATTERY_PV_EXPORT"', branch)
        self.assertIn("inverter_work_mode_sell_option", branch)
        self.assertIn("sw(inverter_export_surplus, True)", branch)
        self.assertIn("num(inverter_max_charge_current, 0.0)", branch)
        self.assertIn("num(inverter_max_discharge_current, 0.0)", branch)
        self.assertIn('"SELL_BATTERY_HIGH_PRICE"', branch)
        self.assertIn('"PREPARE_NEGATIVE_PRICE_WINDOW"', branch)
        self.assertIn("pv_export_surplus_w > 50.0", branch)
        self.assertIn('current_mode == "WAIT_BETTER_SELL_PRICE"', planner)
        self.assertIn('_f(data.get("pv_power"), 0.0) > _f(data.get("load_power"), 0.0) + 50.0', planner)
        self.assertIn("pv_reality_lock and min_soc < soc < 90.0", coordinator)

    def test_full_soc_charge_cutoff_has_hysteresis_and_overrides_every_mode(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        self.assertIn("if current_soc >= 95.0", source)
        self.assertIn("elif current_soc <= 90.0", source)
        self.assertIn('data["inverter_full_soc_charge_lock"]', source)
        self.assertIn("if full_soc_charge_lock:", source)
        self.assertIn("num(inverter_max_charge_current, 0.0)", source)
        self.assertIn("sw(inverter_grid_charging, False)", source)


    def test_wait_for_better_price_has_no_fifteen_minute_gap(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        condition_start = source.index("wait_for_better_sell = bool(")
        condition_end = source.index("\n        )", condition_start)
        condition = source[condition_start:condition_end]

        self.assertIn("0.0 < best_sell_minutes", condition)
        self.assertNotIn("15.0 < best_sell_minutes", condition)


    def test_wait_mode_allows_battery_to_supply_home(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        branch_start = source.index('elif mode == "WAIT_BETTER_SELL_PRICE":')
        branch_end = source.index('elif mode == "PV_CHARGE":', branch_start)
        branch = source[branch_start:branch_end]

        self.assertIn("inverter_work_mode_pv_charge_option", branch)
        self.assertIn("sw(inverter_export_surplus, False)", branch)
        self.assertIn("num(inverter_max_discharge_current, inverter_discharge_current_a)", branch)
        self.assertNotIn("num(inverter_max_discharge_current, 0.0)", branch)


if __name__ == "__main__":
    unittest.main()
