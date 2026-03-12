"""Traffic System - vehicle traffic simulation for the open world."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class TrafficVehicleType(Enum):
    """Categories of traffic vehicles."""

    CAR = auto()
    TRUCK = auto()
    BUS = auto()
    MOTORCYCLE = auto()
    TAXI = auto()
    POLICE = auto()
    AMBULANCE = auto()
    FIRE_TRUCK = auto()


class TrafficState(Enum):
    """Behavioural states for a traffic vehicle."""

    MOVING = auto()
    STOPPED = auto()
    TURNING = auto()
    PARKED = auto()
    EMERGENCY = auto()


@dataclass
class TrafficVehicle:
    """A single NPC vehicle participating in the traffic simulation."""

    vehicle_id: str
    vehicle_type: TrafficVehicleType
    position: Tuple[float, float]
    heading: float = 0.0          # degrees, 0 = north
    speed: float = 0.0            # m/s
    max_speed: float = 13.9       # ~50 km/h default
    state: TrafficState = TrafficState.STOPPED
    destination: Optional[Tuple[float, float]] = None
    active: bool = True

    def update(self, delta_time: float) -> None:
        """Advance position towards destination."""
        if not self.active or self.destination is None:
            return
        if self.state == TrafficState.PARKED:
            return

        dx = self.destination[0] - self.position[0]
        dy = self.destination[1] - self.position[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 5.0:
            self.state = TrafficState.STOPPED
            return

        self.state = TrafficState.MOVING
        self.heading = math.degrees(math.atan2(dy, dx))
        move_dist = min(self.speed * delta_time, dist)
        nx = dx / dist
        ny = dy / dist
        self.position = (
            self.position[0] + nx * move_dist,
            self.position[1] + ny * move_dist,
        )

    def accelerate(self, delta_time: float, acceleration: float = 3.0) -> None:
        """Increase speed up to max_speed."""
        self.speed = min(self.speed + acceleration * delta_time, self.max_speed)

    def brake(self, delta_time: float, deceleration: float = 6.0) -> None:
        """Reduce speed to zero."""
        self.speed = max(0.0, self.speed - deceleration * delta_time)


class TrafficLight:
    """A traffic light with configurable phase timings."""

    def __init__(
        self,
        position: Tuple[float, float],
        green_duration: float = 30.0,
        yellow_duration: float = 5.0,
        red_duration: float = 30.0,
    ) -> None:
        self.position: Tuple[float, float] = position
        self.green_duration: float = green_duration
        self.yellow_duration: float = yellow_duration
        self.red_duration: float = red_duration
        self._phase: str = "green"
        self._timer: float = 0.0

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def is_stop(self) -> bool:
        """Return True when vehicles should stop (red or yellow)."""
        return self._phase in ("red", "yellow")

    def update(self, delta_time: float) -> None:
        """Advance the signal phase."""
        self._timer += delta_time
        durations = {"green": self.green_duration, "yellow": self.yellow_duration, "red": self.red_duration}
        transitions = {"green": "yellow", "yellow": "red", "red": "green"}
        if self._timer >= durations[self._phase]:
            self._timer = 0.0
            self._phase = transitions[self._phase]


class TrafficSystem:
    """Manages NPC vehicle spawning, routing, and despawning.

    Vehicles are spawned procedurally around a centre of interest (usually
    the player position) and despawned when they travel too far away.
    """

    MAX_VEHICLES: int = 80
    SPAWN_RADIUS: float = 500.0
    DESPAWN_RADIUS: float = 700.0
    SPAWN_INTERVAL: float = 5.0  # seconds between spawn attempts

    def __init__(self) -> None:
        self._vehicles: Dict[str, TrafficVehicle] = {}
        self._traffic_lights: List[TrafficLight] = []
        self._spawn_timer: float = 0.0
        self._id_counter: int = 0
        self._centre: Tuple[float, float] = (0.0, 0.0)

    # ------------------------------------------------------------------ #
    # Update                                                               #
    # ------------------------------------------------------------------ #

    def update(self, delta_time: float, player_position: Tuple[float, float]) -> None:
        """Advance the traffic simulation.

        Args:
            delta_time: Time elapsed since the last tick in seconds.
            player_position: Current player world position for spawn/despawn.
        """
        self._centre = player_position
        self._spawn_timer += delta_time

        for light in self._traffic_lights:
            light.update(delta_time)

        for vehicle in list(self._vehicles.values()):
            self._apply_traffic_rules(vehicle, delta_time)
            vehicle.update(delta_time)
            vehicle.accelerate(delta_time)

        if self._spawn_timer >= self.SPAWN_INTERVAL:
            self._spawn_timer = 0.0
            self._try_spawn()

        self._despawn_distant(player_position)

    def _apply_traffic_rules(self, vehicle: TrafficVehicle, delta_time: float) -> None:
        """Apply traffic light and collision-avoidance rules."""
        for light in self._traffic_lights:
            dx = light.position[0] - vehicle.position[0]
            dy = light.position[1] - vehicle.position[1]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < 20.0 and light.is_stop:
                vehicle.brake(delta_time)
                return

    # ------------------------------------------------------------------ #
    # Spawn / despawn                                                      #
    # ------------------------------------------------------------------ #

    def _try_spawn(self) -> None:
        if len(self._vehicles) >= self.MAX_VEHICLES:
            return
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(self.SPAWN_RADIUS * 0.5, self.SPAWN_RADIUS)
        spawn_x = self._centre[0] + math.cos(angle) * dist
        spawn_y = self._centre[1] + math.sin(angle) * dist
        dest_x = self._centre[0] + math.cos(angle + math.pi) * dist
        dest_y = self._centre[1] + math.sin(angle + math.pi) * dist

        vehicle_type = random.choice(list(TrafficVehicleType))
        self._id_counter += 1
        vehicle_id = f"traffic_{self._id_counter}"
        vehicle = TrafficVehicle(
            vehicle_id=vehicle_id,
            vehicle_type=vehicle_type,
            position=(spawn_x, spawn_y),
            destination=(dest_x, dest_y),
            max_speed=random.uniform(8.0, 16.7),
        )
        self._vehicles[vehicle_id] = vehicle

    def _despawn_distant(self, player_position: Tuple[float, float]) -> None:
        to_remove = []
        for vid, vehicle in self._vehicles.items():
            dx = vehicle.position[0] - player_position[0]
            dy = vehicle.position[1] - player_position[1]
            if (dx * dx + dy * dy) > self.DESPAWN_RADIUS ** 2:
                to_remove.append(vid)
        for vid in to_remove:
            del self._vehicles[vid]

    # ------------------------------------------------------------------ #
    # Traffic lights                                                       #
    # ------------------------------------------------------------------ #

    def add_traffic_light(self, light: TrafficLight) -> None:
        """Add a traffic light to the simulation."""
        self._traffic_lights.append(light)

    # ------------------------------------------------------------------ #
    # Accessors                                                            #
    # ------------------------------------------------------------------ #

    @property
    def vehicle_count(self) -> int:
        return len(self._vehicles)

    def get_vehicles_near(
        self, position: Tuple[float, float], radius: float
    ) -> List[TrafficVehicle]:
        """Return all vehicles within radius of position."""
        result = []
        for v in self._vehicles.values():
            dx = v.position[0] - position[0]
            dy = v.position[1] - position[1]
            if (dx * dx + dy * dy) <= radius ** 2:
                result.append(v)
        return result

    def __repr__(self) -> str:
        return (
            f"TrafficSystem(vehicles={self.vehicle_count}, "
            f"lights={len(self._traffic_lights)})"
        )
