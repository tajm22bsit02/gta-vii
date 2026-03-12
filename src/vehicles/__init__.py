"""Vehicle system module."""

from .types.vehicle_types import Vehicle, VehicleType, VehicleCategory
from .physics.vehicle_physics import VehiclePhysics
from .damage.vehicle_damage import VehicleDamageSystem, DamageZone

__all__ = [
    "Vehicle",
    "VehicleType",
    "VehicleCategory",
    "VehiclePhysics",
    "VehicleDamageSystem",
    "DamageZone",
]
