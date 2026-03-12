"""Physics engine - rigid-body dynamics and collision detection."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class Vector2:
    """2-D vector with common math operations."""

    x: float = 0.0
    y: float = 0.0

    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2":
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vector2":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector2":
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide vector by zero.")
        return Vector2(self.x / scalar, self.y / scalar)

    def magnitude(self) -> float:
        """Return the Euclidean length of the vector."""
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def normalized(self) -> "Vector2":
        """Return a unit vector in the same direction."""
        mag = self.magnitude()
        if mag == 0:
            return Vector2(0.0, 0.0)
        return Vector2(self.x / mag, self.y / mag)

    def dot(self, other: "Vector2") -> float:
        """Compute dot product with another vector."""
        return self.x * other.x + self.y * other.y

    def distance_to(self, other: "Vector2") -> float:
        """Return Euclidean distance to another vector."""
        return (self - other).magnitude()

    def copy(self) -> "Vector2":
        """Return a copy of this vector."""
        return Vector2(self.x, self.y)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return math.isclose(self.x, other.x) and math.isclose(self.y, other.y)

    def __repr__(self) -> str:
        return f"Vector2({self.x:.3f}, {self.y:.3f})"


@dataclass
class Vector3:
    """3-D vector with common math operations."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vector3":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector3":
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide vector by zero.")
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)

    def magnitude(self) -> float:
        """Return Euclidean length."""
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def normalized(self) -> "Vector3":
        """Return a unit vector."""
        mag = self.magnitude()
        if mag == 0:
            return Vector3(0.0, 0.0, 0.0)
        return Vector3(self.x / mag, self.y / mag, self.z / mag)

    def dot(self, other: "Vector3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vector3") -> "Vector3":
        """Compute cross product."""
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def distance_to(self, other: "Vector3") -> float:
        return (self - other).magnitude()

    def copy(self) -> "Vector3":
        return Vector3(self.x, self.y, self.z)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3):
            return NotImplemented
        return (
            math.isclose(self.x, other.x)
            and math.isclose(self.y, other.y)
            and math.isclose(self.z, other.z)
        )

    def __repr__(self) -> str:
        return f"Vector3({self.x:.3f}, {self.y:.3f}, {self.z:.3f})"


@dataclass
class AABB:
    """Axis-Aligned Bounding Box for collision detection."""

    min: Vector3 = field(default_factory=Vector3)
    max: Vector3 = field(default_factory=Vector3)

    def intersects(self, other: "AABB") -> bool:
        """Test AABB vs AABB intersection."""
        return (
            self.min.x <= other.max.x
            and self.max.x >= other.min.x
            and self.min.y <= other.max.y
            and self.max.y >= other.min.y
            and self.min.z <= other.max.z
            and self.max.z >= other.min.z
        )

    def contains_point(self, point: Vector3) -> bool:
        """Test whether a point is inside this AABB."""
        return (
            self.min.x <= point.x <= self.max.x
            and self.min.y <= point.y <= self.max.y
            and self.min.z <= point.z <= self.max.z
        )

    def center(self) -> Vector3:
        """Return the centre of this AABB."""
        return Vector3(
            (self.min.x + self.max.x) / 2,
            (self.min.y + self.max.y) / 2,
            (self.min.z + self.max.z) / 2,
        )


@dataclass
class RigidBody:
    """Rigid-body physics state for a physics entity."""

    position: Vector3 = field(default_factory=Vector3)
    velocity: Vector3 = field(default_factory=Vector3)
    acceleration: Vector3 = field(default_factory=Vector3)
    mass: float = 1.0
    drag: float = 0.98
    gravity_scale: float = 1.0
    is_static: bool = False
    on_ground: bool = False

    def apply_force(self, force: Vector3) -> None:
        """Apply a force to this body (F = ma)."""
        if self.is_static or self.mass == 0:
            return
        self.acceleration = self.acceleration + force * (1.0 / self.mass)

    def apply_impulse(self, impulse: Vector3) -> None:
        """Apply an instantaneous velocity change."""
        if self.is_static or self.mass == 0:
            return
        self.velocity = self.velocity + impulse * (1.0 / self.mass)

    def integrate(self, delta_time: float, gravity: Vector3) -> None:
        """Integrate physics state forward by delta_time."""
        if self.is_static:
            return
        total_accel = self.acceleration + gravity * self.gravity_scale
        self.velocity = self.velocity + total_accel * delta_time
        self.velocity = self.velocity * self.drag
        self.position = self.position + self.velocity * delta_time
        self.acceleration = Vector3()


CollisionCallback = Callable[["RigidBody", "RigidBody"], None]


class PhysicsEngine:
    """Simple physics engine with gravity and collision detection.

    Provides rigid-body dynamics, AABB collision, and a callback system
    for collision events.
    """

    GRAVITY = Vector3(0.0, -9.81, 0.0)

    def __init__(self) -> None:
        self._bodies: Dict[str, RigidBody] = {}
        self._collision_callbacks: List[CollisionCallback] = []
        self.gravity: Vector3 = Vector3(*self.GRAVITY.__dict__.values())

    def register_body(self, body_id: str, body: RigidBody) -> None:
        """Register a rigid body with a unique identifier."""
        self._bodies[body_id] = body

    def unregister_body(self, body_id: str) -> None:
        """Remove a rigid body from the simulation."""
        self._bodies.pop(body_id, None)

    def add_collision_callback(self, callback: CollisionCallback) -> None:
        """Register a callback invoked on each collision pair."""
        self._collision_callbacks.append(callback)

    def update(self, delta_time: float) -> None:
        """Step the physics simulation by delta_time seconds."""
        for body in self._bodies.values():
            body.integrate(delta_time, self.gravity)

        self._detect_collisions()

    def _detect_collisions(self) -> None:
        """Naive O(n²) broad-phase collision check for all registered bodies."""
        bodies = list(self._bodies.values())
        for i in range(len(bodies)):
            for j in range(i + 1, len(bodies)):
                a, b = bodies[i], bodies[j]
                if a.is_static and b.is_static:
                    continue
                if self._bodies_overlap(a, b):
                    for cb in self._collision_callbacks:
                        cb(a, b)

    def _bodies_overlap(self, a: RigidBody, b: RigidBody) -> bool:
        """Simple proximity check (distance-based)."""
        distance = a.position.distance_to(b.position)
        return distance < 1.0

    def raycast(
        self,
        origin: Vector3,
        direction: Vector3,
        max_distance: float = 100.0,
    ) -> Optional[Tuple[str, float]]:
        """Cast a ray and return the nearest hit body_id and distance.

        Args:
            origin: Ray start position.
            direction: Normalised ray direction.
            max_distance: Maximum ray travel distance.

        Returns:
            (body_id, distance) tuple for the nearest hit, or None if no hit.
        """
        dir_norm = direction.normalized()
        nearest: Optional[Tuple[str, float]] = None

        for body_id, body in self._bodies.items():
            if body.is_static:
                continue
            to_body = body.position - origin
            proj = to_body.dot(dir_norm)
            if proj < 0 or proj > max_distance:
                continue
            closest = origin + dir_norm * proj
            dist = closest.distance_to(body.position)
            if dist < 1.0:
                if nearest is None or proj < nearest[1]:
                    nearest = (body_id, proj)

        return nearest
