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
        self.assertEqual("1.2.13", manifest["version"])
        for filename in ("sensor.py", "number.py", "switch.py"):
            source = (COMPONENT / filename).read_text(encoding="utf-8")
            self.assertIn('"sw_version": "1.2.13"', source)

    def test_wait_for_better_price_charges_pv_instead_of_exporting(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        branch_start = source.index('elif mode == "WAIT_BETTER_SELL_PRICE":')
        branch_end = source.index('elif mode == "PV_CHARGE":', branch_start)
        branch = source[branch_start:branch_end]

        self.assertIn("inverter_work_mode_pv_charge_option", branch)
        self.assertIn("sw(inverter_export_surplus, False)", branch)
        self.assertIn("num(inverter_max_charge_current, inverter_charge_current_a)", branch)
        self.assertIn("num(inverter_max_discharge_current, 0.0)", branch)
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
        branch_start = coordinator.index('elif mode == "PV_PRICE_EXPORT":')
        branch_end = coordinator.index('elif (', branch_start)
        branch = coordinator[branch_start:branch_end]

        self.assertIn("if full_soc_charge_lock", branch)
        self.assertIn("inverter_work_mode_pv_charge_option", branch)
        self.assertIn("num(inverter_max_discharge_current, 0.0)", branch)
        self.assertIn("sw(inverter_export_surplus, sell_solar_allowed)", branch)
        self.assertIn('current_mode == "WAIT_BETTER_SELL_PRICE" and soc >= 99.0', planner)
        self.assertIn("pv_reality_lock and min_soc < soc < 99.0", coordinator)

    def test_full_soc_charge_cutoff_has_hysteresis_and_overrides_every_mode(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")

        self.assertIn("if current_soc >= 99.0", source)
        self.assertIn("elif current_soc <= 97.0", source)
        self.assertIn('data["inverter_full_soc_charge_lock"]', source)
        self.assertIn("if full_soc_charge_lock:", source)
        self.assertIn("num(inverter_max_charge_current, 0.0)", source)
        self.assertIn("sw(inverter_grid_charging, False)", source)


if __name__ == "__main__":
    unittest.main()
