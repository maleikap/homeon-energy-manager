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
        first_guard = source.index("if not enabled:", function_start)
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
        self.assertEqual("1.2.57", manifest["version"])
        for filename in ("sensor.py", "number.py", "switch.py"):
            source = (COMPONENT / filename).read_text(encoding="utf-8")
            self.assertIn('"sw_version": "1.2.56"', source)

    def test_profit_mode_accounts_for_repurchase_losses_and_cycle_cost(self) -> None:
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        switches = (COMPONENT / "switch.py").read_text(encoding="utf-8")
        sensors = (COMPONENT / "sensor.py").read_text(encoding="utf-8")
        planner = (COMPONENT / "planner.py").read_text(encoding="utf-8")

        self.assertIn('("profit_mode", "Tryb zarabiania"', switches)
        self.assertIn("def _profit_mode_plan(", coordinator)
        self.assertIn("replacement_input_kwh", coordinator)
        self.assertIn("charge_efficiency * discharge_efficiency", coordinator)
        self.assertIn("expected_revenue - expected_energy_cost - expected_cycle_cost", coordinator)
        self.assertIn("pv_surplus_for_refill_kwh", coordinator)
        self.assertIn("forecast_refill_allowed", coordinator)
        self.assertIn("current_good_pv_sale", coordinator)
        self.assertIn("effective_reserve_soc", coordinator)
        self.assertIn("grid_repurchase_kwh = max(0.0, replacement_input_kwh - pv_refill_kwh)", coordinator)
        self.assertIn("expected_purchase_cost = grid_repurchase_kwh * cheapest_buy", coordinator)
        self.assertIn("stored_energy_above_reserve_kwh", coordinator)
        self.assertIn("current_good_pv_sale", coordinator)
        self.assertIn("current_sell_price >= best_sell_price - 0.01", coordinator)
        self.assertIn('item["dt"] > now + timedelta(minutes=20)', coordinator)
        self.assertIn("prepare_charge = False", coordinator)
        self.assertIn('"profit_mode_expected_net_profit"', sensors)
        self.assertNotIn("sell_price_now >= best_sell_price * 0.95", planner)
        self.assertIn('data.get("profit_mode_current_good_pv_sale", "OFF")', planner)
        self.assertIn('data.get("profit_mode_sale_energy_kwh")', planner)

    def test_daily_financial_stats_are_calculated_live(self) -> None:
        learning = (COMPONENT / "learning.py").read_text(encoding="utf-8")
        sensors = (COMPONENT / "sensor.py").read_text(encoding="utf-8")

        self.assertIn('learn["financial_daily_key"] = day_key', learning)
        self.assertIn("interval_import_kwh * buy_price", learning)
        self.assertIn("interval_export_kwh * sell_price", learning)
        self.assertIn("if not financial_day_key or financial_day_key != day_key:", learning)
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
        self.assertIn("missing_kwh / estimated_charge_kw", helper)
        self.assertIn("math.ceil(required_charge_hours)", helper)
        self.assertNotIn("min(3, max(1", helper)
        self.assertIn('self._runtime_float("inverter_rated_power_kw", 20.0)', helper)
        self.assertIn('self._runtime_float("battery_max_charge_c_rate", 0.5)', helper)
        self.assertIn("min(inverter_power_kw, battery_charge_limit_kw)", helper)
        self.assertIn("schedule_available", helper)
        self.assertIn('"charge_now": charge_now', helper)
        self.assertIn("hours_before_reserve", helper)
        self.assertIn("item[\"dt\"] < reserve_deadline", helper)
        self.assertIn("deadline_missed", helper)
        self.assertIn("deadline_imminent", helper)
        self.assertIn("predictive_floor_soc", helper)
        self.assertIn("predicted_depletion_deadline", helper)
        self.assertIn("predictive_precharge", helper)
        self.assertIn("survival_hours", helper)
        self.assertIn("prediction_safety_margin", helper)
        self.assertIn("hourly_profile", helper)
        self.assertIn("predicted_consumption_until_reserve_kwh", helper)
        self.assertIn("target_energy_kwh", helper)
        self.assertIn("current_energy_kwh", helper)
        self.assertIn("def _slot_hours", helper)
        self.assertIn("((current_hour + timedelta(hours=1)) - now)", helper)
        self.assertIn("def _slot_capacity_kwh", helper)
        self.assertIn("remaining_kwh -= slot_capacity_kwh", helper)
        self.assertIn("direct_reserve_missing_kwh", helper)
        self.assertIn("recover_missed_reserve_now", helper)
        self.assertIn("schedule_covers_deadline", helper)
        self.assertIn("grid_charge_target_soc", helper)
        self.assertIn("bridge_charge_only", helper)
        self.assertIn("consumption_until_next_slot_kwh", helper)
        self.assertIn("current_slot_charge_kwh", helper)

        self.assertIn('cheap_grid_charge_plan.get("charge_now", False)', source)
        self.assertIn('not cheap_grid_charge_plan.get("schedule_available", False)', source)
        self.assertIn('"cheap_charge_windows"', source)
        self.assertIn("reserve_ready_by_hour", source)
        self.assertIn("early_load_threshold_w", source)
        self.assertIn("grid_charge_blocked_by_pv", source)
        self.assertIn("live_pv_surplus_for_charge_w >= 500.0", source)
        self.assertIn("forecast_pv_surplus_for_charge_kwh", source)
        self.assertIn("not grid_charge_blocked_by_pv", source)
        self.assertIn('str(last_mode) == "CHEAP_CHARGE"', source)
        self.assertIn('not cheap_grid_charge_plan.get("charge_now", False)', source)

        pv_sale_mode = source.index(
            'profit_mode_plan.get("current_good_pv_sale", False)'
        )
        cheap_mode = source.index('mode = "CHEAP_CHARGE"', pv_sale_mode)
        self.assertLess(pv_sale_mode, cheap_mode)

        home_protection = source.index('elif home_battery_protection_active:', cheap_mode)
        self.assertLess(cheap_mode, home_protection)

    def test_required_charging_and_home_priority_are_both_executable(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        executor_start = source.index("async def _async_apply_inverter_control")
        executor_end = source.index("async def _async_update_data", executor_start)
        executor = source[executor_start:executor_end]

        self.assertIn('elif mode == "HOME_BATTERY_PRIORITY":', executor)
        self.assertIn('elif mode in ("NEGATIVE_IMPORT", "CHEAP_CHARGE"):', executor)
        self.assertIn('elif mode == "EMERGENCY_RESERVE":', executor)
        self.assertNotIn("BLOCKED_HOME_PRIORITY", executor)

    def test_grid_charging_programs_active_deye_tou_slot(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        executor_start = source.index("async def _async_apply_inverter_control")
        executor_end = source.index("async def _async_update_data", executor_start)
        executor = source[executor_start:executor_end]

        self.assertIn("def _active_tou_slot()", executor)
        self.assertIn('f"time.inverter_program_{slot}_time"', executor)
        self.assertIn('f"select.inverter_program_{slot}_charging"', executor)
        self.assertIn('f"number.inverter_program_{slot}_soc"', executor)
        self.assertIn("def add_tou_commands(*, grid_charge: bool, target_soc: float, reason: str)", executor)
        self.assertIn("_tou_charge_options", executor)
        self.assertIn('"no grid"', executor)
        self.assertIn("add_tou_commands(grid_charge=tou_grid_charge", executor)
        self.assertIn("and not full_soc_charge_lock", executor)
        self.assertIn('data.get("charge_target_soc")', executor)
        self.assertIn('data.get("cheap_charge_grid_target_soc")', executor)
        self.assertIn('data.get("discharge_target_soc")', executor)
        self.assertIn('data.get("self_use_reserve_soc")', executor)
        self.assertIn('tou_target_soc = minimum_soc', executor)
        self.assertIn('"rozładowanie do minimalnego SOC falownika"', executor)
        self.assertNotIn('executor_mode == "PREPARE_NEGATIVE_PRICE_WINDOW"', executor)
        self.assertIn('"AKTYWNE — PRZYWRÓCONO TRYB I CEL ROZŁADOWANIA"', executor)
        self.assertIn('"inverter_tou_control_status"', executor)

    def test_control_target_uses_calibrated_pv_forecast(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('learn.get("pv_forecast_factor")', source)
        self.assertIn("pv_tomorrow_for_control = max(0.0, pv_tomorrow * pv_forecast_factor)", source)
        self.assertIn("target_expected_24h_consumption_kwh - pv_reserve_forecast_kwh", source)
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
        self.assertIn("inverter_discharge_current_a", branch)
        self.assertNotIn("inverter_block_discharge_current_a", branch)
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
        self.assertIn("sensor.pstryk_json_buy", constants)
        self.assertIn("sensor.pstryk_json_sell", constants)
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
        self.assertIn("append_schedule(pstryk_current, pstryk_tomorrow)", helper)
        self.assertIn("append_schedule(modern_current, modern_schedule)", helper)

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

        self.assertIn("best_sell_price > sell_price + 0.01", condition)
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

    def test_strategy_does_not_limit_battery_discharge_to_five_amps(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        executor_start = source.index('if mode == "SAFE_MODE":')
        executor_end = source.index("\n        tou_grid_charge = (", executor_start)
        executor = source[executor_start:executor_end]

        self.assertNotIn(
            "num(inverter_max_discharge_current, inverter_block_discharge_current_a)",
            executor,
        )

        pv_export_start = executor.index('elif mode == "PV_PRICE_EXPORT":')
        pv_export_end = executor.index('elif (\n            mode == "SELL_BATTERY_HIGH_PRICE"', pv_export_start)
        pv_export = executor[pv_export_start:pv_export_end]
        self.assertIn("inverter_work_mode_pv_charge_option", pv_export)
        self.assertIn("num(inverter_max_charge_current, 0.0)", pv_export)
        self.assertIn("num(inverter_max_discharge_current, inverter_discharge_current_a)", pv_export)

    def test_home_priority_restores_self_consumption_instead_of_skipping_control(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        branch_start = source.index('elif mode == "HOME_BATTERY_PRIORITY":')
        branch_end = source.index("\n        elif (", branch_start)
        branch = source[branch_start:branch_end]

        self.assertIn("inverter_work_mode_pv_charge_option", branch)
        self.assertIn("sw(inverter_grid_charging, False)", branch)
        self.assertIn("num(inverter_max_discharge_current, inverter_discharge_current_a)", branch)
        self.assertNotIn("return data", branch)
        self.assertNotIn("BLOCKED_HOME_PRIORITY", source)
        self.assertNotIn("BLOCKED_BATTERY_TRADE_OFF", source)

    def test_only_safe_mode_uses_reduced_discharge_current(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        executor_start = source.index('if mode == "SAFE_MODE":')
        executor_end = source.index("\n        tou_grid_charge = (", executor_start)
        executor = source[executor_start:executor_end]

        self.assertEqual(
            1,
            executor.count(
                "num(inverter_max_discharge_current, inverter_safe_discharge_current_a)"
            ),
        )

    def test_deye_driver_sends_only_changed_commands_and_uses_configured_interval(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        self.assertIn("changed_commands.append((domain, entity_id, value))", source)
        self.assertIn("for domain, entity_id, value in commands_to_send:", source)
        self.assertIn("elapsed_since_last_send < deye_min_command_interval_seconds", source)
        self.assertNotIn("now_ts - float(last_ts or 0.0) < 120", source)
        self.assertIn('data["deye_driver_safety_status"] = "COMMAND_ERROR"', source)
        self.assertIn("commands_to_send = changed_commands[:max_changes]", source)
        self.assertIn("deferred_commands = changed_commands[max_changes:]", source)
        self.assertIn('data["deye_command_confirmation"] = "PARTIAL"', source)
        self.assertNotIn('data["deye_driver_safety_status"] = "BLOCKED_TOO_MANY_CHANGES"', source)

    def test_negative_price_preparation_uses_configured_limits(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        plan_start = source.index("def _negative_price_plan(")
        plan_end = source.index("def _pv_reality_data(", plan_start)
        plan = source[plan_start:plan_end]

        self.assertIn('self._runtime_float("economic_negative_prepare_hours", 6.0)', plan)
        self.assertIn('self._runtime_float("economic_min_energy_to_free_kwh", 0.5)', plan)
        self.assertIn('"economic_min_sell_price_prepare"', plan)
        self.assertIn("sell_price >= best_sell_price - 0.01", plan)

    def test_battery_export_requires_the_best_sale_window(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        self.assertIn("sell_price_trigger = best_window_sell_opportunity", source)
        self.assertNotIn("sell_price >= economic_good_sell_price\n            or best_window_sell_opportunity", source)
        self.assertIn("current_sell_price >= best_sell_price - 0.01", source)

    def test_night_charge_uses_today_pv_and_remembers_grid_energy_cost(self) -> None:
        coordinator = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        learning = (COMPONENT / "learning.py").read_text(encoding="utf-8")

        self.assertIn("def _reserve_pv_forecast(", coordinator)
        self.assertIn("use_today = local_hour < 12", coordinator)
        self.assertIn("morning_target_soc - expected_night_consumption_soc", coordinator)
        self.assertIn("16 if pv_coverage_ratio >= 0.80 else reserve_ready_by_hour", coordinator)
        self.assertIn('learn.get("stored_grid_charge_kwh")', coordinator)
        self.assertIn("stored_energy_sale_floor", coordinator)
        self.assertIn('learn["stored_grid_charge_kwh"]', learning)
        self.assertIn('learn["stored_grid_charge_cost_pln_per_kwh"]', learning)


if __name__ == "__main__":
    unittest.main()
