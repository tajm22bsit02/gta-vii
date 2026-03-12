"""Test suite for the economy and save systems."""

import pytest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from economy.currency.currency_system import CurrencySystem, Transaction, TransactionType
from economy.property.property_system import PropertySystem, Property, PropertyType
from economy.progression.progression_system import ProgressionSystem, Skill, SkillCategory
from save.slots.save_manager import SaveManager, GameState
from save.checkpoint.checkpoint_system import CheckpointSystem, Checkpoint


# ------------------------------------------------------------------ #
# Tests: Currency System                                              #
# ------------------------------------------------------------------ #

class TestCurrencySystem:
    def test_initial_balance(self):
        cs = CurrencySystem(initial_balance=1000)
        assert cs.balance == 1000

    def test_earn_increases_balance(self):
        cs = CurrencySystem(initial_balance=0)
        cs.earn(500, TransactionType.MISSION_REWARD, "test")
        assert cs.balance == 500

    def test_spend_decreases_balance(self):
        cs = CurrencySystem(initial_balance=1000)
        result = cs.spend(400, TransactionType.STORE_PURCHASE, "test")
        assert result is True
        assert cs.balance == 600

    def test_spend_insufficient_funds(self):
        cs = CurrencySystem(initial_balance=100)
        result = cs.spend(200, TransactionType.STORE_PURCHASE, "test")
        assert result is False
        assert cs.balance == 100

    def test_can_afford(self):
        cs = CurrencySystem(initial_balance=500)
        assert cs.can_afford(500)
        assert cs.can_afford(499)
        assert not cs.can_afford(501)

    def test_earn_negative_raises(self):
        cs = CurrencySystem()
        with pytest.raises(ValueError):
            cs.earn(-100)

    def test_spend_negative_raises(self):
        cs = CurrencySystem(initial_balance=1000)
        with pytest.raises(ValueError):
            cs.spend(-50)

    def test_transaction_history(self):
        cs = CurrencySystem(initial_balance=1000)
        cs.earn(200, TransactionType.MISSION_REWARD)
        cs.spend(100, TransactionType.STORE_PURCHASE)
        history = cs.get_transaction_history()
        assert len(history) == 2

    def test_balance_callback(self):
        changes = []
        cs = CurrencySystem(initial_balance=100)
        cs.add_change_callback(lambda old, new, tx: changes.append((old, new)))
        cs.earn(50)
        assert changes[-1] == (100, 150)

    def test_total_earned(self):
        cs = CurrencySystem(initial_balance=0)
        cs.earn(300)
        cs.earn(200)
        assert cs.total_earned == 500

    def test_total_spent(self):
        cs = CurrencySystem(initial_balance=1000)
        cs.spend(150)
        cs.spend(50)
        assert cs.total_spent == 200


# ------------------------------------------------------------------ #
# Tests: Property System                                              #
# ------------------------------------------------------------------ #

class TestPropertySystem:
    def test_default_properties_populated(self):
        ps = PropertySystem()
        assert len(ps.available_properties) > 0

    def test_purchase_property(self):
        ps = PropertySystem()
        avail = ps.available_properties
        prop = avail[0]
        result = ps.purchase(prop.property_id, prop.purchase_price)
        assert result is not None
        assert prop.is_owned

    def test_cannot_buy_same_property_twice(self):
        ps = PropertySystem()
        prop = ps.available_properties[0]
        ps.purchase(prop.property_id, prop.purchase_price)
        result = ps.purchase(prop.property_id, prop.purchase_price)
        assert result is None

    def test_insufficient_funds(self):
        ps = PropertySystem()
        prop = ps.available_properties[0]
        result = ps.purchase(prop.property_id, 0)  # 0 balance
        assert result is None

    def test_owned_properties_list(self):
        ps = PropertySystem()
        prop = ps.available_properties[0]
        ps.purchase(prop.property_id, prop.purchase_price)
        assert len(ps.owned_properties) == 1

    def test_total_weekly_income(self):
        ps = PropertySystem()
        # Find a property with income
        for prop in ps.available_properties:
            if prop.weekly_income > 0:
                ps.purchase(prop.property_id, prop.purchase_price)
                assert ps.total_weekly_income == prop.weekly_income
                break

    def test_income_collected_on_timer(self):
        ps = PropertySystem()
        ps.INCOME_INTERVAL = 1.0  # 1 second for testing
        prop = ps.available_properties[0]
        if prop.weekly_income > 0:
            ps.purchase(prop.property_id, prop.purchase_price)
            income = ps.update(1.5)
            assert income >= 0

    def test_purchase_callback(self):
        called = []
        ps = PropertySystem()
        ps.on_purchase(lambda p: called.append(p))
        prop = ps.available_properties[0]
        ps.purchase(prop.property_id, prop.purchase_price)
        assert len(called) == 1


# ------------------------------------------------------------------ #
# Tests: Progression System                                           #
# ------------------------------------------------------------------ #

class TestProgressionSystem:
    def test_initial_level(self):
        ps = ProgressionSystem()
        assert ps.player_level == 1

    def test_grant_xp_levels_up(self):
        ps = ProgressionSystem()
        levels = ps.grant_xp(ps.XP_PER_LEVEL)
        assert levels >= 1
        assert ps.player_level >= 2

    def test_multiple_level_ups(self):
        ps = ProgressionSystem()
        ps.grant_xp(ps.XP_PER_LEVEL * 5)
        assert ps.player_level >= 3

    def test_default_skills_created(self):
        ps = ProgressionSystem()
        assert len(ps.unlocked_skills) > 0

    def test_skill_xp_levels_up_skill(self):
        ps = ProgressionSystem()
        skill = ps.get_skill("faster_reload")
        assert skill is not None
        assert skill.is_unlocked
        old_level = skill.level
        ps.grant_skill_xp("faster_reload", skill.xp_per_level * 2)
        assert skill.level > old_level

    def test_level_up_callback(self):
        levels = []
        ps = ProgressionSystem()
        ps.on_level_up(lambda lv: levels.append(lv))
        ps.grant_xp(ps.XP_PER_LEVEL)
        assert len(levels) >= 1

    def test_unlock_skill_with_prereq(self):
        ps = ProgressionSystem()
        skill_faster = ps.get_skill("faster_reload")
        skill_faster.level = 1  # Simulate having earned level 1
        result = ps.unlock_skill("improved_accuracy")
        assert result is True

    def test_locked_skill_no_xp(self):
        ps = ProgressionSystem()
        # improved_accuracy starts locked
        skill = ps.get_skill("improved_accuracy")
        if skill and not skill.is_unlocked:
            result = ps.grant_skill_xp("improved_accuracy", 10000)
            assert result == 0

    def test_xp_to_next_level(self):
        ps = ProgressionSystem()
        assert ps.xp_to_next_level > 0


# ------------------------------------------------------------------ #
# Tests: Save Manager                                                 #
# ------------------------------------------------------------------ #

class TestSaveManager:
    def setup_method(self):
        self.save_dir = tempfile.mkdtemp()
        self.manager = SaveManager(save_directory=self.save_dir)

    def teardown_method(self):
        shutil.rmtree(self.save_dir, ignore_errors=True)

    def test_slots_initialised(self):
        assert len(self.manager.all_slots) == SaveManager.MAX_SLOTS + 1

    def test_save_and_load(self):
        state = GameState(player_health=75.0, player_money=12345)
        self.manager.save(1, state, "Test Save")
        loaded = self.manager.load(1)
        assert loaded is not None
        assert loaded.player_health == pytest.approx(75.0)
        assert loaded.player_money == 12345

    def test_autosave(self):
        state = GameState(player_level=5)
        result = self.manager.autosave(state)
        assert result is True
        loaded = self.manager.load(SaveManager.AUTOSAVE_SLOT_ID)
        assert loaded is not None
        assert loaded.player_level == 5

    def test_load_empty_slot_returns_none(self):
        result = self.manager.load(3)  # Empty slot
        assert result is None

    def test_delete_slot(self):
        state = GameState()
        self.manager.save(2, state)
        self.manager.delete(2)
        result = self.manager.load(2)
        assert result is None

    def test_slot_metadata_after_save(self):
        state = GameState(player_level=10, play_time_seconds=3600.0)
        self.manager.save(1, state, "My Save")
        slot = self.manager.get_slot(1)
        assert slot is not None
        assert not slot.is_empty
        assert slot.player_level == 10

    def test_game_state_serialization(self):
        state = GameState(
            player_position={"x": 100.0, "y": 0.0, "z": 200.0},
            completed_missions=["m1", "m2"],
            inventory={"weapon": "pistol"},
        )
        d = state.to_dict()
        restored = GameState.from_dict(d)
        assert restored.player_position["x"] == pytest.approx(100.0)
        assert "m1" in restored.completed_missions

    def test_manual_slots_exclude_autosave(self):
        manual = self.manager.manual_slots
        assert all(not s.is_autosave for s in manual)


# ------------------------------------------------------------------ #
# Tests: Checkpoint System                                            #
# ------------------------------------------------------------------ #

class TestCheckpointSystem:
    def test_checkpoint_triggered(self):
        system = CheckpointSystem()
        cp = Checkpoint("cp1", (5.0, 0.0, 0.0), radius=3.0)
        system.add_checkpoint(cp)
        reached = system.update((5.0, 0.0, 0.0))
        assert len(reached) == 1
        assert reached[0] is cp

    def test_checkpoint_not_triggered_from_far(self):
        system = CheckpointSystem()
        cp = Checkpoint("cp1", (100.0, 0.0, 0.0), radius=3.0)
        system.add_checkpoint(cp)
        reached = system.update((0.0, 0.0, 0.0))
        assert len(reached) == 0

    def test_checkpoint_only_triggered_once(self):
        system = CheckpointSystem()
        cp = Checkpoint("cp1", (0.0, 0.0, 0.0), radius=3.0)
        system.add_checkpoint(cp)
        system.update((0.0, 0.0, 0.0))
        reached_again = system.update((0.0, 0.0, 0.0))
        assert len(reached_again) == 0

    def test_callback_on_reached(self):
        fired = []
        system = CheckpointSystem()
        cp = Checkpoint("cp1", (0.0, 0.0, 0.0), radius=5.0)
        system.add_checkpoint(cp)
        system.on_reached(lambda c: fired.append(c))
        system.update((1.0, 0.0, 0.0))
        assert len(fired) == 1

    def test_respawn_position(self):
        system = CheckpointSystem()
        cp = Checkpoint("cp1", (10.0, 0.0, 0.0), radius=5.0,
                         respawn_position=(10.0, 2.0, 0.0))
        system.add_checkpoint(cp)
        system.update((10.0, 0.0, 0.0))
        assert system.respawn_position == (10.0, 2.0, 0.0)

    def test_reset_checkpoints(self):
        system = CheckpointSystem()
        cp = Checkpoint("cp1", (0.0, 0.0, 0.0), radius=5.0)
        system.add_checkpoint(cp)
        system.update((0.0, 0.0, 0.0))
        assert cp.is_reached
        system.reset_all()
        assert not cp.is_reached

    def test_pending_count(self):
        system = CheckpointSystem()
        system.add_checkpoint(Checkpoint("cp1", (0.0, 0.0, 0.0), radius=100.0))
        system.add_checkpoint(Checkpoint("cp2", (50.0, 0.0, 0.0), radius=3.0))
        assert system.pending_count == 2
        system.update((0.0, 0.0, 0.0))
        assert system.pending_count == 1
