"""Base System class for the Entity-Component-System architecture."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .world import ECSWorld


class System(ABC):
    """Base class for all ECS systems.

    Systems contain the game logic and operate on entities with
    specific component combinations.
    """

    def __init__(self) -> None:
        self._world: "ECSWorld | None" = None
        self.priority: int = 0
        self.enabled: bool = True

    @property
    def world(self) -> "ECSWorld | None":
        """Return the ECS world this system belongs to."""
        return self._world

    @world.setter
    def world(self, value: "ECSWorld | None") -> None:
        """Set the owning ECS world."""
        self._world = value

    def initialize(self) -> None:
        """Called once when the system is added to the world."""

    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Update the system each game tick.

        Args:
            delta_time: Time elapsed since last update in seconds.
        """

    def shutdown(self) -> None:
        """Called when the system is removed from the world."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(priority={self.priority}, enabled={self.enabled})"
