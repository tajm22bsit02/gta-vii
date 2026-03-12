"""Base Component class for the Entity-Component-System architecture."""

from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .entity import Entity


class Component:
    """Base class for all ECS components.

    Components hold only data, no logic. Systems operate on components.
    """

    def __init__(self) -> None:
        self._entity: Optional["Entity"] = None
        self.enabled: bool = True

    @property
    def entity(self) -> Optional["Entity"]:
        """Return the owning entity."""
        return self._entity

    @entity.setter
    def entity(self, value: Optional["Entity"]) -> None:
        """Set the owning entity."""
        self._entity = value

    def __repr__(self) -> str:
        entity_name = self._entity.name if self._entity else "None"
        return f"{type(self).__name__}(entity={entity_name!r})"
