"""Vehicle Damage System - zone-based damage model."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional

from ..types.vehicle_types import Vehicle


class DamageZone(Enum):
    """Named zones on the vehicle body."""

    ENGINE = auto()
    FRONT_LEFT = auto()
    FRONT_RIGHT = auto()
    REAR_LEFT = auto()
    REAR_RIGHT = auto()
    ROOF = auto()
    WINDSHIELD = auto()
    FUEL_TANK = auto()


@dataclass
class ZoneDamageState:
    """Damage state for a single vehicle zone."""

    zone: DamageZone
    integrity: float = 100.0     # 100 = pristine, 0 = destroyed
    is_broken: bool = False
    is_on_fire: bool = False

    @property
    def damage_level(self) -> str:
        if self.integrity >= 80:
            return "pristine"
        if self.integrity >= 50:
            return "scratched"
        if self.integrity >= 20:
            return "damaged"
        return "destroyed"


VehicleDestroyedCallback = Callable[[Vehicle], None]


class VehicleDamageSystem:
    """Models zone-specific damage for a vehicle.

    Each zone has independent integrity. Critical zones (engine, fuel
    tank) trigger special effects when destroyed.
    """

    FIRE_THRESHOLD: float = 15.0          # Engine integrity below which fire starts
    EXPLOSION_THRESHOLD: float = 5.0      # Vehicle blows up below this total integrity
    ZONE_MULTIPLIERS: Dict[DamageZone, float] = {
        DamageZone.ENGINE: 1.5,
        DamageZone.FUEL_TANK: 2.0,
        DamageZone.WINDSHIELD: 0.5,
        DamageZone.ROOF: 0.8,
        DamageZone.FRONT_LEFT: 1.0,
        DamageZone.FRONT_RIGHT: 1.0,
        DamageZone.REAR_LEFT: 1.0,
        DamageZone.REAR_RIGHT: 1.0,
    }

    def __init__(self, vehicle: Vehicle) -> None:
        self.vehicle: Vehicle = vehicle
        self._zones: Dict[DamageZone, ZoneDamageState] = {
            zone: ZoneDamageState(zone=zone) for zone in DamageZone
        }
        self._destroyed_callbacks: List[VehicleDestroyedCallback] = []

    def apply_damage(
        self,
        zone: DamageZone,
        amount: float,
        ignore_multiplier: bool = False,
    ) -> float:
        """Apply damage to a specific zone.

        Args:
            zone: The target damage zone.
            amount: Raw damage amount.
            ignore_multiplier: If True, use amount directly.

        Returns:
            Effective damage applied to the zone.
        """
        if self.vehicle.is_destroyed:
            return 0.0

        multiplier = 1.0 if ignore_multiplier else self.ZONE_MULTIPLIERS.get(zone, 1.0)
        effective = amount * multiplier
        zone_state = self._zones[zone]
        zone_state.integrity = max(0.0, zone_state.integrity - effective)

        if zone_state.integrity <= 0.0:
            zone_state.is_broken = True

        # Reduce overall vehicle health proportionally
        total_integrity_fraction = effective / 100.0
        self.vehicle.health = max(
            0.0, self.vehicle.health - self.vehicle.max_health * total_integrity_fraction
        )

        self._check_critical_effects(zone, zone_state)
        self._check_destruction()

        return effective

    def repair_zone(self, zone: DamageZone, amount: float = 100.0) -> None:
        """Repair a single zone."""
        zone_state = self._zones[zone]
        zone_state.integrity = min(100.0, zone_state.integrity + amount)
        if zone_state.integrity > 0.0:
            zone_state.is_broken = False

    def repair_all(self) -> None:
        """Fully repair all zones."""
        for zone_state in self._zones.values():
            zone_state.integrity = 100.0
            zone_state.is_broken = False
            zone_state.is_on_fire = False
        self.vehicle.health = self.vehicle.max_health
        self.vehicle.is_on_fire = False
        self.vehicle.is_destroyed = False

    def get_zone_state(self, zone: DamageZone) -> ZoneDamageState:
        """Return the damage state for a specific zone."""
        return self._zones[zone]

    def on_destroyed(self, callback: VehicleDestroyedCallback) -> None:
        """Register a callback for when the vehicle is destroyed."""
        self._destroyed_callbacks.append(callback)

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _check_critical_effects(self, zone: DamageZone, state: ZoneDamageState) -> None:
        if zone == DamageZone.ENGINE and state.integrity <= self.FIRE_THRESHOLD:
            state.is_on_fire = True
            self.vehicle.is_on_fire = True
        if zone == DamageZone.FUEL_TANK and state.is_broken:
            self.vehicle.fuel = 0.0

    def _check_destruction(self) -> None:
        if self.vehicle.health <= self.EXPLOSION_THRESHOLD:
            self.vehicle.is_destroyed = True
            for cb in self._destroyed_callbacks:
                cb(self.vehicle)

    @property
    def overall_integrity(self) -> float:
        """Return average integrity across all zones (0-100)."""
        return sum(z.integrity for z in self._zones.values()) / len(self._zones)

    def __repr__(self) -> str:
        return (
            f"VehicleDamageSystem({self.vehicle.name!r}, "
            f"integrity={self.overall_integrity:.1f}%)"
        )
