"""Vehicle Types - definition of all drivable vehicles."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional


class VehicleCategory(Enum):
    """Broad vehicle categories."""

    CAR = auto()
    MOTORCYCLE = auto()
    TRUCK = auto()
    BUS = auto()
    BOAT = auto()
    AIRCRAFT = auto()
    HELICOPTER = auto()
    EMERGENCY = auto()
    SPORTS = auto()
    MUSCLE = auto()
    SUV = auto()
    BICYCLE = auto()


class VehicleType(Enum):
    """Specific vehicle models."""

    # Cars
    SEDAN = auto()
    COUPE = auto()
    HATCHBACK = auto()
    CONVERTIBLE = auto()
    # Sports
    SUPERCAR = auto()
    SPORTS_CAR = auto()
    # Muscle
    MUSCLE_CAR = auto()
    # Trucks / vans
    PICKUP_TRUCK = auto()
    BOX_TRUCK = auto()
    SEMI_TRUCK = auto()
    VAN = auto()
    # Emergency
    POLICE_CAR = auto()
    AMBULANCE = auto()
    FIRE_TRUCK = auto()
    # Motorbikes
    MOTORCYCLE = auto()
    DIRT_BIKE = auto()
    CHOPPER = auto()
    # Watercraft
    SPEEDBOAT = auto()
    YACHT = auto()
    JET_SKI = auto()
    # Aircraft
    SMALL_PLANE = auto()
    JET = auto()
    HELICOPTER = auto()
    # Misc
    BICYCLE = auto()
    GOLF_CART = auto()


@dataclass
class VehicleStats:
    """Performance statistics for a vehicle type."""

    max_speed: float = 50.0          # m/s
    acceleration: float = 5.0        # m/s²
    braking: float = 8.0             # m/s² deceleration
    handling: float = 0.8            # 0.0 (terrible) - 1.0 (perfect)
    mass: float = 1500.0             # kg
    fuel_capacity: float = 60.0      # litres
    fuel_consumption: float = 0.01   # L/s at full throttle
    seats: int = 4
    is_armoured: bool = False
    top_speed_water: float = 0.0     # 0 if not amphibious


@dataclass
class Vehicle:
    """Represents a drivable vehicle in the game world."""

    vehicle_id: str
    vehicle_type: VehicleType
    category: VehicleCategory
    name: str
    stats: VehicleStats = field(default_factory=VehicleStats)
    position: tuple = field(default_factory=lambda: (0.0, 0.0, 0.0))
    heading: float = 0.0
    speed: float = 0.0
    fuel: float = 60.0
    health: float = 1000.0
    max_health: float = 1000.0
    is_on_fire: bool = False
    is_destroyed: bool = False
    is_occupied: bool = False
    driver_id: Optional[str] = None
    color_primary: tuple = field(default_factory=lambda: (255, 255, 255))
    color_secondary: tuple = field(default_factory=lambda: (0, 0, 0))
    license_plate: str = ""
    mods: List[str] = field(default_factory=list)

    @property
    def health_percentage(self) -> float:
        return self.health / self.max_health

    @property
    def is_drivable(self) -> bool:
        return not self.is_destroyed and self.fuel > 0.0

    def repair(self, amount: float = 1000.0) -> None:
        """Restore vehicle health."""
        if not self.is_destroyed:
            self.health = min(self.max_health, self.health + amount)

    def refuel(self, amount: float = 60.0) -> None:
        """Refuel the vehicle."""
        self.fuel = min(self.stats.fuel_capacity, self.fuel + amount)

    def add_mod(self, mod_name: str) -> None:
        """Add a vehicle modification."""
        if mod_name not in self.mods:
            self.mods.append(mod_name)

    def __repr__(self) -> str:
        return (
            f"Vehicle({self.name!r}, "
            f"type={self.vehicle_type.name}, "
            f"speed={self.speed:.1f}m/s, "
            f"hp={self.health:.0f})"
        )


# ------------------------------------------------------------------ #
# Preset vehicle catalogue                                            #
# ------------------------------------------------------------------ #

def create_vehicle_catalogue() -> dict:
    """Return a dictionary of preset vehicle definitions keyed by model name."""
    return {
        "Speedo GT": Vehicle(
            vehicle_id="speedo_gt",
            vehicle_type=VehicleType.SUPERCAR,
            category=VehicleCategory.SPORTS,
            name="Speedo GT",
            stats=VehicleStats(max_speed=90.0, acceleration=12.0, handling=0.95, mass=1200.0),
        ),
        "Urban Cruiser": Vehicle(
            vehicle_id="urban_cruiser",
            vehicle_type=VehicleType.SEDAN,
            category=VehicleCategory.CAR,
            name="Urban Cruiser",
            stats=VehicleStats(max_speed=50.0, acceleration=5.0, handling=0.7, mass=1500.0),
        ),
        "Thunder Hawk": Vehicle(
            vehicle_id="thunder_hawk",
            vehicle_type=VehicleType.MUSCLE_CAR,
            category=VehicleCategory.MUSCLE,
            name="Thunder Hawk",
            stats=VehicleStats(max_speed=65.0, acceleration=9.0, handling=0.6, mass=1700.0),
        ),
        "Waverunner": Vehicle(
            vehicle_id="waverunner",
            vehicle_type=VehicleType.SPEEDBOAT,
            category=VehicleCategory.BOAT,
            name="Waverunner",
            stats=VehicleStats(max_speed=40.0, acceleration=6.0, handling=0.75, mass=800.0),
        ),
        "Nighthawk": Vehicle(
            vehicle_id="nighthawk",
            vehicle_type=VehicleType.HELICOPTER,
            category=VehicleCategory.HELICOPTER,
            name="Nighthawk",
            stats=VehicleStats(max_speed=70.0, acceleration=8.0, handling=0.8, mass=2500.0),
        ),
        "Police Cruiser": Vehicle(
            vehicle_id="police_cruiser",
            vehicle_type=VehicleType.POLICE_CAR,
            category=VehicleCategory.EMERGENCY,
            name="Police Cruiser",
            stats=VehicleStats(max_speed=60.0, acceleration=7.0, handling=0.85, mass=1600.0),
        ),
        "Iron Steed": Vehicle(
            vehicle_id="iron_steed",
            vehicle_type=VehicleType.MOTORCYCLE,
            category=VehicleCategory.MOTORCYCLE,
            name="Iron Steed",
            stats=VehicleStats(max_speed=70.0, acceleration=10.0, handling=0.9, mass=250.0, seats=2),
        ),
    }
