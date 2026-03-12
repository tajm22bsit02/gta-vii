"""Test suite for the physics engine."""

import pytest
import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.physics.physics_engine import (
    Vector2,
    Vector3,
    AABB,
    RigidBody,
    PhysicsEngine,
)


class TestVector2:
    def test_addition(self):
        v = Vector2(1.0, 2.0) + Vector2(3.0, 4.0)
        assert v.x == pytest.approx(4.0)
        assert v.y == pytest.approx(6.0)

    def test_subtraction(self):
        v = Vector2(5.0, 3.0) - Vector2(2.0, 1.0)
        assert v.x == pytest.approx(3.0)
        assert v.y == pytest.approx(2.0)

    def test_scalar_multiplication(self):
        v = Vector2(2.0, 4.0) * 3.0
        assert v.x == pytest.approx(6.0)
        assert v.y == pytest.approx(12.0)

    def test_division(self):
        v = Vector2(6.0, 8.0) / 2.0
        assert v.x == pytest.approx(3.0)
        assert v.y == pytest.approx(4.0)

    def test_division_by_zero(self):
        with pytest.raises(ZeroDivisionError):
            _ = Vector2(1.0, 2.0) / 0

    def test_magnitude(self):
        assert Vector2(3.0, 4.0).magnitude() == pytest.approx(5.0)

    def test_normalise_zero_vector(self):
        v = Vector2(0.0, 0.0).normalized()
        assert v.x == 0.0
        assert v.y == 0.0

    def test_dot(self):
        assert Vector2(1.0, 0.0).dot(Vector2(0.0, 1.0)) == pytest.approx(0.0)
        assert Vector2(1.0, 0.0).dot(Vector2(1.0, 0.0)) == pytest.approx(1.0)

    def test_distance_to(self):
        a = Vector2(0.0, 0.0)
        b = Vector2(3.0, 4.0)
        assert a.distance_to(b) == pytest.approx(5.0)


class TestVector3:
    def test_addition(self):
        v = Vector3(1, 2, 3) + Vector3(4, 5, 6)
        assert v == Vector3(5, 7, 9)

    def test_cross_product(self):
        i = Vector3(1, 0, 0)
        j = Vector3(0, 1, 0)
        k = i.cross(j)
        assert k == Vector3(0, 0, 1)

    def test_magnitude(self):
        assert Vector3(1, 2, 2).magnitude() == pytest.approx(3.0)

    def test_normalise(self):
        v = Vector3(3, 0, 4).normalized()
        assert v.magnitude() == pytest.approx(1.0)


class TestAABB:
    def test_intersection(self):
        a = AABB(Vector3(0, 0, 0), Vector3(2, 2, 2))
        b = AABB(Vector3(1, 1, 1), Vector3(3, 3, 3))
        assert a.intersects(b)

    def test_no_intersection(self):
        a = AABB(Vector3(0, 0, 0), Vector3(1, 1, 1))
        b = AABB(Vector3(5, 5, 5), Vector3(6, 6, 6))
        assert not a.intersects(b)

    def test_contains_point(self):
        aabb = AABB(Vector3(0, 0, 0), Vector3(10, 10, 10))
        assert aabb.contains_point(Vector3(5, 5, 5))
        assert not aabb.contains_point(Vector3(15, 5, 5))

    def test_center(self):
        aabb = AABB(Vector3(0, 0, 0), Vector3(4, 4, 4))
        c = aabb.center()
        assert c == Vector3(2, 2, 2)


class TestRigidBody:
    def test_apply_force_changes_acceleration(self):
        body = RigidBody(mass=2.0)
        body.apply_force(Vector3(4.0, 0.0, 0.0))
        assert body.acceleration.x == pytest.approx(2.0)

    def test_static_body_ignores_force(self):
        body = RigidBody(is_static=True)
        body.apply_force(Vector3(100.0, 0.0, 0.0))
        assert body.acceleration.x == pytest.approx(0.0)

    def test_integrate_moves_body(self):
        body = RigidBody(gravity_scale=0.0)
        body.velocity = Vector3(10.0, 0.0, 0.0)
        body.integrate(1.0, Vector3(0, 0, 0))
        assert body.position.x > 0.0

    def test_impulse_changes_velocity(self):
        body = RigidBody(mass=1.0)
        body.apply_impulse(Vector3(5.0, 0.0, 0.0))
        assert body.velocity.x == pytest.approx(5.0)


class TestPhysicsEngine:
    def test_register_and_update(self):
        engine = PhysicsEngine()
        body = RigidBody(gravity_scale=0.0, drag=1.0)
        engine.register_body("ball", body)
        engine.update(0.016)
        assert engine._bodies["ball"] is body

    def test_collision_callback(self):
        collisions = []
        engine = PhysicsEngine()
        # At least one body must be dynamic (not static) for collision to be detected
        a = RigidBody(position=Vector3(0, 0, 0), gravity_scale=0.0, is_static=False)
        b = RigidBody(position=Vector3(0.5, 0, 0), gravity_scale=0.0, is_static=True)
        engine.register_body("a", a)
        engine.register_body("b", b)
        engine.add_collision_callback(lambda x, y: collisions.append((x, y)))
        engine.update(0.016)
        assert len(collisions) >= 1

    def test_raycast_no_hit(self):
        engine = PhysicsEngine()
        result = engine.raycast(Vector3(0, 0, 0), Vector3(0, 0, 1))
        assert result is None

    def test_unregister_body(self):
        engine = PhysicsEngine()
        engine.register_body("x", RigidBody())
        engine.unregister_body("x")
        assert "x" not in engine._bodies
