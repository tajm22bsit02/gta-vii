"""Test suite for the ECS engine."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.ecs.ecs_engine import World, Entity, Component, System
from engine.ecs.world import ECSWorld
from engine.ecs.entity import Entity as LegacyEntity
from engine.ecs.component import Component as LegacyComponent


# ------------------------------------------------------------------ #
# Test Components                                                     #
# ------------------------------------------------------------------ #

class PositionComponent(Component):
    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = x
        self.y = y


class VelocityComponent(Component):
    def __init__(self, vx: float = 0.0, vy: float = 0.0):
        self.vx = vx
        self.vy = vy


class HealthComponent(Component):
    def __init__(self, hp: int = 100):
        self.hp = hp


# ------------------------------------------------------------------ #
# Tests: Entity                                                       #
# ------------------------------------------------------------------ #

class TestEntity:
    def test_create_entity_has_unique_id(self):
        world = World()
        e1 = world.create_entity()
        e2 = world.create_entity()
        assert e1.entity_id != e2.entity_id

    def test_add_and_get_component(self):
        world = World()
        e = world.create_entity()
        pos = PositionComponent(5.0, 10.0)
        e.add(pos)
        retrieved = e.get(PositionComponent)
        assert retrieved is pos
        assert retrieved.x == 5.0

    def test_has_component(self):
        world = World()
        e = world.create_entity()
        assert not e.has(PositionComponent)
        e.add(PositionComponent())
        assert e.has(PositionComponent)

    def test_remove_component(self):
        world = World()
        e = world.create_entity()
        e.add(PositionComponent())
        assert e.has(PositionComponent)
        e.remove(PositionComponent)
        assert not e.has(PositionComponent)

    def test_remove_absent_component_returns_false(self):
        world = World()
        e = world.create_entity()
        result = e.remove(PositionComponent)
        assert result is False

    def test_has_all_components(self):
        world = World()
        e = world.create_entity()
        e.add(PositionComponent())
        e.add(VelocityComponent())
        assert e.has_all(PositionComponent, VelocityComponent)
        assert not e.has_all(PositionComponent, HealthComponent)

    def test_tags(self):
        world = World()
        e = world.create_entity()
        e.add_tag("player")
        assert "player" in e.tags


# ------------------------------------------------------------------ #
# Tests: World                                                        #
# ------------------------------------------------------------------ #

class TestWorld:
    def test_entity_count(self):
        world = World()
        assert world.entity_count == 0
        world.create_entity()
        world.create_entity()
        assert world.entity_count == 2

    def test_destroy_entity(self):
        world = World()
        e = world.create_entity()
        assert world.entity_count == 1
        world.destroy_entity(e.entity_id)
        assert world.entity_count == 0

    def test_destroy_nonexistent_entity(self):
        world = World()
        result = world.destroy_entity(9999)
        assert result is False

    def test_query_by_component(self):
        world = World()
        e1 = world.create_entity()
        e1.add(PositionComponent())
        e2 = world.create_entity()
        e2.add(PositionComponent())
        e2.add(VelocityComponent())
        e3 = world.create_entity()  # no components

        results = list(world.query(PositionComponent))
        assert len(results) == 2

    def test_query_multiple_components(self):
        world = World()
        e1 = world.create_entity()
        e1.add(PositionComponent())
        e1.add(VelocityComponent())
        e2 = world.create_entity()
        e2.add(PositionComponent())

        results = list(world.query(PositionComponent, VelocityComponent))
        assert len(results) == 1
        assert results[0] is e1

    def test_query_with_tag(self):
        world = World()
        e1 = world.create_entity()
        e1.add_tag("enemy")
        e2 = world.create_entity()
        e2.add_tag("player")

        enemies = list(world.query_with_tag("enemy"))
        assert len(enemies) == 1

    def test_create_entity_with_components(self):
        world = World()
        e = world.create_entity(PositionComponent(1.0, 2.0), VelocityComponent(0.5, 0.5))
        assert e.has(PositionComponent)
        assert e.has(VelocityComponent)

    def test_system_update_called(self):
        update_count = {"n": 0}

        class CountSystem(System):
            def update(self, w: World, dt: float) -> None:
                update_count["n"] += 1

        world = World()
        world.register_system(CountSystem())
        world.update(0.016)
        world.update(0.016)
        assert update_count["n"] == 2

    def test_systems_sorted_by_priority(self):
        order = []

        class SystemA(System):
            priority = 10
            def update(self, w, dt):
                order.append("A")

        class SystemB(System):
            priority = 1
            def update(self, w, dt):
                order.append("B")

        world = World()
        world.register_system(SystemA())
        world.register_system(SystemB())
        world.update(0.016)
        assert order == ["B", "A"]

    def test_inactive_entity_not_in_query(self):
        world = World()
        e = world.create_entity(PositionComponent())
        e.active = False
        results = list(world.query(PositionComponent))
        assert len(results) == 0
