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
        self.assertEqual("1.2.9", manifest["version"])
        for filename in ("sensor.py", "number.py", "switch.py"):
            source = (COMPONENT / filename).read_text(encoding="utf-8")
            self.assertIn('"sw_version": "1.2.9"', source)


if __name__ == "__main__":
    unittest.main()
