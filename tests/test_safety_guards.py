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
        self.assertEqual(manifest["version"], "0.2.44-beta.4")
        self.assertIn('VERSION = "0.2.44-beta.4"', const)

    def test_pv_installed_power_is_available_and_persistent(self) -> None:
        init_source = (COMPONENT / "__init__.py").read_text(encoding="utf-8")
        number_source = (COMPONENT / "number.py").read_text(encoding="utf-8")
        coordinator_source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('"pv_installed_kwp": 0.0', init_source)
        self.assertIn('"pv_installed_kwp"', number_source)
        self.assertIn('"Moc paneli PV – suma kWp"', number_source)
        self.assertIn('options[self._key] = final_value', number_source)
        self.assertIn('self._runtime_float("pv_installed_kwp", 0.0)', coordinator_source)

    def test_discharge_target_is_a_hard_floor(self) -> None:
        source = (COMPONENT / "coordinator.py").read_text(encoding="utf-8")
        self.assertIn('elif soc <= discharge_target_soc:', source)
        self.assertIn('mode = "DISCHARGE_TARGET_HOLD"', source)
        self.assertIn(
            'buy_price >= economic_expensive_buy_price and soc > discharge_target_soc',
            source,
        )
        self.assertNotIn(
            'buy_price >= economic_expensive_buy_price and soc > min_soc',
            source,
        )
        hold_executor = source.split('elif mode == "DISCHARGE_TARGET_HOLD":', 1)[1].split(
            'elif mode == "SELL_BATTERY_HIGH_PRICE"', 1
        )[0]
        self.assertIn("sw(inverter_grid_charging, False)", hold_executor)
        self.assertIn(
            "num(inverter_max_discharge_current, inverter_block_discharge_current_a)",
            hold_executor,
        )
        urgent_block = source.split("urgent_modes = {", 1)[1].split("}", 1)[0]
        self.assertIn('"DISCHARGE_TARGET_HOLD"', urgent_block)

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
