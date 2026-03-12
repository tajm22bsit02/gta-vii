"""Health System - player health, armour, and damage management."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List, Optional


class DamageType(Enum):
    """Categories of damage sources."""

    BULLET = auto()
    EXPLOSION = auto()
    MELEE = auto()
    FIRE = auto()
    FALL = auto()
    DROWNING = auto()
    VEHICLE = auto()
    ENVIRONMENTAL = auto()


@dataclass
class DamageEvent:
    """Records a single damage instance."""

    damage_type: DamageType
    amount: float
    source_id: Optional[str] = None


DeathCallback = Callable[[], None]
DamageCallback = Callable[[DamageEvent], None]


class HealthSystem:
    """Manages player health, armour, and death events.

    Health regen kicks in after a configurable delay when the player
    is not under fire. Armour absorbs a percentage of incoming damage
    before health is reduced.
    """

    MAX_HEALTH: float = 100.0
    MAX_ARMOUR: float = 100.0
    REGEN_DELAY: float = 8.0        # seconds without damage before regen starts
    REGEN_RATE: float = 2.0         # HP per second
    ARMOUR_ABSORPTION: float = 0.5  # fraction of damage blocked by armour

    def __init__(
        self,
        health: float = 100.0,
        armour: float = 0.0,
    ) -> None:
        self._health: float = min(health, self.MAX_HEALTH)
        self._armour: float = min(armour, self.MAX_ARMOUR)
        self._regen_timer: float = 0.0
        self._alive: bool = True
        self._death_callbacks: List[DeathCallback] = []
        self._damage_callbacks: List[DamageCallback] = []
        self.damage_history: List[DamageEvent] = []

    # ------------------------------------------------------------------ #
    # Properties                                                           #
    # ------------------------------------------------------------------ #

    @property
    def health(self) -> float:
        return self._health

    @property
    def armour(self) -> float:
        return self._armour

    @property
    def is_alive(self) -> bool:
        return self._alive

    @property
    def health_percentage(self) -> float:
        return self._health / self.MAX_HEALTH

    @property
    def armour_percentage(self) -> float:
        return self._armour / self.MAX_ARMOUR

    # ------------------------------------------------------------------ #
    # Core methods                                                         #
    # ------------------------------------------------------------------ #

    def take_damage(self, event: DamageEvent) -> float:
        """Apply damage to the character.

        Armour absorbs a fraction of damage first; remaining damage
        reduces health. Returns the effective health damage dealt.

        Args:
            event: The damage event to apply.

        Returns:
            Effective health damage after armour absorption.
        """
        if not self._alive:
            return 0.0

        raw = event.amount
        health_dmg = raw

        if self._armour > 0:
            absorbed = min(self._armour, raw * self.ARMOUR_ABSORPTION)
            self._armour -= absorbed
            health_dmg = raw - absorbed

        self._health = max(0.0, self._health - health_dmg)
        self._regen_timer = 0.0
        self.damage_history.append(event)

        for cb in self._damage_callbacks:
            cb(event)

        if self._health <= 0.0:
            self._alive = False
            for cb in self._death_callbacks:
                cb()

        return health_dmg

    def heal(self, amount: float) -> None:
        """Restore health up to MAX_HEALTH."""
        if self._alive:
            self._health = min(self.MAX_HEALTH, self._health + amount)

    def add_armour(self, amount: float) -> None:
        """Add armour up to MAX_ARMOUR."""
        self._armour = min(self.MAX_ARMOUR, self._armour + amount)

    def respawn(self) -> None:
        """Respawn the character at full health and zero armour."""
        self._health = self.MAX_HEALTH
        self._armour = 0.0
        self._alive = True
        self._regen_timer = 0.0

    def update(self, delta_time: float) -> None:
        """Advance the health regen timer."""
        if not self._alive or self._health >= self.MAX_HEALTH:
            return
        self._regen_timer += delta_time
        if self._regen_timer >= self.REGEN_DELAY:
            self._health = min(
                self.MAX_HEALTH, self._health + self.REGEN_RATE * delta_time
            )

    # ------------------------------------------------------------------ #
    # Callbacks                                                            #
    # ------------------------------------------------------------------ #

    def on_death(self, callback: DeathCallback) -> None:
        """Register a callback invoked when health reaches zero."""
        self._death_callbacks.append(callback)

    def on_damage(self, callback: DamageCallback) -> None:
        """Register a callback invoked on every damage event."""
        self._damage_callbacks.append(callback)

    def __repr__(self) -> str:
        return (
            f"HealthSystem("
            f"hp={self._health:.1f}/{self.MAX_HEALTH}, "
            f"armour={self._armour:.1f}, "
            f"alive={self._alive})"
        )
