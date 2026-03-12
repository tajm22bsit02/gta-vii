"""Character Controller - handles player movement and input."""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple

from engine.physics.physics_engine import Vector3


class MovementState(Enum):
    """Player movement states."""

    IDLE = auto()
    WALKING = auto()
    RUNNING = auto()
    SPRINTING = auto()
    CROUCHING = auto()
    PRONE = auto()
    JUMPING = auto()
    FALLING = auto()
    SWIMMING = auto()
    CLIMBING = auto()
    IN_VEHICLE = auto()


@dataclass
class CharacterStats:
    """Tunable character movement and physics stats."""

    walk_speed: float = 2.0        # m/s
    run_speed: float = 5.0
    sprint_speed: float = 9.0
    crouch_speed: float = 1.5
    jump_force: float = 5.0
    gravity: float = 9.81
    stamina: float = 100.0
    max_stamina: float = 100.0
    stamina_regen_rate: float = 10.0   # per second
    sprint_stamina_cost: float = 20.0  # per second


class CharacterController:
    """Manages player character position, movement, and state transitions.

    Accepts directional input each frame and produces updated position and
    heading, enforcing stamina limits and smooth animation state transitions.
    """

    def __init__(
        self,
        position: Optional[Vector3] = None,
        stats: Optional[CharacterStats] = None,
    ) -> None:
        self.position: Vector3 = position or Vector3()
        self.velocity: Vector3 = Vector3()
        self.heading: float = 0.0          # degrees, 0 = north (+Z)
        self.state: MovementState = MovementState.IDLE
        self.stats: CharacterStats = stats or CharacterStats()
        self._on_ground: bool = True
        self._vertical_velocity: float = 0.0
        self.is_in_cover: bool = False
        self.wanted_level: int = 0         # 0-5 stars

    # ------------------------------------------------------------------ #
    # Input-driven update                                                  #
    # ------------------------------------------------------------------ #

    def update(
        self,
        delta_time: float,
        move_input: Tuple[float, float] = (0.0, 0.0),
        sprint: bool = False,
        crouch: bool = False,
        jump: bool = False,
    ) -> None:
        """Update character state from input.

        Args:
            delta_time: Frame time in seconds.
            move_input: (dx, dz) normalised input direction (-1 to 1).
            sprint: Whether the sprint key is held.
            crouch: Whether the crouch key is held.
            jump: Whether jump was pressed this frame.
        """
        dx, dz = move_input
        moving = abs(dx) > 0.01 or abs(dz) > 0.01

        # Determine target speed / state
        if not moving:
            speed = 0.0
            self.state = MovementState.IDLE
        elif crouch:
            speed = self.stats.crouch_speed
            self.state = MovementState.CROUCHING
        elif sprint and self.stats.stamina > 0:
            speed = self.stats.sprint_speed
            self.state = MovementState.SPRINTING
            self.stats.stamina = max(
                0.0, self.stats.stamina - self.stats.sprint_stamina_cost * delta_time
            )
        else:
            speed = self.stats.run_speed
            self.state = MovementState.RUNNING

        # Update heading
        if moving:
            self.heading = math.degrees(math.atan2(dx, dz))

        # Apply horizontal movement
        if moving:
            mag = math.sqrt(dx * dx + dz * dz)
            if mag > 0:
                nx, nz = dx / mag, dz / mag
            else:
                nx, nz = 0.0, 0.0
            self.position.x += nx * speed * delta_time
            self.position.z += nz * speed * delta_time

        # Stamina regen when not sprinting
        if self.state != MovementState.SPRINTING:
            self.stats.stamina = min(
                self.stats.max_stamina,
                self.stats.stamina + self.stats.stamina_regen_rate * delta_time,
            )

        # Jumping / gravity
        if jump and self._on_ground:
            self._vertical_velocity = self.stats.jump_force
            self._on_ground = False
            self.state = MovementState.JUMPING

        if not self._on_ground:
            self._vertical_velocity -= self.stats.gravity * delta_time
            self.position.y += self._vertical_velocity * delta_time
            if self.position.y <= 0.0:
                self.position.y = 0.0
                self._vertical_velocity = 0.0
                self._on_ground = True
                self.state = MovementState.IDLE if not moving else MovementState.RUNNING

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    def teleport(self, new_position: Vector3) -> None:
        """Instantly move the character to a new position."""
        self.position = new_position

    def take_cover(self) -> None:
        """Place character in cover (reduces hit chance)."""
        self.is_in_cover = True
        self.state = MovementState.CROUCHING

    def leave_cover(self) -> None:
        """Leave cover position."""
        self.is_in_cover = False

    def enter_vehicle(self) -> None:
        """Transition to in-vehicle state."""
        self.state = MovementState.IN_VEHICLE

    def exit_vehicle(self) -> None:
        """Return to on-foot state."""
        self.state = MovementState.IDLE

    def add_wanted_level(self, amount: int = 1) -> None:
        """Increase wanted level (capped at 5)."""
        self.wanted_level = min(5, self.wanted_level + amount)

    def clear_wanted_level(self) -> None:
        """Remove all wanted stars."""
        self.wanted_level = 0

    def __repr__(self) -> str:
        return (
            f"CharacterController("
            f"pos={self.position}, "
            f"state={self.state.name}, "
            f"wanted={self.wanted_level})"
        )
