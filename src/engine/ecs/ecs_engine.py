"""Entity-Component-System (ECS) Engine.

The ECS architecture separates data (Components) from logic (Systems)
and identity (Entities), enabling scalable and modular game object design.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Set, Type, TypeVar

ComponentType = TypeVar("ComponentType", bound="Component")


class Component:
    """Base class for all ECS components.

    Components are pure data containers with no behaviour logic.
    """

    @classmethod
    def component_type(cls) -> str:
        return cls.__name__


@dataclass
class Entity:
    """An entity is a unique identifier with a set of components."""

    entity_id: int
    _components: Dict[str, Component] = field(default_factory=dict, repr=False)
    active: bool = True
    tags: Set[str] = field(default_factory=set)

    def add(self, component: Component) -> "Entity":
        """Attach a component to this entity."""
        self._components[component.component_type()] = component
        return self

    def remove(self, component_type: Type[ComponentType]) -> bool:
        """Remove a component by type.

        Returns:
            True if removed, False if not present.
        """
        key = component_type.__name__
        if key in self._components:
            del self._components[key]
            return True
        return False

    def get(self, component_type: Type[ComponentType]) -> Optional[ComponentType]:
        """Retrieve a component by type."""
        return self._components.get(component_type.__name__)  # type: ignore[return-value]

    def has(self, component_type: Type[ComponentType]) -> bool:
        return component_type.__name__ in self._components

    def has_all(self, *component_types: Type[Component]) -> bool:
        return all(ct.__name__ in self._components for ct in component_types)

    def add_tag(self, tag: str) -> None:
        self.tags.add(tag)

    def __repr__(self) -> str:
        comps = list(self._components.keys())
        return f"Entity(id={self.entity_id}, components={comps}, active={self.active})"


class System(ABC):
    """Base class for all ECS systems.

    Systems contain the game logic and operate on sets of entities
    that match their required components.
    """

    priority: int = 0  # Lower value = runs earlier

    @abstractmethod
    def update(self, world: "World", delta_time: float) -> None:
        """Process all relevant entities for this frame."""

    @property
    def required_components(self) -> List[Type[Component]]:
        """Return component types this system needs to query."""
        return []


class World:
    """The ECS world containing all entities and systems.

    The world manages entity lifecycle, system registration, and
    drives the per-frame update loop.
    """

    def __init__(self) -> None:
        self._entities: Dict[int, Entity] = {}
        self._systems: List[System] = []
        self._next_id: int = 1

    # ------------------------------------------------------------------ #
    # Entity lifecycle                                                     #
    # ------------------------------------------------------------------ #

    def create_entity(self, *components: Component) -> Entity:
        """Create a new entity and optionally attach initial components.

        Args:
            *components: Optional components to attach immediately.

        Returns:
            The newly created entity.
        """
        entity = Entity(entity_id=self._next_id)
        self._next_id += 1
        for component in components:
            entity.add(component)
        self._entities[entity.entity_id] = entity
        return entity

    def destroy_entity(self, entity_id: int) -> bool:
        """Remove an entity from the world.

        Returns:
            True if found and removed.
        """
        if entity_id in self._entities:
            del self._entities[entity_id]
            return True
        return False

    def get_entity(self, entity_id: int) -> Optional[Entity]:
        return self._entities.get(entity_id)

    # ------------------------------------------------------------------ #
    # Querying                                                             #
    # ------------------------------------------------------------------ #

    def query(self, *component_types: Type[Component]) -> Iterator[Entity]:
        """Yield all active entities that have all required component types."""
        for entity in self._entities.values():
            if entity.active and entity.has_all(*component_types):
                yield entity

    def query_with_tag(self, tag: str) -> Iterator[Entity]:
        """Yield all active entities with a specific tag."""
        for entity in self._entities.values():
            if entity.active and tag in entity.tags:
                yield entity

    # ------------------------------------------------------------------ #
    # System management                                                    #
    # ------------------------------------------------------------------ #

    def register_system(self, system: System) -> None:
        """Add a system to the update loop (sorted by priority)."""
        self._systems.append(system)
        self._systems.sort(key=lambda s: s.priority)

    def update(self, delta_time: float) -> None:
        """Run all registered systems in priority order."""
        for system in self._systems:
            system.update(self, delta_time)

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    @property
    def entity_count(self) -> int:
        return len(self._entities)

    @property
    def active_entity_count(self) -> int:
        return sum(1 for e in self._entities.values() if e.active)

    @property
    def system_count(self) -> int:
        return len(self._systems)

    def __repr__(self) -> str:
        return (
            f"World(entities={self.entity_count}, "
            f"active={self.active_entity_count}, "
            f"systems={self.system_count})"
        )
