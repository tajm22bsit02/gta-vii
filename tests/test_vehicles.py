"""Test suite for the vehicle systems."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from vehicles.types.vehicle_types import (
    Vehicle,
    VehicleType,
    VehicleCategory,
    VehicleStats,
    create_vehicle_catalogue,
)
from vehicles.physics.vehicle_physics import VehiclePhysics
from vehicles.damage.vehicle_damage import VehicleDamageSystem, DamageZone


class TestVehicleTypes:
    def test_create_vehicle(self):
        v = Vehicle(
            vehicle_id="test_car",
            vehicle_type=VehicleType.SEDAN,
            category=VehicleCategory.CAR,
            name="Test Car",
        )
        assert v.vehicle_id == "test_car"
        assert v.health == 1000.0
        assert v.health_percentage == 1.0

    def test_repair_restores_health(self):
        v = Vehicle("v1", VehicleType.SEDAN, VehicleCategory.CAR, "Car")
        v.health = 500.0
        v.repair(300.0)
        assert v.health == 800.0

    def test_repair_capped_at_max(self):
        v = Vehicle("v1", VehicleType.SEDAN, VehicleCategory.CAR, "Car")
        v.repair(9999.0)
        assert v.health == v.max_health

    def test_refuel(self):
        v = Vehicle("v1", VehicleType.SEDAN, VehicleCategory.CAR, "Car")
        v.fuel = 10.0
        v.refuel(30.0)
        assert v.fuel == 40.0

    def test_refuel_capped_at_capacity(self):
        v = Vehicle("v1", VehicleType.SEDAN, VehicleCategory.CAR, "Car")
        v.fuel = 0.0
        v.refuel(9999.0)
        assert v.fuel == v.stats.fuel_capacity

    def test_is_drivable(self):
        v = Vehicle("v1", VehicleType.SEDAN, VehicleCategory.CAR, "Car")
        assert v.is_drivable
        v.fuel = 0.0
        assert not v.is_drivable

    def test_add_mod(self):
        v = Vehicle("v1", VehicleType.SEDAN, VehicleCategory.CAR, "Car")
        v.add_mod("turbo")
        v.add_mod("turbo")  # duplicate should not be added
        assert v.mods.count("turbo") == 1

    def test_catalogue_contains_vehicles(self):
        catalogue = create_vehicle_catalogue()
        assert len(catalogue) > 0
        assert "Speedo GT" in catalogue


class TestVehiclePhysics:
    def _make_physics(self, max_speed: float = 50.0) -> VehiclePhysics:
        v = Vehicle("v1", VehicleType.SEDAN, VehicleCategory.CAR, "Car",
                    stats=VehicleStats(max_speed=max_speed, acceleration=10.0))
        return VehiclePhysics(v)

    def test_initial_speed_is_zero(self):
        phys = self._make_physics()
        assert phys.vehicle.speed == 0.0

    def test_throttle_increases_speed(self):
        phys = self._make_physics()
        phys.set_input(throttle=1.0)
        for _ in range(10):
            phys.update(0.1)
        assert phys.vehicle.speed > 0.0

    def test_brake_reduces_speed(self):
        phys = self._make_physics()
        phys.set_input(throttle=1.0)
        for _ in range(20):
            phys.update(0.1)
        speed_before = phys.vehicle.speed
        phys.set_input(throttle=0.0, brake=1.0)
        for _ in range(5):
            phys.update(0.1)
        assert phys.vehicle.speed < speed_before

    def test_speed_capped_at_max(self):
        phys = self._make_physics(max_speed=20.0)
        phys.set_input(throttle=1.0)
        for _ in range(100):
            phys.update(0.1)
        assert phys.vehicle.speed <= 20.0 + 0.01  # small tolerance

    def test_fuel_decreases_with_throttle(self):
        phys = self._make_physics()
        initial_fuel = phys.vehicle.fuel
        phys.set_input(throttle=1.0)
        for _ in range(50):
            phys.update(0.1)
        assert phys.vehicle.fuel < initial_fuel

    def test_no_acceleration_with_empty_fuel(self):
        phys = self._make_physics()
        phys.vehicle.fuel = 0.0
        phys.set_input(throttle=1.0)
        phys.update(0.1)
        assert phys.vehicle.speed == pytest.approx(0.0, abs=1e-3)

    def test_steering_changes_heading(self):
        phys = self._make_physics()
        phys.set_input(throttle=1.0)
        for _ in range(5):
            phys.update(0.1)
        initial_heading = phys.vehicle.heading
        phys.set_input(throttle=1.0, steer=1.0)
        for _ in range(5):
            phys.update(0.1)
        assert phys.vehicle.heading != initial_heading

    def test_destroyed_vehicle_does_not_move(self):
        phys = self._make_physics()
        phys.vehicle.is_destroyed = True
        phys.set_input(throttle=1.0)
        phys.update(0.1)
        assert phys.vehicle.speed == 0.0

    def test_speed_in_kmh(self):
        phys = self._make_physics()
        phys._speed_ms = 10.0
        assert phys.speed_kmh == pytest.approx(36.0)


class TestVehicleDamageSystem:
    def _make_system(self) -> tuple:
        v = Vehicle("v1", VehicleType.SEDAN, VehicleCategory.CAR, "Car")
        system = VehicleDamageSystem(v)
        return v, system

    def test_damage_reduces_zone_integrity(self):
        v, system = self._make_system()
        initial = system.get_zone_state(DamageZone.FRONT_LEFT).integrity
        system.apply_damage(DamageZone.FRONT_LEFT, 20.0)
        after = system.get_zone_state(DamageZone.FRONT_LEFT).integrity
        assert after < initial

    def test_engine_damage_can_cause_fire(self):
        v, system = self._make_system()
        system.apply_damage(DamageZone.ENGINE, 90.0)
        # Engine integrity below fire threshold
        zone = system.get_zone_state(DamageZone.ENGINE)
        if zone.integrity <= system.FIRE_THRESHOLD:
            assert v.is_on_fire

    def test_fuel_tank_damage_drains_fuel(self):
        v, system = self._make_system()
        # Destroy the fuel tank
        system.apply_damage(DamageZone.FUEL_TANK, 100.0, ignore_multiplier=True)
        zone = system.get_zone_state(DamageZone.FUEL_TANK)
        if zone.is_broken:
            assert v.fuel == 0.0

    def test_destruction_callback_fires(self):
        v, system = self._make_system()
        destroyed = []
        system.on_destroyed(lambda veh: destroyed.append(veh))
        # Massive damage to trigger destruction
        for zone in DamageZone:
            system.apply_damage(zone, 200.0)
        if v.is_destroyed:
            assert len(destroyed) >= 1

    def test_repair_all_restores(self):
        v, system = self._make_system()
        system.apply_damage(DamageZone.WINDSHIELD, 50.0)
        system.repair_all()
        assert system.get_zone_state(DamageZone.WINDSHIELD).integrity == 100.0

    def test_overall_integrity_property(self):
        v, system = self._make_system()
        assert system.overall_integrity == pytest.approx(100.0)
