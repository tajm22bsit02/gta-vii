"""Level-of-Detail (LOD) System - mesh quality reduction by distance."""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class LODLevel(Enum):
    """Mesh detail levels from highest to lowest quality."""

    LOD0 = 0   # Full detail (< 50m)
    LOD1 = 1   # High detail (50-150m)
    LOD2 = 2   # Medium detail (150-400m)
    LOD3 = 3   # Low detail (400-800m)
    CULLED = 4  # Not rendered (> 800m)


# Distance thresholds (metres) for each transition
LOD_DISTANCES: Dict[LODLevel, float] = {
    LODLevel.LOD0: 50.0,
    LODLevel.LOD1: 150.0,
    LODLevel.LOD2: 400.0,
    LODLevel.LOD3: 800.0,
    LODLevel.CULLED: float("inf"),
}


@dataclass
class LODObject:
    """An object participating in the LOD system."""

    object_id: str
    position: Tuple[float, float, float]
    current_lod: LODLevel = LODLevel.LOD0
    bias: float = 1.0   # multiplier applied to distance thresholds

    def update_lod(self, camera_distance: float) -> bool:
        """Recompute LOD level from camera distance.

        Args:
            camera_distance: Distance from camera to this object.

        Returns:
            True if the LOD level changed.
        """
        effective_dist = camera_distance / self.bias
        new_lod = LODLevel.CULLED
        for level in (LODLevel.LOD0, LODLevel.LOD1, LODLevel.LOD2, LODLevel.LOD3):
            if effective_dist <= LOD_DISTANCES[level]:
                new_lod = level
                break

        if new_lod != self.current_lod:
            self.current_lod = new_lod
            return True
        return False


class LODSystem:
    """Manages LOD transitions for all registered objects each frame."""

    def __init__(self) -> None:
        self._objects: Dict[str, LODObject] = {}

    def register(self, lod_obj: LODObject) -> None:
        self._objects[lod_obj.object_id] = lod_obj

    def unregister(self, object_id: str) -> None:
        self._objects.pop(object_id, None)

    def update(
        self, camera_position: Tuple[float, float, float]
    ) -> Dict[str, LODLevel]:
        """Update all LOD levels and return a dict of changed objects.

        Args:
            camera_position: Current camera world position.

        Returns:
            Dict mapping object_id -> new LODLevel for objects that changed.
        """
        import math
        changed: Dict[str, LODLevel] = {}
        cx, cy, cz = camera_position
        for obj in self._objects.values():
            dist = math.sqrt(
                (obj.position[0] - cx) ** 2
                + (obj.position[1] - cy) ** 2
                + (obj.position[2] - cz) ** 2
            )
            if obj.update_lod(dist):
                changed[obj.object_id] = obj.current_lod
        return changed

    def get_visible_objects(self) -> List[LODObject]:
        """Return all objects not culled."""
        return [o for o in self._objects.values() if o.current_lod != LODLevel.CULLED]

    @property
    def registered_count(self) -> int:
        return len(self._objects)

    @property
    def culled_count(self) -> int:
        return sum(1 for o in self._objects.values() if o.current_lod == LODLevel.CULLED)

    def __repr__(self) -> str:
        return (
            f"LODSystem("
            f"total={self.registered_count}, "
            f"culled={self.culled_count}, "
            f"visible={self.registered_count - self.culled_count})"
        )
