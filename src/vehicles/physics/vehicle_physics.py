"""Vehicle Physics - realistic vehicle dynamics and handling."""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional

from ..types.vehicle_types import Vehicle


@dataclass
class WheelState:
    """State of a single vehicle wheel."""

    rotation: float = 0.0    # degrees
    angular_velocity: float = 0.0
    slip_ratio: float = 0.0   # 0 = no slip, 1 = full spin
    contact: bool = True


class VehiclePhysics:
    """Computes vehicle dynamics using a simplified vehicle model.

    Implements throttle/brake/steering response with traction limits,
    suspension simulation, and air-time handling for all vehicle
    categories (ground, water, air).
    """

    MAX_STEER_ANGLE: float = 35.0   # degrees

    def __init__(self, vehicle: Vehicle) -> None:
        self.vehicle: Vehicle = vehicle
        self.throttle: float = 0.0    # 0.0-1.0
        self.brake: float = 0.0       # 0.0-1.0
        self.steer: float = 0.0       # -1.0 (left) to 1.0 (right)
        self.handbrake: bool = False
        self._speed_ms: float = 0.0   # m/s
        self._heading_rad: float = 0.0
        self._drift_angle: float = 0.0
        self.wheels = [WheelState() for _ in range(4)]
        self.is_airborne: bool = False

    # ------------------------------------------------------------------ #
    # Input                                                                #
    # ------------------------------------------------------------------ #

    def set_input(
        self,
        throttle: float = 0.0,
        brake: float = 0.0,
        steer: float = 0.0,
        handbrake: bool = False,
    ) -> None:
        """Set driver input for this frame.

        All inputs are clamped to valid ranges.
        """
        self.throttle = max(0.0, min(1.0, throttle))
        self.brake = max(0.0, min(1.0, brake))
        self.steer = max(-1.0, min(1.0, steer))
        self.handbrake = handbrake

    # ------------------------------------------------------------------ #
    # Update                                                               #
    # ------------------------------------------------------------------ #

    def update(self, delta_time: float) -> None:
        """Advance the vehicle physics simulation.

        Args:
            delta_time: Frame time in seconds.
        """
        if self.vehicle.is_destroyed:
            return

        stats = self.vehicle.stats
        self._apply_throttle_and_brake(delta_time, stats)
        self._apply_steering(delta_time, stats)
        self._update_wheel_rotation(delta_time)
        self._update_position(delta_time)
        self._consume_fuel(delta_time)

    def _apply_throttle_and_brake(self, dt: float, stats: object) -> None:
        """Compute longitudinal speed change."""
        if self.vehicle.fuel <= 0.0:
            self.throttle = 0.0

        if self.brake > 0.0:
            decel = stats.braking * self.brake
            self._speed_ms = max(0.0, self._speed_ms - decel * dt)
        elif self.throttle > 0.0:
            accel = stats.acceleration * self.throttle * self._traction_factor()
            self._speed_ms = min(
                stats.max_speed, self._speed_ms + accel * dt
            )
        else:
            # Natural deceleration (rolling resistance + drag)
            self._speed_ms = max(0.0, self._speed_ms - 2.0 * dt)

        self.vehicle.speed = self._speed_ms

    def _apply_steering(self, dt: float, stats: object) -> None:
        """Update heading based on steering input and speed."""
        if self._speed_ms < 0.5:
            return
        speed_factor = min(1.0, self._speed_ms / 20.0)
        effective_steer = self.steer * self.MAX_STEER_ANGLE * stats.handling
        turn_rate = math.radians(effective_steer) * speed_factor / max(1.0, self._speed_ms * 0.1)

        if self.handbrake and self._speed_ms > 5.0:
            self._drift_angle += self.steer * 30.0 * dt
        else:
            self._drift_angle *= (1.0 - 5.0 * dt)

        self._heading_rad += turn_rate * dt
        self._heading_rad = self._heading_rad % (2 * math.pi)
        self.vehicle.heading = math.degrees(self._heading_rad)

    def _update_wheel_rotation(self, dt: float) -> None:
        """Spin wheel meshes in proportion to ground speed."""
        wheel_circumference = 2.0
        angular_speed = (self._speed_ms / wheel_circumference) * 360.0  # deg/s
        for wheel in self.wheels:
            wheel.rotation = (wheel.rotation + angular_speed * dt) % 360.0
            wheel.slip_ratio = max(0.0, self.throttle - 0.3) if self.throttle > 0.3 else 0.0

    def _update_position(self, dt: float) -> None:
        """Move the vehicle forward in its heading direction."""
        heading_rad = math.radians(self.vehicle.heading) + math.radians(self._drift_angle)
        dx = math.sin(heading_rad) * self._speed_ms * dt
        dz = math.cos(heading_rad) * self._speed_ms * dt
        x, y, z = self.vehicle.position
        self.vehicle.position = (x + dx, y, z + dz)

    def _traction_factor(self) -> float:
        """Return traction multiplier based on speed (wheel spin reduces it)."""
        if self._speed_ms < 5.0:
            return 0.7  # wheelspin on launch
        return 1.0

    def _consume_fuel(self, dt: float) -> None:
        """Reduce fuel based on throttle input."""
        stats = self.vehicle.stats
        consumption = stats.fuel_consumption * self.throttle * dt
        self.vehicle.fuel = max(0.0, self.vehicle.fuel - consumption)

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    @property
    def speed_kmh(self) -> float:
        return self._speed_ms * 3.6

    @property
    def speed_mph(self) -> float:
        return self._speed_ms * 2.237

    def __repr__(self) -> str:
        return (
            f"VehiclePhysics({self.vehicle.name!r}, "
            f"speed={self.speed_kmh:.1f}km/h, "
            f"heading={self.vehicle.heading:.1f}°)"
        )
