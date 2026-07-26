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
        self.assertEqual(manifest["version"], "0.2.44-beta.1")
        self.assertIn('VERSION = "0.2.44-beta.1"', const)

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
