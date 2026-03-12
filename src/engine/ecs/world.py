"""ECS World - manages all entities and systems."""

from __future__ import annotations
from typing import Dict, Iterable, List, Optional, Set, Type, TypeVar

from .entity import Entity
from .component import Component
from .system import System

T = TypeVar("T", bound=Component)
S = TypeVar("S", bound=System)


class ECSWorld:
    """The ECS World manages all entities and systems.

    It serves as the central coordinator for the game's ECS architecture,
    providing entity lifecycle management, component queries, and
    ordered system execution.
    """

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}
        self._systems: List[System] = []
        self._pending_destroy: Set[str] = set()

    # ------------------------------------------------------------------ #
    # Entity management                                                    #
    # ------------------------------------------------------------------ #

    def create_entity(self, name: str = "") -> Entity:
        """Create and register a new entity.

        Args:
            name: Optional display name for the entity.

        Returns:
            The newly created entity.
        """
        entity = Entity(name)
        self._entities[entity.id] = entity
        return entity

    def destroy_entity(self, entity: Entity) -> None:
        """Schedule an entity for removal at the end of the current tick."""
        self._pending_destroy.add(entity.id)
        entity.destroy()

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve an entity by ID.

        Args:
            entity_id: The unique entity identifier.

        Returns:
            The entity, or None if not found.
        """
        return self._entities.get(entity_id)

    def get_entities_with_components(
        self, *component_types: type
    ) -> Iterable[Entity]:
        """Yield all active entities that have *all* of the given component types.

        Args:
            *component_types: One or more component types to filter by.

        Yields:
            Entities that possess every requested component type.
        """
        for entity in list(self._entities.values()):
            if not entity.active:
                continue
            if all(entity.has_component(ct) for ct in component_types):
                yield entity

    def get_entities_by_tag(self, tag: str) -> Iterable[Entity]:
        """Yield all active entities that have the given tag."""
        for entity in list(self._entities.values()):
            if entity.active and entity.has_tag(tag):
                yield entity

    @property
    def entity_count(self) -> int:
        """Return the current number of registered entities."""
        return len(self._entities)

    # ------------------------------------------------------------------ #
    # System management                                                    #
    # ------------------------------------------------------------------ #

    def add_system(self, system: System) -> "ECSWorld":
        """Register a system and sort by priority.

        Args:
            system: The system instance to add.

        Returns:
            Self for method chaining.
        """
        system.world = self
        system.initialize()
        self._systems.append(system)
        self._systems.sort(key=lambda s: s.priority)
        return self

    def remove_system(self, system_type: Type[S]) -> Optional[S]:
        """Remove a system by type.

        Args:
            system_type: The type of system to remove.

        Returns:
            The removed system, or None if not found.
        """
        for i, system in enumerate(self._systems):
            if isinstance(system, system_type):
                system.shutdown()
                system.world = None
                return self._systems.pop(i)
        return None

    def get_system(self, system_type: Type[S]) -> Optional[S]:
        """Retrieve a system by type."""
        for system in self._systems:
            if isinstance(system, system_type):
                return system  # type: ignore[return-value]
        return None

    # ------------------------------------------------------------------ #
    # Main update loop                                                     #
    # ------------------------------------------------------------------ #

    def update(self, delta_time: float) -> None:
        """Update all enabled systems and flush destroyed entities.

        Args:
            delta_time: Time elapsed since the last update in seconds.
        """
        for system in self._systems:
            if system.enabled:
                system.update(delta_time)

        self._flush_destroyed()

    def _flush_destroyed(self) -> None:
        """Remove all entities that were scheduled for destruction."""
        for entity_id in self._pending_destroy:
            self._entities.pop(entity_id, None)
        self._pending_destroy.clear()

    def clear(self) -> None:
        """Remove all entities and shut down all systems."""
        for system in self._systems:
            system.shutdown()
        self._systems.clear()
        self._entities.clear()
        self._pending_destroy.clear()

    def __repr__(self) -> str:
        return (
            f"ECSWorld(entities={len(self._entities)}, "
            f"systems={len(self._systems)})"
        )
