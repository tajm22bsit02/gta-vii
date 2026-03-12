"""Cover System - third-person cover mechanics."""

from __future__ import annotations
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class CoverType(Enum):
    """Height and protection level of cover."""

    FULL = auto()    # Standing cover (wall, car body)
    HALF = auto()    # Crouching cover (low wall, crate)
    PARTIAL = auto() # Thin cover (pole, slim pillar)


@dataclass
class CoverPoint:
    """A static cover position in the world."""

    cover_id: str
    position: Tuple[float, float]
    cover_type: CoverType
    facing: float = 0.0          # degrees – direction the cover faces outward
    max_occupants: int = 1
    _occupants: int = 0

    @property
    def is_available(self) -> bool:
        return self._occupants < self.max_occupants

    @property
    def protection_factor(self) -> float:
        """Fraction of incoming damage blocked (0.0-1.0)."""
        return {
            CoverType.FULL: 0.85,
            CoverType.HALF: 0.60,
            CoverType.PARTIAL: 0.30,
        }[self.cover_type]

    def occupy(self) -> bool:
        """Attempt to occupy this cover point.

        Returns:
            True if successfully occupied.
        """
        if not self.is_available:
            return False
        self._occupants += 1
        return True

    def vacate(self) -> None:
        """Release this cover point."""
        self._occupants = max(0, self._occupants - 1)

    def peek_position(self, offset: float = 0.5) -> Tuple[float, float]:
        """Return the world position for peeking/shooting from this cover."""
        rad = math.radians(self.facing)
        return (
            self.position[0] + math.sin(rad) * offset,
            self.position[1] + math.cos(rad) * offset,
        )


class CoverSystem:
    """Manages world cover points and player/enemy cover state.

    Provides nearest cover lookup, cover transitions, and damage
    reduction calculations.
    """

    def __init__(self) -> None:
        self._cover_points: Dict[str, CoverPoint] = {}
        self._player_cover: Optional[CoverPoint] = None

    def register_cover(self, cover: CoverPoint) -> None:
        """Add a cover point to the world."""
        self._cover_points[cover.cover_id] = cover

    def find_nearest_cover(
        self,
        position: Tuple[float, float],
        max_distance: float = 20.0,
        facing_threat: Optional[Tuple[float, float]] = None,
    ) -> Optional[CoverPoint]:
        """Find the nearest available cover point.

        Args:
            position: Seeker's current world position.
            max_distance: Maximum search radius.
            facing_threat: If given, prefer cover that faces the threat.

        Returns:
            Best available cover point, or None.
        """
        candidates = []
        for cp in self._cover_points.values():
            if not cp.is_available:
                continue
            dist = math.hypot(cp.position[0] - position[0], cp.position[1] - position[1])
            if dist > max_distance:
                continue
            score = dist
            if facing_threat:
                dx = facing_threat[0] - cp.position[0]
                dy = facing_threat[1] - cp.position[1]
                threat_angle = math.degrees(math.atan2(dx, dy)) % 360
                angle_diff = abs((cp.facing - threat_angle + 180) % 360 - 180)
                score += angle_diff * 0.1
            candidates.append((score, cp))

        if not candidates:
            return None
        return min(candidates, key=lambda x: x[0])[1]

    def take_cover(self, cover_point: CoverPoint) -> bool:
        """Attempt to take cover at a specific point."""
        if not cover_point.occupy():
            return False
        if self._player_cover:
            self._player_cover.vacate()
        self._player_cover = cover_point
        return True

    def leave_cover(self) -> None:
        """Release the player's current cover."""
        if self._player_cover:
            self._player_cover.vacate()
            self._player_cover = None

    def calculate_damage_taken(
        self, raw_damage: float, in_cover: bool = False
    ) -> float:
        """Return effective damage after applying cover protection.

        Args:
            raw_damage: Full damage before cover reduction.
            in_cover: Whether the target is actively in cover.

        Returns:
            Effective damage to apply.
        """
        if not in_cover or self._player_cover is None:
            return raw_damage
        protection = self._player_cover.protection_factor
        return raw_damage * (1.0 - protection)

    @property
    def player_in_cover(self) -> bool:
        return self._player_cover is not None

    @property
    def available_cover_count(self) -> int:
        return sum(1 for cp in self._cover_points.values() if cp.is_available)

    # ------------------------------------------------------------------ #
    # World generation helpers                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def generate_urban_cover(
        centre: Tuple[float, float],
        count: int = 20,
        radius: float = 50.0,
    ) -> List[CoverPoint]:
        """Generate cover points for an urban combat zone."""
        import random
        cover_points = []
        for i in range(count):
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(5.0, radius)
            x = centre[0] + math.cos(angle) * dist
            y = centre[1] + math.sin(angle) * dist
            cover_type = random.choices(
                list(CoverType),
                weights=[40, 45, 15],
                k=1,
            )[0]
            cp = CoverPoint(
                cover_id=f"cover_{i}",
                position=(x, y),
                cover_type=cover_type,
                facing=math.degrees(angle + math.pi) % 360,
            )
            cover_points.append(cp)
        return cover_points

    def __repr__(self) -> str:
        total = len(self._cover_points)
        avail = self.available_cover_count
        return (
            f"CoverSystem(total={total}, available={avail}, "
            f"player_in_cover={self.player_in_cover})"
        )
