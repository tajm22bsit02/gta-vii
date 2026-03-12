"""Test suite for the mission and combat systems."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from missions.framework.mission_framework import (
    Mission,
    MissionManager,
    MissionReward,
    MissionStatus,
    MissionTrigger,
    MissionType,
)
from missions.objectives.objective_tracker import (
    Objective,
    ObjectiveStatus,
    ObjectiveTracker,
    ObjectiveType,
)
from combat.weapons.weapon_system import Weapon, WeaponStats, WeaponSystem, WeaponType
from combat.ai.enemy_ai import Enemy, EnemyAI, EnemyCombatState, PatrolPoint
from combat.cover.cover_system import CoverPoint, CoverSystem, CoverType


# ------------------------------------------------------------------ #
# Concrete mission for testing                                        #
# ------------------------------------------------------------------ #

class SimpleTestMission(Mission):
    def __init__(self, mission_id: str, **kwargs):
        super().__init__(mission_id, "Test Mission", "A test mission", **kwargs)
        self.started = False
        self.completed = False
        self.failed_reason = ""

    def on_start(self):
        self.started = True

    def on_update(self, delta_time: float):
        pass

    def on_complete(self):
        self.completed = True

    def on_fail(self, reason: str):
        self.failed_reason = reason


# ------------------------------------------------------------------ #
# Tests: Mission Framework                                            #
# ------------------------------------------------------------------ #

class TestMission:
    def test_start_sets_active(self):
        m = SimpleTestMission("m1")
        m.status = MissionStatus.AVAILABLE
        m.start()
        assert m.status == MissionStatus.ACTIVE
        assert m.started

    def test_complete_sets_completed(self):
        m = SimpleTestMission("m1")
        m.status = MissionStatus.AVAILABLE
        m.start()
        m.complete()
        assert m.status == MissionStatus.COMPLETED
        assert m.completed

    def test_fail_sets_failed(self):
        m = SimpleTestMission("m1")
        m.status = MissionStatus.AVAILABLE
        m.start()
        m.fail("test reason")
        assert m.status == MissionStatus.FAILED
        assert m.failed_reason == "test reason"

    def test_time_limit_causes_failure(self):
        m = SimpleTestMission("m1")
        m.time_limit = 5.0
        m.status = MissionStatus.AVAILABLE
        m.start()
        m.update(3.0)
        assert m.status == MissionStatus.ACTIVE
        m.update(3.0)
        assert m.status == MissionStatus.FAILED

    def test_complete_callback_fired(self):
        fired = []
        m = SimpleTestMission("m1")
        m.on_complete_callback(lambda mission: fired.append(mission))
        m.status = MissionStatus.AVAILABLE
        m.start()
        m.complete()
        assert len(fired) == 1

    def test_fail_callback_fired(self):
        fired = []
        m = SimpleTestMission("m1")
        m.on_fail_callback(lambda mission: fired.append(mission))
        m.status = MissionStatus.AVAILABLE
        m.start()
        m.fail()
        assert len(fired) == 1


class TestMissionManager:
    def test_register_and_unlock(self):
        manager = MissionManager()
        m = SimpleTestMission("m1")
        manager.register(m)
        result = manager.unlock("m1")
        assert result
        assert m.status == MissionStatus.AVAILABLE

    def test_unlock_with_unmet_prereqs(self):
        manager = MissionManager()
        m1 = SimpleTestMission("m1")
        m2 = SimpleTestMission("m2", prerequisites=["m1"])
        manager.register(m1)
        manager.register(m2)
        result = manager.unlock("m2")
        assert not result
        assert m2.status == MissionStatus.LOCKED

    def test_unlock_with_met_prereqs(self):
        manager = MissionManager()
        m1 = SimpleTestMission("m1")
        m2 = SimpleTestMission("m2", prerequisites=["m1"])
        manager.register(m1)
        manager.register(m2)
        manager.unlock("m1")
        m1.status = MissionStatus.COMPLETED
        result = manager.unlock("m2")
        assert result

    def test_start_mission(self):
        manager = MissionManager()
        m = SimpleTestMission("m1")
        manager.register(m)
        manager.unlock("m1")
        assert manager.start_mission("m1")
        assert manager.active_mission is m

    def test_no_concurrent_missions(self):
        manager = MissionManager()
        m1 = SimpleTestMission("m1")
        m2 = SimpleTestMission("m2")
        manager.register(m1)
        manager.register(m2)
        manager.unlock("m1")
        manager.unlock("m2")
        manager.start_mission("m1")
        assert not manager.start_mission("m2")

    def test_trigger_detection(self):
        manager = MissionManager()
        m = SimpleTestMission("m1")
        manager.register(m)
        manager.unlock("m1")
        trigger = MissionTrigger(position=(100.0, 100.0), radius=5.0, mission_id="m1")
        manager.add_trigger(trigger)
        result = manager.check_triggers((101.0, 101.0))
        assert result == "m1"

    def test_trigger_out_of_range(self):
        manager = MissionManager()
        m = SimpleTestMission("m1")
        manager.register(m)
        manager.unlock("m1")
        trigger = MissionTrigger(position=(100.0, 100.0), radius=5.0, mission_id="m1")
        manager.add_trigger(trigger)
        result = manager.check_triggers((200.0, 200.0))
        assert result is None


# ------------------------------------------------------------------ #
# Tests: Objective Tracker                                            #
# ------------------------------------------------------------------ #

class TestObjectiveTracker:
    def test_add_objective_activates_first(self):
        tracker = ObjectiveTracker(sequential=False)
        obj = Objective("o1", ObjectiveType.REACH_LOCATION, "Go here")
        tracker.add_objective(obj)
        assert obj.status == ObjectiveStatus.ACTIVE

    def test_sequential_activates_one_at_a_time(self):
        tracker = ObjectiveTracker(sequential=True)
        obj1 = Objective("o1", ObjectiveType.REACH_LOCATION, "Go here")
        obj2 = Objective("o2", ObjectiveType.COLLECT_ITEM, "Get item")
        tracker.add_objective(obj1)
        tracker.add_objective(obj2)
        assert obj1.status == ObjectiveStatus.ACTIVE
        assert obj2.status == ObjectiveStatus.PENDING

    def test_advance_completes_objective(self):
        tracker = ObjectiveTracker(sequential=False)
        obj = Objective("o1", ObjectiveType.ELIMINATE_TARGET, "Kill target", target_value=3.0)
        tracker.add_objective(obj)
        tracker.update()
        result = obj.advance(3.0)
        assert result is True
        assert obj.status == ObjectiveStatus.COMPLETED

    def test_progress_percentage(self):
        obj = Objective("o1", ObjectiveType.COLLECT_ITEM, "Collect 10", target_value=10.0)
        obj.status = ObjectiveStatus.ACTIVE
        obj.advance(5.0)
        assert obj.progress_percentage == pytest.approx(50.0)

    def test_all_required_complete(self):
        tracker = ObjectiveTracker(sequential=False)
        obj = Objective("o1", ObjectiveType.REACH_LOCATION, "Go")
        tracker.add_objective(obj)
        tracker.update()
        obj.mark_complete()
        assert tracker.all_required_complete

    def test_optional_objective_doesnt_block_completion(self):
        tracker = ObjectiveTracker(sequential=False)
        required = Objective("r", ObjectiveType.REACH_LOCATION, "Required")
        optional = Objective("o", ObjectiveType.TAKE_PHOTO, "Optional", is_optional=True)
        tracker.add_objective(required)
        tracker.add_objective(optional)
        tracker.update()
        required.mark_complete()
        assert tracker.all_required_complete


# ------------------------------------------------------------------ #
# Tests: Weapon System                                                #
# ------------------------------------------------------------------ #

class TestWeaponSystem:
    def test_fire_reduces_ammo(self):
        weapon = Weapon("pistol", WeaponType.PISTOL, "Pistol",
                        WeaponStats(magazine_size=12, fire_rate=5.0))
        initial = weapon.current_ammo
        weapon.fire((0, 0, 0), (0, 0, 1))
        assert weapon.current_ammo == initial - 1

    def test_empty_mag_cannot_fire(self):
        weapon = Weapon("pistol", WeaponType.PISTOL, "Pistol",
                        WeaponStats(magazine_size=12, fire_rate=5.0))
        weapon.current_ammo = 0
        result = weapon.fire((0, 0, 0), (0, 0, 1))
        assert result is None

    def test_reload_refills_mag(self):
        weapon = Weapon("pistol", WeaponType.PISTOL, "Pistol",
                        WeaponStats(magazine_size=12, fire_rate=5.0, reload_time=0.01),
                        reserved_ammo=30)
        weapon.current_ammo = 0
        weapon.reload()
        weapon.update(0.1)  # Finish reload
        assert weapon.current_ammo == 12

    def test_no_reload_without_reserved_ammo(self):
        weapon = Weapon("pistol", WeaponType.PISTOL, "Pistol",
                        WeaponStats(magazine_size=12), reserved_ammo=0)
        weapon.current_ammo = 0
        result = weapon.reload()
        assert result is False

    def test_bullet_has_damage(self):
        weapon = Weapon("rifle", WeaponType.ASSAULT_RIFLE, "Rifle",
                        WeaponStats(damage=35.0, fire_rate=10.0))
        bullet = weapon.fire((0, 0, 0), (0, 0, 1))
        assert bullet is not None
        assert bullet.damage == 35.0

    def test_weapon_system_catalogue(self):
        catalogue = WeaponSystem.create_catalogue()
        assert "pistol" in catalogue
        assert "assault_rifle" in catalogue
        assert "sniper" in catalogue

    def test_weapon_system_fire_and_track(self):
        system = WeaponSystem()
        for wep in WeaponSystem.create_catalogue().values():
            system.register_weapon(wep)
        bullet = system.fire_weapon("pistol", (0, 0, 0), (0, 0, 1))
        assert bullet is not None
        assert system.active_bullet_count >= 1

    def test_bullets_expire(self):
        system = WeaponSystem()
        wep = Weapon("pistol", WeaponType.PISTOL, "Pistol",
                     WeaponStats(range_=5.0, projectile_speed=100.0, fire_rate=5.0))
        system.register_weapon(wep)
        system.fire_weapon("pistol", (0, 0, 0), (0, 0, 1))
        # Advance until bullet has travelled beyond range
        for _ in range(20):
            system.update(0.1)
        assert system.active_bullet_count == 0


# ------------------------------------------------------------------ #
# Tests: Enemy AI                                                     #
# ------------------------------------------------------------------ #

class TestEnemyAI:
    def test_enemy_detects_player(self):
        ai = EnemyAI()
        enemy = Enemy("e1", (0.0, 0.0), detection_range=50.0)
        ai.add_enemy(enemy)
        # Enemy transitions IDLE -> ALERT -> ENGAGE over multiple updates
        for _ in range(20):
            ai.update(0.5, (10.0, 0.0))
        assert enemy.state in (EnemyCombatState.ALERT, EnemyCombatState.ENGAGE)

    def test_enemy_patrols(self):
        ai = EnemyAI()
        patrol = [PatrolPoint((10.0, 0.0)), PatrolPoint((-10.0, 0.0))]
        enemy = Enemy("e1", (0.0, 0.0), detection_range=5.0, patrol_route=patrol)
        ai.add_enemy(enemy)
        # Player far away - should patrol
        ai.update(0.1, (1000.0, 1000.0))
        assert enemy.state == EnemyCombatState.PATROL

    def test_enemy_takes_damage(self):
        enemy = Enemy("e1", (0.0, 0.0))
        enemy.take_damage(30.0)
        assert enemy.health == pytest.approx(70.0)

    def test_enemy_dies(self):
        enemy = Enemy("e1", (0.0, 0.0))
        enemy.take_damage(1000.0)
        assert not enemy.is_alive
        assert enemy.state == EnemyCombatState.DEAD

    def test_dead_enemy_count(self):
        ai = EnemyAI()
        e1 = Enemy("e1", (0.0, 0.0))
        e2 = Enemy("e2", (5.0, 0.0))
        ai.add_enemy(e1)
        ai.add_enemy(e2)
        e1.take_damage(1000.0)
        assert ai.alive_count == 1
        assert ai.dead_count == 1

    def test_get_enemies_near(self):
        ai = EnemyAI()
        ai.add_enemy(Enemy("e1", (1.0, 0.0)))
        ai.add_enemy(Enemy("e2", (1000.0, 0.0)))
        near = ai.get_enemies_near((0.0, 0.0), 10.0)
        assert len(near) == 1


# ------------------------------------------------------------------ #
# Tests: Cover System                                                 #
# ------------------------------------------------------------------ #

class TestCoverSystem:
    def test_find_cover(self):
        system = CoverSystem()
        cp = CoverPoint("c1", (5.0, 0.0), CoverType.FULL)
        system.register_cover(cp)
        found = system.find_nearest_cover((0.0, 0.0))
        assert found is cp

    def test_take_cover(self):
        system = CoverSystem()
        cp = CoverPoint("c1", (5.0, 0.0), CoverType.FULL)
        system.register_cover(cp)
        result = system.take_cover(cp)
        assert result
        assert system.player_in_cover

    def test_leave_cover(self):
        system = CoverSystem()
        cp = CoverPoint("c1", (5.0, 0.0), CoverType.FULL)
        system.register_cover(cp)
        system.take_cover(cp)
        system.leave_cover()
        assert not system.player_in_cover

    def test_damage_reduced_in_cover(self):
        system = CoverSystem()
        cp = CoverPoint("c1", (5.0, 0.0), CoverType.FULL)
        system.register_cover(cp)
        system.take_cover(cp)
        damage = system.calculate_damage_taken(100.0, in_cover=True)
        assert damage < 100.0

    def test_full_damage_out_of_cover(self):
        system = CoverSystem()
        damage = system.calculate_damage_taken(100.0, in_cover=False)
        assert damage == pytest.approx(100.0)

    def test_protection_factors(self):
        assert CoverPoint("c", (0, 0), CoverType.FULL).protection_factor == pytest.approx(0.85)
        assert CoverPoint("c", (0, 0), CoverType.HALF).protection_factor == pytest.approx(0.60)
        assert CoverPoint("c", (0, 0), CoverType.PARTIAL).protection_factor == pytest.approx(0.30)

    def test_max_occupants(self):
        cp = CoverPoint("c1", (0.0, 0.0), CoverType.FULL, max_occupants=1)
        assert cp.occupy()
        assert not cp.is_available
        assert not cp.occupy()

    def test_urban_cover_generation(self):
        points = CoverSystem.generate_urban_cover((0.0, 0.0), count=10)
        assert len(points) == 10
