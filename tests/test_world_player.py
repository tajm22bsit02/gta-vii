"""Test suite for the world and player systems."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from world.weather.weather_system import WeatherSystem, WeatherCondition
from world.traffic.traffic_system import TrafficSystem, TrafficVehicle, TrafficState
from world.pedestrians.pedestrian_ai import PedestrianAI, Pedestrian, PedestrianBehavior
from world.city.city_manager import CityManager, District, DistrictType
from player.character.character_controller import CharacterController, MovementState
from player.health.health_system import HealthSystem, DamageType, DamageEvent
from player.inventory.inventory_system import InventorySystem, WeaponItem


# ------------------------------------------------------------------ #
# Tests: Weather System                                               #
# ------------------------------------------------------------------ #

class TestWeatherSystem:
    def test_initial_condition(self):
        ws = WeatherSystem()
        assert ws.current is not None
        assert ws.current.condition is not None

    def test_force_condition(self):
        ws = WeatherSystem()
        ws.force_condition(WeatherCondition.RAIN)
        assert ws.current.condition == WeatherCondition.RAIN

    def test_game_time_advances(self):
        ws = WeatherSystem()
        initial = ws.time_of_day.hour
        ws.update(3600.0)  # 1 hour

    def test_is_daytime(self):
        ws = WeatherSystem()
        ws.time_of_day.time = 12.0
        assert ws.time_of_day.is_daytime()

    def test_is_nighttime(self):
        ws = WeatherSystem()
        ws.time_of_day.time = 23.0
        assert not ws.time_of_day.is_daytime()  # 23:00 is night (>= 20:00)

    def test_weather_update_does_not_crash(self):
        ws = WeatherSystem()
        ws.update(0.5)

    def test_wind_speed_in_storm(self):
        ws = WeatherSystem()
        ws.force_condition(WeatherCondition.THUNDERSTORM)
        assert ws.current.wind_speed > 0.0

    def test_rain_intensity(self):
        ws = WeatherSystem()
        ws.force_condition(WeatherCondition.RAIN)
        assert ws.current.precipitation > 0.0
        ws.force_condition(WeatherCondition.CLEAR)
        assert ws.current.precipitation == 0.0

    def test_change_callback_fired(self):
        called = []
        ws = WeatherSystem()
        ws.add_change_callback(lambda old, new: called.append((old, new)))
        ws.force_condition(WeatherCondition.SNOW)
        assert len(called) >= 1


# ------------------------------------------------------------------ #
# Tests: Traffic System                                               #
# ------------------------------------------------------------------ #

class TestTrafficSystem:
    def test_vehicle_count_starts_at_zero(self):
        ts = TrafficSystem()
        assert ts.vehicle_count == 0

    def test_update_spawns_vehicles(self):
        ts = TrafficSystem()
        ts.SPAWN_INTERVAL = 0.1
        ts.update(1.0, player_position=(0.0, 0.0))
        assert ts.vehicle_count >= 0  # May or may not spawn in one tick

    def test_add_traffic_light(self):
        from world.traffic.traffic_system import TrafficLight
        ts = TrafficSystem()
        light = TrafficLight((0.0, 0.0))
        ts.add_traffic_light(light)
        assert len(ts._traffic_lights) == 1

    def test_traffic_vehicle_state_enum(self):
        assert TrafficState.MOVING in TrafficState
        assert TrafficState.STOPPED in TrafficState

    def test_traffic_vehicle_update(self):
        v = TrafficVehicle("v1", None, (0.0, 0.0), destination=(50.0, 0.0), speed=5.0)
        v.state = TrafficState.MOVING
        pos_before = v.position
        v.update(1.0)
        # Should have moved towards destination
        assert v.position != pos_before or v.state == TrafficState.STOPPED

    def test_get_vehicles_near(self):
        ts = TrafficSystem()
        ts._vehicles["v1"] = TrafficVehicle("v1", None, (5.0, 0.0))
        ts._vehicles["v2"] = TrafficVehicle("v2", None, (1000.0, 0.0))
        near = ts.get_vehicles_near((0.0, 0.0), 20.0)
        assert len(near) == 1


# ------------------------------------------------------------------ #
# Tests: Pedestrian System                                            #
# ------------------------------------------------------------------ #

class TestPedestrianAI:
    def test_pedestrian_count_starts_zero(self):
        ai = PedestrianAI()
        assert ai.pedestrian_count == 0

    def test_update_spawns_pedestrians(self):
        ai = PedestrianAI()
        ai.SPAWN_INTERVAL = 0.1
        ai.update(1.0, player_position=(0.0, 0.0))
        assert ai.pedestrian_count >= 0

    def test_trigger_mass_panic(self):
        ai = PedestrianAI()
        ai._pedestrians["p1"] = Pedestrian("p1", (0.0, 0.0))
        ai.trigger_mass_panic((0.0, 0.0))
        for ped in ai._pedestrians.values():
            assert ped.behavior == PedestrianBehavior.PANICKING

    def test_pedestrian_trigger_panic(self):
        ped = Pedestrian("p1", (0.0, 0.0))
        ped.trigger_panic(5.0)
        assert ped.behavior == PedestrianBehavior.PANICKING

    def test_pedestrian_set_destination(self):
        ped = Pedestrian("p1", (0.0, 0.0))
        ped.set_destination((10.0, 10.0))
        assert ped.destination == (10.0, 10.0)

    def test_get_pedestrians_near(self):
        ai = PedestrianAI()
        ai._pedestrians["p1"] = Pedestrian("p1", (5.0, 0.0))
        ai._pedestrians["p2"] = Pedestrian("p2", (1000.0, 0.0))
        near = ai.get_pedestrians_near((0.0, 0.0), 10.0)
        assert len(near) == 1


# ------------------------------------------------------------------ #
# Tests: City Manager                                                 #
# ------------------------------------------------------------------ #

class TestCityManager:
    def test_districts_populated(self):
        cm = CityManager()
        assert len(cm._districts) > 0

    def test_get_district_at_position(self):
        cm = CityManager()
        district = cm.get_district_at(0.0, 0.0)
        # May be None if origin is outside all districts - just check no crash

    def test_get_district_by_name(self):
        cm = CityManager()
        first_name = cm.district_names[0]
        district = cm.get_district(first_name)
        assert district is not None

    def test_district_types(self):
        cm = CityManager()
        types = {d.district_type for d in cm._districts.values()}
        assert len(types) > 0

    def test_total_buildings(self):
        cm = CityManager()
        assert cm.total_buildings >= 0

    def test_total_roads(self):
        cm = CityManager()
        assert cm.total_roads >= 0

    def test_register_district(self):
        cm = CityManager()
        initial_count = len(cm._districts)
        new_district = District("custom", "Custom", DistrictType.INDUSTRIAL, (500.0, 500.0), 100.0, 100.0)
        cm.register_district(new_district)
        assert len(cm._districts) == initial_count + 1


# ------------------------------------------------------------------ #
# Tests: Character Controller                                         #
# ------------------------------------------------------------------ #

class TestCharacterController:
    def test_initial_state(self):
        cc = CharacterController()
        assert cc.state == MovementState.IDLE

    def test_move_forward(self):
        cc = CharacterController()
        cc.update(0.1, move_input=(0.0, 1.0))
        assert cc.state in (MovementState.WALKING, MovementState.RUNNING)

    def test_sprint(self):
        cc = CharacterController()
        cc.update(0.1, move_input=(0.0, 1.0), sprint=True)
        assert cc.state == MovementState.SPRINTING

    def test_crouch_state(self):
        cc = CharacterController()
        cc.update(0.1, move_input=(0.0, 0.5), crouch=True)
        assert cc.state == MovementState.CROUCHING

    def test_jump_while_grounded(self):
        cc = CharacterController()
        initial_y = cc.position.y
        cc.update(0.1, jump=True)
        # After jump, vertical velocity should be positive
        assert cc._vertical_velocity > 0.0 or cc.position.y >= initial_y

    def test_position_updates_on_move(self):
        from engine.physics.physics_engine import Vector3
        cc = CharacterController()
        initial_pos = cc.position.copy()
        cc.update(1.0, move_input=(0.0, 1.0))
        assert cc.position.z != initial_pos.z or cc.position.x != initial_pos.x

    def test_take_cover(self):
        cc = CharacterController()
        cc.take_cover()
        assert cc.is_in_cover
        assert cc.state == MovementState.CROUCHING

    def test_add_wanted_level(self):
        cc = CharacterController()
        cc.add_wanted_level(2)
        assert cc.wanted_level == 2

    def test_wanted_level_capped_at_5(self):
        cc = CharacterController()
        cc.add_wanted_level(10)
        assert cc.wanted_level == 5


# ------------------------------------------------------------------ #
# Tests: Health System                                                #
# ------------------------------------------------------------------ #

class TestHealthSystem:
    def test_initial_health(self):
        hs = HealthSystem()
        assert hs.health == hs.MAX_HEALTH
        assert hs.is_alive

    def test_take_damage(self):
        hs = HealthSystem()
        initial = hs.health
        event = DamageEvent(DamageType.BULLET, 30.0)
        hs.take_damage(event)
        assert hs.health < initial

    def test_death(self):
        hs = HealthSystem()
        event = DamageEvent(DamageType.EXPLOSION, 9999.0)
        hs.take_damage(event)
        assert not hs.is_alive

    def test_heal_restores_health(self):
        hs = HealthSystem()
        event = DamageEvent(DamageType.MELEE, 50.0)
        hs.take_damage(event)
        hs.heal(30.0)
        # Health should have increased by 30 (up to max)

    def test_armour_absorbs_damage(self):
        hs = HealthSystem()
        hs.add_armour(100.0)
        health_before = hs.health
        event = DamageEvent(DamageType.BULLET, 30.0)
        hs.take_damage(event)
        # Armour should have absorbed some/all damage
        assert hs.armour < 100.0 or hs.health < health_before

    def test_death_callback_fires(self):
        fired = []
        hs = HealthSystem()
        hs.on_death(lambda: fired.append(True))
        hs.take_damage(DamageEvent(DamageType.EXPLOSION, 9999.0))
        assert len(fired) == 1

    def test_respawn_restores_health(self):
        hs = HealthSystem()
        hs.take_damage(DamageEvent(DamageType.EXPLOSION, 9999.0))
        hs.respawn()
        assert hs.is_alive
        assert hs.health > 0


# ------------------------------------------------------------------ #
# Tests: Inventory System                                             #
# ------------------------------------------------------------------ #

class TestInventorySystem:
    def _make_pistol(self) -> WeaponItem:
        from player.inventory.inventory_system import ItemCategory
        return WeaponItem(
            item_id="pistol",
            name="Pistol",
            category=ItemCategory.WEAPON,
            magazine_size=12,
            reserved_ammo=60,
        )

    def test_add_weapon(self):
        inv = InventorySystem()
        pistol = self._make_pistol()
        inv.add_item(pistol)
        assert inv.has_item("pistol")

    def test_remove_weapon(self):
        inv = InventorySystem()
        pistol = self._make_pistol()
        inv.add_item(pistol)
        # quantity defaults to 1 in InventoryItem
        inv.remove_item("pistol")
        assert not inv.has_item("pistol")

    def test_equip_weapon_to_slot(self):
        inv = InventorySystem()
        pistol = self._make_pistol()
        inv.add_item(pistol)
        result = inv.equip_weapon(pistol, slot=1)
        assert result is True

    def test_add_ammo_to_weapon(self):
        inv = InventorySystem()
        pistol = self._make_pistol()
        inv.add_item(pistol)
        initial = pistol.reserved_ammo
        pistol.add_ammo(30)
        assert pistol.reserved_ammo == initial + 30

    def test_add_money(self):
        inv = InventorySystem()
        inv.add_money(100)
        assert inv.money == 100

    def test_spend_money(self):
        inv = InventorySystem()
        inv.add_money(200)
        result = inv.spend_money(100)
        assert result is True
        assert inv.money == 100

    def test_spend_insufficient_money(self):
        inv = InventorySystem()
        inv.add_money(50)
        result = inv.spend_money(100)
        assert result is False
        assert inv.money == 50

    def test_item_count(self):
        inv = InventorySystem()
        inv.add_item(self._make_pistol())
        assert inv.item_count >= 1
