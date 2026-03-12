"""Entity class for the Entity-Component-System architecture."""

from __future__ import annotations
import uuid
from typing import TYPE_CHECKING, Dict, Optional, Type, TypeVar

if TYPE_CHECKING:
    from .component import Component

T = TypeVar("T", bound="Component")


class Entity:
    """Represents a game object in the ECS architecture.

    Entities are lightweight containers that hold components.
    They are identified by a unique ID and can be enabled/disabled.
    """

    def __init__(self, name: str = "") -> None:
        self._id: str = str(uuid.uuid4())
        self.name: str = name or f"Entity_{self._id[:8]}"
        self._components: Dict[type, "Component"] = {}
        self.active: bool = True
        self.tags: set = set()

    @property
    def id(self) -> str:
        """Return the unique entity ID."""
        return self._id

    def add_component(self, component: "Component") -> "Entity":
        """Add a component to this entity.

        Args:
            component: The component instance to add.

        Returns:
            Self for method chaining.
        """
        component_type = type(component)
        self._components[component_type] = component
        component.entity = self
        return self

    def remove_component(self, component_type: Type[T]) -> Optional[T]:
        """Remove a component by type.

        Args:
            component_type: The type of component to remove.

        Returns:
            The removed component, or None if not found.
        """
        component = self._components.pop(component_type, None)
        if component is not None:
            component.entity = None
        return component

    def get_component(self, component_type: Type[T]) -> Optional[T]:
        """Get a component by type.

        Args:
            component_type: The type of component to retrieve.

        Returns:
            The component instance, or None if not found.
        """
        return self._components.get(component_type)

    def has_component(self, component_type: type) -> bool:
        """Check if the entity has a specific component type.

        Args:
            component_type: The component type to check for.

        Returns:
            True if the component exists, False otherwise.
        """
        return component_type in self._components

    def add_tag(self, tag: str) -> "Entity":
        """Add a tag to this entity."""
        self.tags.add(tag)
        return self

    def has_tag(self, tag: str) -> bool:
        """Check if entity has a specific tag."""
        return tag in self.tags

    def destroy(self) -> None:
        """Mark this entity as inactive for removal."""
        self.active = False

    def __repr__(self) -> str:
        return f"Entity(id={self._id[:8]}, name={self.name!r}, active={self.active})"
