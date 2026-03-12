"""Culling System - frustum and occlusion culling."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class BoundingSphere:
    """Sphere representation for culling tests."""

    centre: Tuple[float, float, float]
    radius: float


@dataclass
class FrustumPlane:
    """A single half-space of the view frustum."""

    normal: Tuple[float, float, float]
    distance: float

    def signed_distance(self, point: Tuple[float, float, float]) -> float:
        nx, ny, nz = self.normal
        return nx * point[0] + ny * point[1] + nz * point[2] + self.distance


@dataclass
class CullableObject:
    """An object that can be frustum-culled."""

    object_id: str
    bounds: BoundingSphere
    is_visible: bool = True


class FrustumCuller:
    """Tests bounding spheres against a simple view frustum.

    The frustum is approximated from camera position, forward vector,
    FOV, and near/far clip planes.
    """

    def __init__(
        self,
        fov_degrees: float = 90.0,
        aspect_ratio: float = 16.0 / 9.0,
        near: float = 0.1,
        far: float = 2000.0,
    ) -> None:
        self.fov_degrees = fov_degrees
        self.aspect_ratio = aspect_ratio
        self.near = near
        self.far = far
        self._planes: List[FrustumPlane] = []

    def update_frustum(
        self,
        camera_pos: Tuple[float, float, float],
        forward: Tuple[float, float, float],
    ) -> None:
        """Recompute frustum planes from the current camera state."""
        fx, fy, fz = forward
        world_up = (0.0, 1.0, 0.0)
        rx = fy * world_up[2] - fz * world_up[1]
        ry = fz * world_up[0] - fx * world_up[2]
        rz = fx * world_up[1] - fy * world_up[0]
        r_len = math.sqrt(rx * rx + ry * ry + rz * rz) or 1.0
        right = (rx / r_len, ry / r_len, rz / r_len)

        half_fov_h = math.atan(math.tan(math.radians(self.fov_degrees / 2)) * self.aspect_ratio)
        sin_h = math.sin(half_fov_h)
        cos_h = math.cos(half_fov_h)

        self._planes = [
            FrustumPlane(forward, -(forward[0]*camera_pos[0] + forward[1]*camera_pos[1] + forward[2]*camera_pos[2] + self.near)),
            FrustumPlane((-forward[0], -forward[1], -forward[2]),
                         (forward[0]*camera_pos[0] + forward[1]*camera_pos[1] + forward[2]*camera_pos[2] + self.far)),
            FrustumPlane(
                (cos_h * forward[0] - sin_h * right[0],
                 cos_h * forward[1] - sin_h * right[1],
                 cos_h * forward[2] - sin_h * right[2]),
                0.0,
            ),
            FrustumPlane(
                (cos_h * forward[0] + sin_h * right[0],
                 cos_h * forward[1] + sin_h * right[1],
                 cos_h * forward[2] + sin_h * right[2]),
                0.0,
            ),
        ]

    def is_sphere_visible(self, sphere: BoundingSphere) -> bool:
        """Return True if the sphere is at least partially inside the frustum."""
        for plane in self._planes:
            dist = plane.signed_distance(sphere.centre)
            if dist < -sphere.radius:
                return False
        return True


class CullingSystem:
    """Manages all cullable objects and applies frustum culling each frame."""

    def __init__(self) -> None:
        self._objects: Dict[str, CullableObject] = {}
        self.culler: FrustumCuller = FrustumCuller()

    def register(self, obj: CullableObject) -> None:
        self._objects[obj.object_id] = obj

    def unregister(self, object_id: str) -> None:
        self._objects.pop(object_id, None)

    def update(
        self,
        camera_pos: Tuple[float, float, float],
        camera_forward: Tuple[float, float, float],
    ) -> int:
        """Update visibility for all objects.

        Returns:
            Number of visible objects after culling.
        """
        self.culler.update_frustum(camera_pos, camera_forward)
        visible_count = 0
        for obj in self._objects.values():
            obj.is_visible = self.culler.is_sphere_visible(obj.bounds)
            if obj.is_visible:
                visible_count += 1
        return visible_count

    @property
    def visible_objects(self) -> List[CullableObject]:
        return [o for o in self._objects.values() if o.is_visible]

    @property
    def culled_count(self) -> int:
        return sum(1 for o in self._objects.values() if not o.is_visible)

    def __repr__(self) -> str:
        total = len(self._objects)
        visible = len(self.visible_objects)
        return f"CullingSystem(total={total}, visible={visible}, culled={total - visible})"
