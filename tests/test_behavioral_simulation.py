from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import unittest

from ha_test_support import (
    Clock,
    FakeEntry,
    FakeHass,
    FakeState,
    WARSAW,
    install_homeassistant_stubs,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
install_homeassistant_stubs()

from custom_components.homeon_energy_manager.const import DOMAIN  # noqa: E402
from custom_components.homeon_energy_manager.coordinator import (  # noqa: E402
    HomeOnEnergyCoordinator,
)
from custom_components.homeon_energy_manager.learning import update_learning  # noqa: E402


BUY = "sensor.test_buy"
SELL = "sensor.test_sell"


def rows(start: datetime, prices: list[float]) -> list[dict]:
    return [
        {
            "start": (start + timedelta(hours=index)).isoformat(),
            "end": (start + timedelta(hours=index + 1)).isoformat(),
            "price": price,
        }
        for index, price in enumerate(prices)
    ]


class BehavioralManagerSimulationTests(unittest.IsolatedAsyncioTestCase):
    def make_coordinator(self, now: datetime, runtime: dict | None = None):
        Clock.set(now)
        hass = FakeHass()
        entry = FakeEntry()
        hass.data = {
            DOMAIN: {
                entry.entry_id: {
                    "enabled": True,
                    "dry_run": False,
                    "inverter_control": True,
                    "battery_trade": True,
                    "profit_mode": True,
                    "deye_min_command_interval_seconds": 0,
                    "deye_max_changes_per_run": 20,
                    "inverter_discharge_current_a": 120,
                    "inverter_charge_current_a": 80,
                    "inverter_safe_discharge_current_a": 20,
                    "min_soc": 16,
                    **(runtime or {}),
                }
            }
        }
        coordinator = HomeOnEnergyCoordinator.__new__(HomeOnEnergyCoordinator)
        coordinator.hass = hass
        coordinator.entry = entry
        return coordinator

    @staticmethod
    def set_prices(coordinator, start: datetime, buy: list[float], sell: list[float]):
        coordinator.hass.states.set(BUY, buy[0], {"today_prices": rows(start, buy)})
        coordinator.hass.states.set(SELL, sell[0], {"today_prices": rows(start, sell)})

    def test_night_plan_charges_before_three_oclock_heat_pump(self):
        now = datetime(2026, 1, 10, 0, 5, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        prices = [0.55, 0.45, 0.65, 0.80, 0.35, 1.10, 1.50]
        self.set_prices(coordinator, now.replace(minute=0), prices, prices)
        profile = {
            f"{hour:02d}": {"avg_load_w": 400.0}
            for hour in range(24)
        }
        profile["03"] = {"avg_load_w": 5000.0}

        plan = coordinator._cheap_grid_charge_plan(
            BUY, prices[0], soc=35.0, target_soc=75.0,
            battery_capacity_kwh=30.0, reserve_ready_by_hour=3,
            minimum_soc=16.0, expected_net_load_w=400.0,
            hourly_profile=profile,
        )

        self.assertTrue(plan["schedule_available"])
        self.assertIn("01:00", plan["windows"])
        self.assertNotIn("04:00", plan["windows"])
        self.assertLessEqual(plan["required_hours"], 2)

    def test_manager_waits_for_cheaper_hour_when_battery_can_survive(self):
        now = datetime(2026, 1, 10, 0, 5, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        prices = [1.10, 0.80, 0.60, 0.40, 0.75, 1.20]
        self.set_prices(coordinator, now.replace(minute=0), prices, prices)

        plan = coordinator._cheap_grid_charge_plan(
            BUY, prices[0], soc=65.0, target_soc=80.0,
            battery_capacity_kwh=30.0, reserve_ready_by_hour=6,
            minimum_soc=16.0, expected_net_load_w=300.0,
            hourly_profile={},
        )

        self.assertFalse(plan["charge_now"])
        self.assertIn("03:00", plan["windows"])
        self.assertNotIn("00:00", plan["windows"])

    def test_missed_deadline_recovers_only_near_protected_floor(self):
        now = datetime(2026, 1, 10, 4, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        prices = [1.40, 0.35, 0.40]
        self.set_prices(coordinator, now, prices, prices)

        safe_plan = coordinator._cheap_grid_charge_plan(
            BUY, prices[0], soc=55.0, target_soc=75.0,
            battery_capacity_kwh=30.0, reserve_ready_by_hour=3,
            minimum_soc=16.0, expected_net_load_w=400.0,
            hourly_profile={},
        )
        emergency_plan = coordinator._cheap_grid_charge_plan(
            BUY, prices[0], soc=18.0, target_soc=75.0,
            battery_capacity_kwh=30.0, reserve_ready_by_hour=3,
            minimum_soc=16.0, expected_net_load_w=400.0,
            hourly_profile={},
        )

        self.assertFalse(safe_plan["recover_missed_reserve_now"])
        self.assertFalse(safe_plan["charge_now"])
        self.assertTrue(emergency_plan["recover_missed_reserve_now"])
        self.assertTrue(emergency_plan["charge_now"])

    def test_low_soc_uses_cheaper_hour_before_morning_price_rise(self):
        """Do not trust an unrealistically low load estimate close to minimum SOC."""
        now = datetime(2026, 10, 15, 5, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        prices = [
            1.09, 1.35, 1.55, 1.40, 0.40, 0.35, 0.30, 0.45,
            0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85,
            0.90, 0.95, 1.00, 0.90, 0.80, 0.70, 0.60, 0.50,
        ]
        self.set_prices(coordinator, now, prices, prices)

        plan = coordinator._cheap_grid_charge_plan(
            BUY, prices[0], soc=25.0, target_soc=75.0,
            battery_capacity_kwh=30.0, reserve_ready_by_hour=3,
            minimum_soc=16.0, expected_net_load_w=200.0,
            hourly_profile={},
        )

        self.assertTrue(plan["charge_now"])
        self.assertTrue(plan["predictive_precharge"])
        self.assertIn("05:00 (1.090 PLN/kWh)", plan["windows"])
        self.assertNotEqual("05:00", plan["predicted_depletion_by"])

    def test_started_hour_counts_only_remaining_minutes(self):
        now = datetime(2026, 1, 10, 4, 55, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        prices = [0.20, 0.90]
        self.set_prices(coordinator, now.replace(minute=0), prices, prices)

        plan = coordinator._cheap_grid_charge_plan(
            BUY, prices[0], soc=20.0, target_soc=60.0,
            battery_capacity_kwh=30.0, reserve_ready_by_hour=6,
            minimum_soc=16.0, expected_net_load_w=500.0,
            hourly_profile={},
        )

        self.assertGreater(plan["missing_kwh"], 6.0)
        self.assertIn("05:00", plan["windows"])

    def test_48_hour_trajectory_never_reaches_emergency_soc_or_buys_peak_energy(self):
        start = datetime(2026, 1, 10, 22, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(start)
        buy = []
        for step in range(48):
            hour = (start + timedelta(hours=step)).hour
            buy.append(
                0.32 if hour in {0, 1, 2}
                else 1.60 if hour in {6, 7, 8, 17, 18, 19}
                else 0.75
            )
        self.set_prices(coordinator, start, buy, buy)
        profile = {f"{hour:02d}": {"avg_load_w": 650.0} for hour in range(24)}
        profile["03"] = {"avg_load_w": 5000.0}
        pv_kwh = {
            8: 0.5, 9: 1.5, 10: 2.5, 11: 3.0, 12: 3.0,
            13: 2.5, 14: 1.5, 15: 0.5,
        }
        for hour, energy_kwh in pv_kwh.items():
            profile[f"{hour:02d}"]["avg_pv_w"] = energy_kwh * 1000.0
        capacity = 30.0
        energy = capacity * 0.50
        emergency_energy = capacity * 0.16
        charged_prices: list[float] = []
        peak_import_kwh = 0.0

        for step in range(48):
            now = start + timedelta(hours=step)
            Clock.set(now)
            coordinator.hass.states.set(BUY, buy[step], {"today_prices": rows(start, buy)})
            soc = energy / capacity * 100.0
            plan = coordinator._cheap_grid_charge_plan(
                BUY, buy[step], soc=soc, target_soc=75.0,
                battery_capacity_kwh=capacity, reserve_ready_by_hour=3,
                minimum_soc=16.0, expected_net_load_w=650.0,
                hourly_profile=profile,
            )
            if plan["charge_now"]:
                added = min(15.0, capacity * 0.95 - energy)
                energy += max(0.0, added)
                charged_prices.append(buy[step])

            load = 5.0 if now.hour == 3 else 0.65
            net_use = max(0.0, load - pv_kwh.get(now.hour, 0.0))
            available = max(0.0, energy - emergency_energy)
            from_battery = min(available, net_use)
            energy -= from_battery
            grid_import = net_use - from_battery
            if buy[step] >= 1.50:
                peak_import_kwh += grid_import
            energy = min(capacity, energy + max(0.0, pv_kwh.get(now.hour, 0.0) - load))

            self.assertGreaterEqual(energy + 0.001, emergency_energy)

        self.assertTrue(charged_prices)
        self.assertTrue(all(price < 1.50 for price in charged_prices))
        self.assertLess(peak_import_kwh, 0.01)

    def test_profit_mode_waits_for_better_sale_price(self):
        now = datetime(2026, 6, 10, 6, 30, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        buy = [0.30] * 24
        sell = [0.80, 1.27] + [0.50] * 22
        self.set_prices(coordinator, now.replace(minute=0), buy, sell)

        plan = coordinator._profit_mode_plan(
            BUY, SELL, current_buy_price=0.30, current_sell_price=0.80,
            soc=70.0, battery_capacity_kwh=30.0, reserve_soc=35.0,
            pv_forecast_today_kwh=7.0, pv_produced_today_kwh=0.0,
            expected_daily_consumption_kwh=30.0, consumed_today_kwh=4.0,
            minimum_soc=16.0, pv_power_w=0.0, load_power_w=800.0,
            enabled=True,
        )

        self.assertFalse(plan["sell_now"])
        self.assertEqual("OCZEKIWANIE", plan["status"])
        self.assertEqual(1.27, plan["best_sell_price"])

    def test_profit_mode_sells_now_and_can_refill_from_good_pv(self):
        now = datetime(2026, 6, 10, 7, 30, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        buy = [0.35] * 24
        sell = [0.98] + [0.70] * 23
        self.set_prices(coordinator, now.replace(minute=0), buy, sell)

        plan = coordinator._profit_mode_plan(
            BUY, SELL, current_buy_price=0.35, current_sell_price=0.98,
            soc=65.0, battery_capacity_kwh=30.0, reserve_soc=40.0,
            pv_forecast_today_kwh=45.0, pv_produced_today_kwh=1.0,
            expected_daily_consumption_kwh=30.0, consumed_today_kwh=3.0,
            minimum_soc=16.0, pv_power_w=3500.0, load_power_w=700.0,
            enabled=True,
        )

        self.assertTrue(plan["forecast_refill_allowed"])
        self.assertTrue(plan["sell_now"])
        self.assertEqual(16.0, plan["reserve_soc"])

    def test_good_pv_does_not_sell_battery_before_best_price(self):
        now = datetime(2026, 6, 10, 7, 30, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        buy = [0.35] * 24
        sell = [0.98, 1.27] + [0.70] * 22
        self.set_prices(coordinator, now.replace(minute=0), buy, sell)

        plan = coordinator._profit_mode_plan(
            BUY, SELL, current_buy_price=0.35, current_sell_price=0.98,
            soc=96.0, battery_capacity_kwh=30.0, reserve_soc=40.0,
            pv_forecast_today_kwh=70.0, pv_produced_today_kwh=1.0,
            expected_daily_consumption_kwh=30.0, consumed_today_kwh=3.0,
            minimum_soc=16.0, pv_power_w=3500.0, load_power_w=700.0,
            enabled=True,
        )

        self.assertTrue(plan["forecast_refill_allowed"])
        self.assertFalse(plan["current_good_pv_sale"])
        self.assertFalse(plan["sell_now"])
        self.assertEqual("OCZEKIWANIE", plan["status"])
        self.assertEqual(1.27, plan["best_sell_price"])

    def test_night_reserve_uses_today_forecast_after_midnight(self):
        coordinator = self.make_coordinator(datetime(2026, 10, 17, 3, 0, tzinfo=WARSAW))

        forecast, label = coordinator._reserve_pv_forecast(42.0, 7.0, 0.9, 3)

        self.assertAlmostEqual(37.8, forecast)
        self.assertEqual("dzisiaj", label)

        forecast, label = coordinator._reserve_pv_forecast(42.0, 7.0, 0.9, 20)

        self.assertAlmostEqual(6.3, forecast)
        self.assertEqual("jutro", label)

    def test_grid_bought_energy_is_not_sold_below_its_real_cost(self):
        now = datetime(2026, 10, 17, 7, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        buy = [0.97] + [0.60] * 23
        sell = [0.94] + [0.80] * 23
        self.set_prices(coordinator, now, buy, sell)

        plan = coordinator._profit_mode_plan(
            BUY, SELL, current_buy_price=0.97, current_sell_price=0.94,
            soc=95.0, battery_capacity_kwh=30.0, reserve_soc=35.0,
            pv_forecast_today_kwh=45.0, pv_produced_today_kwh=0.0,
            expected_daily_consumption_kwh=30.0, consumed_today_kwh=2.0,
            minimum_soc=16.0, pv_power_w=1500.0, load_power_w=500.0,
            enabled=True, stored_grid_charge_kwh=18.0,
            stored_grid_charge_cost_pln_per_kwh=0.97 / 0.94,
        )

        self.assertFalse(plan["profitable"])
        self.assertFalse(plan["sell_now"])
        self.assertGreater(plan["stored_energy_sale_floor"], 1.20)
        self.assertIn("Nie sprzedaję energii kupionej z sieci", plan["reason"])

    async def test_learning_remembers_grid_charge_cost_until_energy_is_used(self):
        now = datetime(2026, 10, 17, 3, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        data = {
            "mode": "CHEAP_CHARGE", "soc": 50.0, "battery_capacity_kwh": 30.0,
            "load_power": 1000.0, "pv_power": 0.0,
            "grid_import_w": 11000.0, "grid_export_w": 0.0,
            "battery_charge_w": 10000.0, "battery_discharge_w": 0.0,
            "deye_self_power": 0.0, "buy_price": 0.97, "sell_price": 0.80,
            "pv_forecast_today": 42.0, "pv_forecast_tomorrow": 7.0,
        }

        result = await update_learning(coordinator, data)

        self.assertGreater(result["learn_stored_grid_charge_kwh"], 0.0)
        self.assertAlmostEqual(0.97 / 0.94, result["learn_stored_grid_charge_cost"], places=3)

        Clock.set(now + timedelta(minutes=15))
        data.update({
            "mode": "NORMAL", "soc": 45.0, "grid_import_w": 0.0,
            "battery_charge_w": 0.0, "battery_discharge_w": 5000.0,
        })
        result = await update_learning(coordinator, data)

        self.assertEqual(0.0, result["learn_stored_grid_charge_kwh"])

    def configure_deye(self, coordinator):
        states = coordinator.hass.states
        states.set("select.inverter_work_mode", "Export First", {"options": ["Export First", "Zero Export To CT"]})
        states.set("switch.inverter_battery_grid_charging", "off")
        states.set("switch.inverter_export_surplus", "on")
        states.set("number.inverter_battery_max_charging_current", "80")
        states.set("number.inverter_battery_max_discharging_current", "5")
        states.set("time.inverter_program_1_time", "23:59")
        states.set("select.inverter_program_1_charging", "Grid", {"options": ["Grid", "No Grid"]})
        states.set("number.inverter_program_1_soc", "43")

    def configure_six_deye_tou_slots(self, coordinator):
        self.configure_deye(coordinator)
        starts = ("00:00", "02:00", "05:00", "08:00", "12:00", "18:00")
        for slot, start in enumerate(starts, start=1):
            coordinator.hass.states.set(f"time.inverter_program_{slot}_time", start)
            coordinator.hass.states.set(
                f"select.inverter_program_{slot}_charging",
                "Grid",
                {"options": ["Grid", "No Grid"]},
            )
            coordinator.hass.states.set(f"number.inverter_program_{slot}_soc", "43")

    async def test_tou_updates_current_period_not_next_future_period(self):
        """Deye program times are period starts, not the preceding period ends."""
        now = datetime(2026, 10, 16, 3, 30, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        self.configure_six_deye_tou_slots(coordinator)
        data = {
            "mode": "NORMAL", "soc": 48.0, "min_soc": 16.0,
            "night_self_use_active": True, "self_use_reserve_soc": 48.0,
            "discharge_target_soc": 75.0, "sell_price": 1.35,
            "pv_power": 0.0, "load_power": 1167.0,
            "economic_pv_export_opportunity": "OFF", "plan_safe_to_sell_kwh": 0.0,
        }

        result = await coordinator._async_apply_inverter_control(data)

        self.assertEqual(2, result["inverter_tou_active_slot"])
        self.assertEqual("No Grid", coordinator.hass.states.get("select.inverter_program_2_charging").state)
        self.assertEqual("16.0", coordinator.hass.states.get("number.inverter_program_2_soc").state)
        self.assertEqual("Grid", coordinator.hass.states.get("select.inverter_program_3_charging").state)
        self.assertEqual("43", coordinator.hass.states.get("number.inverter_program_3_soc").state)

    async def test_tou_last_period_remains_active_until_midnight(self):
        now = datetime(2026, 10, 16, 23, 30, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        self.configure_six_deye_tou_slots(coordinator)
        data = {
            "mode": "NORMAL", "soc": 48.0, "min_soc": 16.0,
            "night_self_use_active": True, "self_use_reserve_soc": 48.0,
            "discharge_target_soc": 75.0, "sell_price": 1.35,
            "pv_power": 0.0, "load_power": 1167.0,
            "economic_pv_export_opportunity": "OFF", "plan_safe_to_sell_kwh": 0.0,
        }

        result = await coordinator._async_apply_inverter_control(data)

        self.assertEqual(6, result["inverter_tou_active_slot"])
        self.assertEqual("No Grid", coordinator.hass.states.get("select.inverter_program_6_charging").state)
        self.assertEqual("16.0", coordinator.hass.states.get("number.inverter_program_6_soc").state)
        self.assertEqual("Grid", coordinator.hass.states.get("select.inverter_program_1_charging").state)
        self.assertEqual("43", coordinator.hass.states.get("number.inverter_program_1_soc").state)

    async def test_cheap_charge_is_written_to_the_current_tou_period(self):
        now = datetime(2026, 10, 16, 3, 30, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        self.configure_six_deye_tou_slots(coordinator)
        coordinator.hass.states.set("select.inverter_program_2_charging", "No Grid", {"options": ["Grid", "No Grid"]})
        coordinator.hass.states.set("number.inverter_program_2_soc", "16")
        data = {
            "mode": "CHEAP_CHARGE", "soc": 25.0, "min_soc": 16.0,
            "night_self_use_active": True, "self_use_reserve_soc": 35.0,
            "discharge_target_soc": 35.0, "charge_target_soc": 75.0,
            "cheap_charge_grid_target_soc": 75.0, "sell_price": 0.40,
            "pv_power": 0.0, "load_power": 500.0,
            "economic_pv_export_opportunity": "OFF", "plan_safe_to_sell_kwh": 0.0,
        }

        result = await coordinator._async_apply_inverter_control(data)

        self.assertEqual(2, result["inverter_tou_active_slot"])
        self.assertEqual("Grid", coordinator.hass.states.get("select.inverter_program_2_charging").state)
        self.assertEqual("75.0", coordinator.hass.states.get("number.inverter_program_2_soc").state)
        self.assertEqual("Grid", coordinator.hass.states.get("select.inverter_program_3_charging").state)
        self.assertEqual("43", coordinator.hass.states.get("number.inverter_program_3_soc").state)

    async def test_wait_mode_restores_self_use_full_current_and_minimum_tou_soc(self):
        now = datetime(2026, 1, 10, 20, 30, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        self.configure_deye(coordinator)
        data = {
            "mode": "WAIT_BETTER_SELL_PRICE", "soc": 35.0, "min_soc": 16.0,
            "night_self_use_active": True, "self_use_reserve_soc": 40.0,
            "discharge_target_soc": 40.0, "sell_price": 0.80,
            "pv_power": 0.0, "load_power": 500.0,
            "economic_pv_export_opportunity": "OFF", "plan_safe_to_sell_kwh": 0.0,
        }

        result = await coordinator._async_apply_inverter_control(data)

        self.assertEqual("Zero Export To CT", coordinator.hass.states.get("select.inverter_work_mode").state)
        self.assertEqual("120.0", coordinator.hass.states.get("number.inverter_battery_max_discharging_current").state)
        self.assertEqual("No Grid", coordinator.hass.states.get("select.inverter_program_1_charging").state)
        self.assertEqual("16.0", coordinator.hass.states.get("number.inverter_program_1_soc").state)
        self.assertNotEqual("5.0", coordinator.hass.states.get("number.inverter_battery_max_discharging_current").state)
        self.assertIn(result["deye_command_confirmation"], {"SENT", "PARTIAL"})

    async def test_weak_pv_protection_blocks_trade_but_not_house_self_use(self):
        now = datetime(2026, 10, 14, 9, 16, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        self.configure_deye(coordinator)
        data = {
            "mode": "WEATHER_HOLD_RESERVE", "soc": 60.0, "min_soc": 16.0,
            "night_self_use_active": False, "self_use_reserve_soc": 60.0,
            "discharge_target_soc": 75.0, "sell_price": 0.80,
            "pv_power": 586.0, "load_power": 1382.0,
            "economic_pv_export_opportunity": "OFF", "plan_safe_to_sell_kwh": 0.0,
        }

        result = await coordinator._async_apply_inverter_control(data)

        self.assertEqual("WEATHER_HOLD_RESERVE", result["inverter_control_executor_mode"])
        self.assertEqual("Zero Export To CT", coordinator.hass.states.get("select.inverter_work_mode").state)
        self.assertEqual("120.0", coordinator.hass.states.get("number.inverter_battery_max_discharging_current").state)
        self.assertEqual("No Grid", coordinator.hass.states.get("select.inverter_program_1_charging").state)
        self.assertEqual("16.0", coordinator.hass.states.get("number.inverter_program_1_soc").state)

    async def test_normal_mode_prioritizes_commands_that_enable_self_use(self):
        """A command limit must not defer TOU SOC while the home imports power."""
        now = datetime(2026, 10, 15, 7, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(
            now,
            runtime={"deye_max_changes_per_run": 4},
        )
        self.configure_deye(coordinator)
        coordinator.hass.states.set("switch.inverter_battery_grid_charging", "on")
        coordinator.hass.states.set("switch.inverter_export_surplus", "off")
        coordinator.hass.states.set("number.inverter_battery_max_charging_current", "20")
        data = {
            "mode": "NORMAL", "soc": 48.0, "min_soc": 16.0,
            "night_self_use_active": True, "self_use_reserve_soc": 48.0,
            "discharge_target_soc": 75.0, "sell_price": 1.35,
            "pv_power": 0.0, "load_power": 1167.0,
            "economic_pv_export_opportunity": "OFF", "plan_safe_to_sell_kwh": 0.0,
        }

        result = await coordinator._async_apply_inverter_control(data)

        self.assertEqual("PARTIAL_CHANGE_LIMIT", result["deye_driver_safety_status"])
        self.assertEqual("Zero Export To CT", coordinator.hass.states.get("select.inverter_work_mode").state)
        self.assertEqual("120.0", coordinator.hass.states.get("number.inverter_battery_max_discharging_current").state)
        self.assertEqual("No Grid", coordinator.hass.states.get("select.inverter_program_1_charging").state)
        self.assertEqual("16.0", coordinator.hass.states.get("number.inverter_program_1_soc").state)

    async def test_command_limit_prioritizes_grid_charge_tou_controls(self):
        """The same priority mechanism must still start a planned grid charge."""
        now = datetime(2026, 10, 15, 5, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(
            now,
            runtime={"deye_max_changes_per_run": 4},
        )
        self.configure_deye(coordinator)
        coordinator.hass.states.set("switch.inverter_battery_grid_charging", "off")
        coordinator.hass.states.set("number.inverter_program_1_soc", "16")
        data = {
            "mode": "CHEAP_CHARGE", "soc": 25.0, "min_soc": 16.0,
            "night_self_use_active": True, "self_use_reserve_soc": 35.0,
            "discharge_target_soc": 35.0, "charge_target_soc": 75.0,
            "cheap_charge_grid_target_soc": 75.0, "sell_price": 0.40,
            "pv_power": 0.0, "load_power": 500.0,
            "economic_pv_export_opportunity": "OFF", "plan_safe_to_sell_kwh": 0.0,
        }

        result = await coordinator._async_apply_inverter_control(data)

        self.assertEqual("PARTIAL_CHANGE_LIMIT", result["deye_driver_safety_status"])
        self.assertEqual("Zero Export To CT", coordinator.hass.states.get("select.inverter_work_mode").state)
        self.assertEqual("on", coordinator.hass.states.get("switch.inverter_battery_grid_charging").state)
        self.assertEqual("Grid", coordinator.hass.states.get("select.inverter_program_1_charging").state)
        self.assertEqual("75.0", coordinator.hass.states.get("number.inverter_program_1_soc").state)

    async def test_load_installation_restores_zero_export_to_load(self):
        now = datetime(2026, 10, 15, 7, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        self.configure_deye(coordinator)
        coordinator.hass.states.set(
            "select.inverter_work_mode",
            "Export First",
            {"options": ["Export First", "Zero Export To CT", "Zero Export To Load"]},
        )
        data = {
            "mode": "NORMAL", "soc": 48.0, "min_soc": 16.0,
            "installation_type": "LOAD", "night_self_use_active": True,
            "self_use_reserve_soc": 48.0, "discharge_target_soc": 75.0,
            "sell_price": 1.35, "pv_power": 0.0, "load_power": 1167.0,
            "economic_pv_export_opportunity": "OFF", "plan_safe_to_sell_kwh": 0.0,
        }

        await coordinator._async_apply_inverter_control(data)

        self.assertEqual("Zero Export To Load", coordinator.hass.states.get("select.inverter_work_mode").state)
        self.assertEqual("120.0", coordinator.hass.states.get("number.inverter_battery_max_discharging_current").state)
        self.assertEqual("No Grid", coordinator.hass.states.get("select.inverter_program_1_charging").state)
        self.assertEqual("16.0", coordinator.hass.states.get("number.inverter_program_1_soc").state)

    async def test_full_battery_stops_charge_and_exports_positive_price_pv(self):
        now = datetime(2026, 6, 10, 12, 0, tzinfo=WARSAW)
        coordinator = self.make_coordinator(now)
        self.configure_deye(coordinator)
        coordinator.hass.states.set("select.inverter_work_mode", "Zero Export To CT")
        data = {
            "mode": "PV_CHARGE", "soc": 100.0, "min_soc": 16.0,
            "night_self_use_active": False, "self_use_reserve_soc": 35.0,
            "discharge_target_soc": 35.0, "sell_price": 0.78,
            "pv_power": 8000.0, "load_power": 800.0,
            "economic_pv_export_opportunity": "ON", "plan_safe_to_sell_kwh": 0.0,
        }

        await coordinator._async_apply_inverter_control(data)

        self.assertEqual("Export First", coordinator.hass.states.get("select.inverter_work_mode").state)
        self.assertEqual("0.0", coordinator.hass.states.get("number.inverter_battery_max_charging_current").state)
        self.assertEqual("off", coordinator.hass.states.get("switch.inverter_battery_grid_charging").state)
        self.assertEqual("on", coordinator.hass.states.get("switch.inverter_export_surplus").state)


if __name__ == "__main__":
    unittest.main()
