"""Enemy AI - finite-state machine driven combat AI."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class EnemyCombatState(Enum):
    """Enemy AI states in the FSM."""

    IDLE = auto()
    PATROL = auto()
    ALERT = auto()
    ENGAGE = auto()
    TAKE_COVER = auto()
    FLANKING = auto()
    RETREATING = auto()
    DEAD = auto()


@dataclass
class PatrolPoint:
    """A waypoint on an enemy patrol route."""

    position: Tuple[float, float]
    wait_time: float = 2.0


@dataclass
class Enemy:
    """A single combat-capable NPC."""

    enemy_id: str
    position: Tuple[float, float]
    health: float = 100.0
    max_health: float = 100.0
    detection_range: float = 30.0
    attack_range: float = 20.0
    move_speed: float = 3.0
    heading: float = 0.0
    state: EnemyCombatState = EnemyCombatState.IDLE
    patrol_route: List[PatrolPoint] = field(default_factory=list)
    _patrol_index: int = field(default=0, init=False, repr=False)
    _state_timer: float = field(default=0.0, init=False, repr=False)
    _last_known_player_pos: Optional[Tuple[float, float]] = field(
        default=None, init=False, repr=False
    )
    _shoot_cooldown: float = field(default=0.0, init=False, repr=False)

    @property
    def is_alive(self) -> bool:
        return self.health > 0.0

    def take_damage(self, amount: float) -> None:
        self.health = max(0.0, self.health - amount)
        if not self.is_alive:
            self.state = EnemyCombatState.DEAD

    @property
    def health_percentage(self) -> float:
        return self.health / self.max_health


class EnemyAI:
    """Manages all enemies and their AI state machines.

    Uses an FSM per enemy to handle patrol, detection, engagement,
    cover-seeking, and death.
    """

    ALERT_DURATION: float = 5.0
    SHOOT_INTERVAL: float = 1.5
    LOW_HEALTH_THRESHOLD: float = 0.3

    def __init__(self) -> None:
        self._enemies: Dict[str, Enemy] = {}

    def add_enemy(self, enemy: Enemy) -> None:
        self._enemies[enemy.enemy_id] = enemy

    def remove_enemy(self, enemy_id: str) -> None:
        self._enemies.pop(enemy_id, None)

    def update(
        self,
        delta_time: float,
        player_position: Tuple[float, float],
        player_visible: bool = True,
    ) -> List[Tuple[str, float]]:
        """Update all enemy AI states.

        Args:
            delta_time: Frame time in seconds.
            player_position: Current player world position.
            player_visible: Whether the player is visible (not in cover etc.)

        Returns:
            List of (enemy_id, damage) tuples for shots that hit the player.
        """
        hits: List[Tuple[str, float]] = []

        for enemy in list(self._enemies.values()):
            if not enemy.is_alive:
                enemy.state = EnemyCombatState.DEAD
                continue

            dist = math.hypot(
                player_position[0] - enemy.position[0],
                player_position[1] - enemy.position[1],
            )

            self._run_fsm(enemy, delta_time, player_position, dist, player_visible)

            # Shooting logic
            if enemy.state == EnemyCombatState.ENGAGE and dist <= enemy.attack_range:
                enemy._shoot_cooldown -= delta_time
                if enemy._shoot_cooldown <= 0.0 and player_visible:
                    enemy._shoot_cooldown = self.SHOOT_INTERVAL
                    if random.random() < 0.4:  # 40% hit chance
                        hits.append((enemy.enemy_id, 15.0))

        return hits

    def _run_fsm(
        self,
        enemy: Enemy,
        delta_time: float,
        player_pos: Tuple[float, float],
        dist: float,
        player_visible: bool,
    ) -> None:
        """Execute one FSM tick for the given enemy."""
        if enemy.state == EnemyCombatState.IDLE:
            if enemy.patrol_route:
                enemy.state = EnemyCombatState.PATROL
            if dist <= enemy.detection_range and player_visible:
                enemy.state = EnemyCombatState.ALERT
                enemy._state_timer = self.ALERT_DURATION
                enemy._last_known_player_pos = player_pos

        elif enemy.state == EnemyCombatState.PATROL:
            self._patrol_step(enemy, delta_time)
            if dist <= enemy.detection_range and player_visible:
                enemy.state = EnemyCombatState.ALERT
                enemy._state_timer = self.ALERT_DURATION
                enemy._last_known_player_pos = player_pos

        elif enemy.state == EnemyCombatState.ALERT:
            enemy._state_timer -= delta_time
            if dist <= enemy.detection_range and player_visible:
                enemy.state = EnemyCombatState.ENGAGE
                enemy._last_known_player_pos = player_pos
            elif enemy._state_timer <= 0.0:
                enemy.state = EnemyCombatState.PATROL

        elif enemy.state == EnemyCombatState.ENGAGE:
            enemy._last_known_player_pos = player_pos
            if enemy.health_percentage < self.LOW_HEALTH_THRESHOLD:
                enemy.state = EnemyCombatState.TAKE_COVER
            elif dist > enemy.detection_range * 1.5:
                enemy.state = EnemyCombatState.ALERT
                enemy._state_timer = self.ALERT_DURATION
            else:
                self._move_towards(enemy, player_pos, delta_time, stop_dist=enemy.attack_range * 0.7)

        elif enemy.state == EnemyCombatState.TAKE_COVER:
            self._seek_cover(enemy, player_pos, delta_time)
            if dist <= enemy.attack_range:
                enemy.state = EnemyCombatState.ENGAGE

        elif enemy.state == EnemyCombatState.RETREATING:
            self._move_away(enemy, player_pos, delta_time)

    def _patrol_step(self, enemy: Enemy, delta_time: float) -> None:
        if not enemy.patrol_route:
            return
        target = enemy.patrol_route[enemy._patrol_index].position
        dist = math.hypot(target[0] - enemy.position[0], target[1] - enemy.position[1])
        if dist < 1.0:
            enemy._patrol_index = (enemy._patrol_index + 1) % len(enemy.patrol_route)
        else:
            self._move_towards(enemy, target, delta_time)

    def _move_towards(
        self,
        enemy: Enemy,
        target: Tuple[float, float],
        delta_time: float,
        stop_dist: float = 0.5,
    ) -> None:
        dx = target[0] - enemy.position[0]
        dy = target[1] - enemy.position[1]
        dist = math.sqrt(dx * dx + dy * dy)
        if dist <= stop_dist:
            return
        nx, ny = dx / dist, dy / dist
        move = enemy.move_speed * delta_time
        enemy.position = (enemy.position[0] + nx * move, enemy.position[1] + ny * move)
        enemy.heading = math.degrees(math.atan2(dx, dy))

    def _move_away(
        self,
        enemy: Enemy,
        threat: Tuple[float, float],
        delta_time: float,
    ) -> None:
        dx = enemy.position[0] - threat[0]
        dy = enemy.position[1] - threat[1]
        dist = math.sqrt(dx * dx + dy * dy) or 1.0
        nx, ny = dx / dist, dy / dist
        move = enemy.move_speed * delta_time
        enemy.position = (enemy.position[0] + nx * move, enemy.position[1] + ny * move)

    def _seek_cover(
        self,
        enemy: Enemy,
        threat: Tuple[float, float],
        delta_time: float,
    ) -> None:
        """Move perpendicular to the threat direction to simulate flanking."""
        dx = threat[0] - enemy.position[0]
        dy = threat[1] - enemy.position[1]
        dist = math.sqrt(dx * dx + dy * dy) or 1.0
        perp_x, perp_y = -dy / dist, dx / dist
        move = enemy.move_speed * delta_time
        enemy.position = (
            enemy.position[0] + perp_x * move,
            enemy.position[1] + perp_y * move,
        )

    # ------------------------------------------------------------------ #
    # Accessors                                                            #
    # ------------------------------------------------------------------ #

    @property
    def alive_count(self) -> int:
        return sum(1 for e in self._enemies.values() if e.is_alive)

    @property
    def dead_count(self) -> int:
        return sum(1 for e in self._enemies.values() if not e.is_alive)

    def get_enemies_near(
        self, position: Tuple[float, float], radius: float
    ) -> List[Enemy]:
        return [
            e for e in self._enemies.values()
            if e.is_alive
            and math.hypot(e.position[0] - position[0], e.position[1] - position[1]) <= radius
        ]

    def __repr__(self) -> str:
        return f"EnemyAI(alive={self.alive_count}, dead={self.dead_count})"
