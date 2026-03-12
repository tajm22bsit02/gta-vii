"""Pedestrian AI - crowd simulation and pedestrian behaviour."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class PedestrianBehavior(Enum):
    """High-level behaviour states for a pedestrian."""

    IDLE = auto()
    WALKING = auto()
    RUNNING = auto()
    PANICKING = auto()
    SITTING = auto()
    SHOPPING = auto()
    TALKING = auto()


@dataclass
class Pedestrian:
    """A single NPC pedestrian."""

    ped_id: str
    position: Tuple[float, float]
    heading: float = 0.0
    speed: float = 0.0
    walk_speed: float = 1.4    # m/s (average human walking speed)
    run_speed: float = 5.0     # m/s
    behavior: PedestrianBehavior = PedestrianBehavior.IDLE
    destination: Optional[Tuple[float, float]] = None
    health: float = 100.0
    active: bool = True
    panic_timer: float = 0.0

    def update(self, delta_time: float) -> None:
        """Step the pedestrian's state machine."""
        if not self.active:
            return

        if self.behavior == PedestrianBehavior.PANICKING:
            self._update_panic(delta_time)
        elif self.destination is not None:
            self._move_towards_destination(delta_time)

    def _move_towards_destination(self, delta_time: float) -> None:
        """Walk or run towards the current destination."""
        if self.destination is None:
            return
        dx = self.destination[0] - self.position[0]
        dy = self.destination[1] - self.position[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 1.0:
            self.destination = None
            self.behavior = PedestrianBehavior.IDLE
            self.speed = 0.0
            return

        self.heading = math.degrees(math.atan2(dy, dx))
        move = self.speed * delta_time
        nx, ny = dx / dist, dy / dist
        self.position = (
            self.position[0] + nx * move,
            self.position[1] + ny * move,
        )

    def _update_panic(self, delta_time: float) -> None:
        """Run in a random direction while panicking."""
        self.panic_timer -= delta_time
        if self.panic_timer <= 0.0:
            self.behavior = PedestrianBehavior.WALKING
            self.speed = self.walk_speed
            return
        move = self.run_speed * delta_time
        rad = math.radians(self.heading)
        self.position = (
            self.position[0] + math.cos(rad) * move,
            self.position[1] + math.sin(rad) * move,
        )

    def trigger_panic(self, duration: float = 10.0) -> None:
        """Cause this pedestrian to flee in a random direction."""
        self.behavior = PedestrianBehavior.PANICKING
        self.speed = self.run_speed
        self.heading = random.uniform(0, 360)
        self.panic_timer = duration

    def set_destination(self, dest: Tuple[float, float]) -> None:
        """Set a walking destination."""
        self.destination = dest
        self.behavior = PedestrianBehavior.WALKING
        self.speed = self.walk_speed

    def __repr__(self) -> str:
        return (
            f"Pedestrian(id={self.ped_id}, "
            f"pos={self.position}, "
            f"behavior={self.behavior.name})"
        )


class PedestrianAI:
    """Manages the pedestrian crowd simulation.

    Handles spawning, despawning, and goal assignment for all active
    pedestrians around the player.
    """

    MAX_PEDESTRIANS: int = 150
    SPAWN_RADIUS: float = 200.0
    DESPAWN_RADIUS: float = 300.0
    SPAWN_INTERVAL: float = 2.0   # seconds between spawn attempts
    GOAL_REASSIGN_INTERVAL: float = 15.0  # seconds before picking new goal

    def __init__(self) -> None:
        self._pedestrians: Dict[str, Pedestrian] = {}
        self._spawn_timer: float = 0.0
        self._goal_timer: float = 0.0
        self._id_counter: int = 0

    def update(
        self,
        delta_time: float,
        player_position: Tuple[float, float],
    ) -> None:
        """Advance the pedestrian simulation.

        Args:
            delta_time: Seconds since the last tick.
            player_position: Player world position for spawn/despawn.
        """
        self._spawn_timer += delta_time
        self._goal_timer += delta_time

        for ped in self._pedestrians.values():
            ped.update(delta_time)

        if self._spawn_timer >= self.SPAWN_INTERVAL:
            self._spawn_timer = 0.0
            self._try_spawn(player_position)

        if self._goal_timer >= self.GOAL_REASSIGN_INTERVAL:
            self._goal_timer = 0.0
            self._reassign_goals(player_position)

        self._despawn_distant(player_position)

    # ------------------------------------------------------------------ #
    # Crowd reactions                                                      #
    # ------------------------------------------------------------------ #

    def trigger_mass_panic(
        self,
        source: Tuple[float, float],
        radius: float = 100.0,
    ) -> int:
        """Cause all pedestrians within radius to panic.

        Args:
            source: World position of the panic trigger.
            radius: Panic propagation radius.

        Returns:
            Number of pedestrians affected.
        """
        count = 0
        for ped in self._pedestrians.values():
            dx = ped.position[0] - source[0]
            dy = ped.position[1] - source[1]
            if (dx * dx + dy * dy) <= radius ** 2:
                ped.trigger_panic()
                count += 1
        return count

    # ------------------------------------------------------------------ #
    # Spawn / despawn helpers                                              #
    # ------------------------------------------------------------------ #

    def _try_spawn(self, centre: Tuple[float, float]) -> None:
        if len(self._pedestrians) >= self.MAX_PEDESTRIANS:
            return
        angle = random.uniform(0, 2 * math.pi)
        dist = random.uniform(self.SPAWN_RADIUS * 0.3, self.SPAWN_RADIUS)
        x = centre[0] + math.cos(angle) * dist
        y = centre[1] + math.sin(angle) * dist
        self._id_counter += 1
        ped = Pedestrian(ped_id=f"ped_{self._id_counter}", position=(x, y))
        self._pedestrians[ped.ped_id] = ped

    def _reassign_goals(self, centre: Tuple[float, float]) -> None:
        """Give idle pedestrians a new random destination."""
        for ped in self._pedestrians.values():
            if ped.behavior == PedestrianBehavior.IDLE:
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(20.0, 100.0)
                dest = (
                    ped.position[0] + math.cos(angle) * dist,
                    ped.position[1] + math.sin(angle) * dist,
                )
                ped.set_destination(dest)

    def _despawn_distant(self, player_position: Tuple[float, float]) -> None:
        to_remove = [
            pid
            for pid, ped in self._pedestrians.items()
            if math.hypot(
                ped.position[0] - player_position[0],
                ped.position[1] - player_position[1],
            )
            > self.DESPAWN_RADIUS
        ]
        for pid in to_remove:
            del self._pedestrians[pid]

    # ------------------------------------------------------------------ #
    # Accessors                                                            #
    # ------------------------------------------------------------------ #

    @property
    def pedestrian_count(self) -> int:
        return len(self._pedestrians)

    def get_pedestrians_near(
        self, position: Tuple[float, float], radius: float
    ) -> List[Pedestrian]:
        result = []
        for ped in self._pedestrians.values():
            if math.hypot(ped.position[0] - position[0], ped.position[1] - position[1]) <= radius:
                result.append(ped)
        return result

    def __repr__(self) -> str:
        return f"PedestrianAI(active={self.pedestrian_count})"
