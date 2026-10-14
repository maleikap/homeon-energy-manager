from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import sys
import types
from zoneinfo import ZoneInfo


WARSAW = ZoneInfo("Europe/Warsaw")


class Clock:
    current = datetime(2026, 1, 1, tzinfo=WARSAW)

    @classmethod
    def set(cls, value: datetime) -> None:
        cls.current = value

    @classmethod
    def now(cls) -> datetime:
        return cls.current


def install_homeassistant_stubs() -> None:
    if "homeassistant.core" in sys.modules:
        return

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    const = types.ModuleType("homeassistant.const")
    helpers = types.ModuleType("homeassistant.helpers")
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
    storage = types.ModuleType("homeassistant.helpers.storage")
    util = types.ModuleType("homeassistant.util")
    dt_module = types.ModuleType("homeassistant.util.dt")

    class ConfigEntry:
        pass

    class HomeAssistant:
        pass

    class Platform(Enum):
        SENSOR = "sensor"
        SWITCH = "switch"
        NUMBER = "number"

    class DataUpdateCoordinator:
        def __init__(self, hass, *args, **kwargs):
            self.hass = hass

    class Store:
        def __init__(self, *args, **kwargs):
            pass

        async def async_load(self):
            return None

        async def async_save(self, data):
            return None

    def parse_datetime(value):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None

    dt_module.DEFAULT_TIME_ZONE = WARSAW
    dt_module.now = Clock.now
    dt_module.as_local = lambda value: value.astimezone(WARSAW)
    dt_module.parse_datetime = parse_datetime
    dt_module.utcnow = lambda: Clock.current.astimezone(timezone.utc)
    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    const.Platform = Platform
    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    storage.Store = Store
    util.dt = dt_module

    sys.modules.update(
        {
            "homeassistant": homeassistant,
            "homeassistant.config_entries": config_entries,
            "homeassistant.core": core,
            "homeassistant.const": const,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.update_coordinator": update_coordinator,
            "homeassistant.helpers.storage": storage,
            "homeassistant.util": util,
            "homeassistant.util.dt": dt_module,
        }
    )


@dataclass
class FakeState:
    state: str
    attributes: dict = field(default_factory=dict)


class FakeStates:
    def __init__(self, initial: dict[str, FakeState] | None = None):
        self.values = dict(initial or {})

    def get(self, entity_id: str):
        return self.values.get(entity_id)

    def set(self, entity_id: str, state, attributes: dict | None = None) -> None:
        self.values[entity_id] = FakeState(str(state), dict(attributes or {}))


class FakeServices:
    def __init__(self, states: FakeStates):
        self.states = states
        self.calls: list[tuple[str, str, dict]] = []

    async def async_call(self, domain: str, service: str, data: dict, blocking=True):
        self.calls.append((domain, service, dict(data)))
        entity_id = data.get("entity_id")
        if domain == "switch":
            self.states.set(entity_id, "on" if service == "turn_on" else "off")
        elif domain == "number":
            self.states.set(entity_id, data["value"])
        elif domain == "select":
            previous = self.states.get(entity_id)
            self.states.set(
                entity_id,
                data["option"],
                previous.attributes if previous is not None else {},
            )


class FakeHass:
    def __init__(self, states: dict[str, FakeState] | None = None):
        self.states = FakeStates(states)
        self.services = FakeServices(self.states)
        self.data: dict = {}
        self.config = types.SimpleNamespace(latitude=50.16)
        self.bus = types.SimpleNamespace(async_fire=lambda *args, **kwargs: None)


@dataclass
class FakeEntry:
    entry_id: str = "test-entry"
    data: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)


def price_rows(day: datetime, prices: list[float]) -> list[dict]:
    start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    return [
        {
            "start": (start.replace(hour=index)).isoformat(),
            "end": (
                start.replace(hour=index) if index < 23 else start.replace(hour=23)
            ).isoformat(),
            "price": price,
        }
        for index, price in enumerate(prices)
    ]
