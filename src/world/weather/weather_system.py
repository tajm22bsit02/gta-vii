"""Weather System - dynamic weather and day/night cycle."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional


class WeatherCondition(Enum):
    """Available weather states."""

    CLEAR = auto()
    CLOUDY = auto()
    OVERCAST = auto()
    RAIN = auto()
    HEAVY_RAIN = auto()
    THUNDERSTORM = auto()
    FOG = auto()
    SNOW = auto()
    HEATWAVE = auto()


@dataclass
class WeatherState:
    """Current weather snapshot."""

    condition: WeatherCondition = WeatherCondition.CLEAR
    temperature: float = 22.0  # Celsius
    wind_speed: float = 0.0    # m/s
    wind_direction: float = 0.0  # degrees
    precipitation: float = 0.0   # 0.0-1.0
    fog_density: float = 0.0     # 0.0-1.0
    cloud_cover: float = 0.0     # 0.0-1.0
    visibility: float = 1000.0   # metres

    def is_raining(self) -> bool:
        return self.condition in (
            WeatherCondition.RAIN,
            WeatherCondition.HEAVY_RAIN,
            WeatherCondition.THUNDERSTORM,
        )

    def is_nighttime_friendly(self) -> bool:
        """Return False for conditions that reduce night-time visibility."""
        return self.fog_density < 0.5 and self.precipitation < 0.3


class TimeOfDay:
    """Represents the current game time (24-hour cycle)."""

    SECONDS_PER_GAME_HOUR = 120  # 2 real minutes = 1 game hour

    def __init__(self, hour: float = 12.0) -> None:
        self.time: float = hour  # 0.0-23.999...

    def advance(self, delta_time: float) -> None:
        """Advance by delta_time real seconds."""
        game_hours = delta_time / self.SECONDS_PER_GAME_HOUR
        self.time = (self.time + game_hours) % 24.0

    @property
    def hour(self) -> int:
        """Integer hour (0-23)."""
        return int(self.time)

    @property
    def minute(self) -> int:
        """Integer minute (0-59)."""
        return int((self.time % 1.0) * 60)

    def is_daytime(self) -> bool:
        """Return True between 06:00 and 20:00."""
        return 6.0 <= self.time < 20.0

    def sun_angle(self) -> float:
        """Return the sun's angle in degrees (0° at midnight, 90° at noon)."""
        return (self.time / 24.0) * 360.0

    def sky_brightness(self) -> float:
        """Return ambient sky brightness between 0.0 (night) and 1.0 (noon)."""
        angle = math.radians(self.sun_angle() - 90)
        return max(0.0, math.sin(angle))

    def __str__(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}"


WeatherChangeCallback = Callable[[WeatherCondition, WeatherCondition], None]

# Weighted transition table: condition -> list of (next_condition, weight)
_TRANSITIONS: dict = {
    WeatherCondition.CLEAR: [
        (WeatherCondition.CLEAR, 70),
        (WeatherCondition.CLOUDY, 20),
        (WeatherCondition.FOG, 5),
        (WeatherCondition.HEATWAVE, 5),
    ],
    WeatherCondition.CLOUDY: [
        (WeatherCondition.CLEAR, 30),
        (WeatherCondition.CLOUDY, 30),
        (WeatherCondition.OVERCAST, 25),
        (WeatherCondition.RAIN, 15),
    ],
    WeatherCondition.OVERCAST: [
        (WeatherCondition.CLOUDY, 20),
        (WeatherCondition.OVERCAST, 20),
        (WeatherCondition.RAIN, 40),
        (WeatherCondition.FOG, 20),
    ],
    WeatherCondition.RAIN: [
        (WeatherCondition.CLOUDY, 30),
        (WeatherCondition.RAIN, 40),
        (WeatherCondition.HEAVY_RAIN, 20),
        (WeatherCondition.THUNDERSTORM, 10),
    ],
    WeatherCondition.HEAVY_RAIN: [
        (WeatherCondition.RAIN, 50),
        (WeatherCondition.HEAVY_RAIN, 20),
        (WeatherCondition.THUNDERSTORM, 30),
    ],
    WeatherCondition.THUNDERSTORM: [
        (WeatherCondition.HEAVY_RAIN, 50),
        (WeatherCondition.RAIN, 30),
        (WeatherCondition.THUNDERSTORM, 20),
    ],
    WeatherCondition.FOG: [
        (WeatherCondition.CLEAR, 40),
        (WeatherCondition.FOG, 30),
        (WeatherCondition.CLOUDY, 30),
    ],
    WeatherCondition.SNOW: [
        (WeatherCondition.SNOW, 60),
        (WeatherCondition.OVERCAST, 30),
        (WeatherCondition.CLEAR, 10),
    ],
    WeatherCondition.HEATWAVE: [
        (WeatherCondition.CLEAR, 60),
        (WeatherCondition.HEATWAVE, 30),
        (WeatherCondition.CLOUDY, 10),
    ],
}


class WeatherSystem:
    """Drives the dynamic weather and day/night cycle.

    Weather transitions probabilistically according to a Markov-chain
    transition table. The caller receives callbacks on every change.
    """

    CHANGE_INTERVAL_SECONDS: float = 300.0  # 5 minutes between checks

    def __init__(
        self,
        initial_condition: WeatherCondition = WeatherCondition.CLEAR,
        initial_hour: float = 12.0,
    ) -> None:
        self.current: WeatherState = self._build_state(initial_condition)
        self.time_of_day: TimeOfDay = TimeOfDay(initial_hour)
        self._change_callbacks: List[WeatherChangeCallback] = []
        self._time_since_last_change: float = 0.0

    # ------------------------------------------------------------------ #
    # Update                                                               #
    # ------------------------------------------------------------------ #

    def update(self, delta_time: float) -> None:
        """Advance weather simulation by delta_time real seconds."""
        self.time_of_day.advance(delta_time)
        self._time_since_last_change += delta_time

        if self._time_since_last_change >= self.CHANGE_INTERVAL_SECONDS:
            self._time_since_last_change = 0.0
            self._maybe_transition()

    # ------------------------------------------------------------------ #
    # Callbacks                                                            #
    # ------------------------------------------------------------------ #

    def add_change_callback(self, callback: WeatherChangeCallback) -> None:
        """Register a callback invoked on weather change."""
        self._change_callbacks.append(callback)

    def force_condition(self, condition: WeatherCondition) -> None:
        """Immediately set the weather to a specific condition."""
        old = self.current.condition
        self.current = self._build_state(condition)
        self._notify(old, condition)

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _maybe_transition(self) -> None:
        old_condition = self.current.condition
        transitions = _TRANSITIONS.get(old_condition, [])
        if not transitions:
            return

        conditions, weights = zip(*transitions)
        new_condition = random.choices(list(conditions), weights=list(weights), k=1)[0]

        if new_condition != old_condition:
            self.current = self._build_state(new_condition)
            self._notify(old_condition, new_condition)

    def _notify(
        self, old: WeatherCondition, new: WeatherCondition
    ) -> None:
        for cb in self._change_callbacks:
            cb(old, new)

    @staticmethod
    def _build_state(condition: WeatherCondition) -> WeatherState:
        """Build a WeatherState for the given condition."""
        presets: dict = {
            WeatherCondition.CLEAR: WeatherState(
                condition, 24.0, 5.0, 180.0, 0.0, 0.0, 0.05, 5000.0
            ),
            WeatherCondition.CLOUDY: WeatherState(
                condition, 18.0, 10.0, 200.0, 0.0, 0.0, 0.5, 3000.0
            ),
            WeatherCondition.OVERCAST: WeatherState(
                condition, 15.0, 15.0, 210.0, 0.1, 0.1, 0.9, 2000.0
            ),
            WeatherCondition.RAIN: WeatherState(
                condition, 14.0, 20.0, 220.0, 0.5, 0.1, 0.8, 500.0
            ),
            WeatherCondition.HEAVY_RAIN: WeatherState(
                condition, 12.0, 35.0, 230.0, 0.8, 0.2, 1.0, 200.0
            ),
            WeatherCondition.THUNDERSTORM: WeatherState(
                condition, 11.0, 60.0, 240.0, 1.0, 0.3, 1.0, 100.0
            ),
            WeatherCondition.FOG: WeatherState(
                condition, 10.0, 2.0, 0.0, 0.0, 0.9, 0.3, 50.0
            ),
            WeatherCondition.SNOW: WeatherState(
                condition, -2.0, 10.0, 0.0, 0.3, 0.0, 0.8, 300.0
            ),
            WeatherCondition.HEATWAVE: WeatherState(
                condition, 38.0, 2.0, 0.0, 0.0, 0.0, 0.0, 8000.0
            ),
        }
        return presets.get(condition, WeatherState(condition=condition))

    def __repr__(self) -> str:
        return (
            f"WeatherSystem(condition={self.current.condition.name}, "
            f"time={self.time_of_day})"
        )
