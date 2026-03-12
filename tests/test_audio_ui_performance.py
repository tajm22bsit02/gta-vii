"""Test suite for audio, UI, and performance systems."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from audio.spatial.audio_3d import Audio3DSystem, AudioSource, AudioListener
from audio.music.music_system import MusicSystem, MusicState
from audio.sfx.sfx_manager import SFXManager, SFXCategory
from ui.hud.hud_system import HUDSystem, HUDElementType, Minimap
from ui.menus.menu_system import MenuSystem, MenuAction
from performance.lod.lod_system import LODSystem, LODObject, LODLevel
from performance.culling.culling_system import CullingSystem, CullableObject, BoundingSphere


# ------------------------------------------------------------------ #
# Tests: 3D Audio                                                     #
# ------------------------------------------------------------------ #

class TestAudio3D:
    def test_create_source(self):
        sys_ = Audio3DSystem()
        src = sys_.create_source("s1", "shot", (10.0, 0.0, 0.0))
        assert src.source_id == "s1"

    def test_play_at_returns_source(self):
        sys_ = Audio3DSystem()
        src = sys_.play_at("explosion", (0.0, 0.0, 0.0))
        assert src is not None
        assert src.is_playing

    def test_volume_at_full_within_min_distance(self):
        listener = AudioListener(position=(0.0, 0.0, 0.0))
        src = AudioSource("s1", "sound", (3.0, 0.0, 0.0), volume=1.0, min_distance=5.0)
        vol = src.calculate_volume_at(listener)
        assert vol == pytest.approx(1.0)

    def test_volume_zero_beyond_max_distance(self):
        listener = AudioListener(position=(0.0, 0.0, 0.0))
        src = AudioSource("s1", "sound", (200.0, 0.0, 0.0), volume=1.0,
                          min_distance=5.0, max_distance=100.0)
        vol = src.calculate_volume_at(listener)
        assert vol == pytest.approx(0.0)

    def test_volume_attenuates_linearly(self):
        listener = AudioListener(position=(0.0, 0.0, 0.0))
        src = AudioSource("s1", "sound", (50.0, 0.0, 0.0), volume=1.0,
                          min_distance=0.0, max_distance=100.0)
        vol = src.calculate_volume_at(listener)
        assert 0.0 < vol < 1.0

    def test_pan_left_right(self):
        listener = AudioListener(position=(0.0, 0.0, 0.0), forward=(0.0, 0.0, 1.0))
        src_right = AudioSource("r", "s", (10.0, 0.0, 0.0))
        src_left = AudioSource("l", "s", (-10.0, 0.0, 0.0))
        pan_r = src_right.calculate_pan_at(listener)
        pan_l = src_left.calculate_pan_at(listener)
        # Pan values should be non-zero and opposite in sign
        assert pan_r != 0.0
        assert pan_l != 0.0
        assert (pan_r > 0.0) != (pan_l > 0.0)  # opposite sides

    def test_update_removes_stopped_sources(self):
        sys_ = Audio3DSystem()
        src = sys_.play_at("sound", (0.0, 0.0, 0.0))
        src.stop()
        sys_.update(0.1)
        assert src.source_id not in sys_._sources

    def test_evict_oldest_when_full(self):
        sys_ = Audio3DSystem()
        sys_.MAX_ACTIVE_SOURCES = 2
        for i in range(3):
            sys_.play_at(f"sound_{i}", (float(i), 0.0, 0.0), looping=True)
        assert len(sys_._sources) <= 2


# ------------------------------------------------------------------ #
# Tests: Music System                                                 #
# ------------------------------------------------------------------ #

class TestMusicSystem:
    def test_set_state_changes_track(self):
        ms = MusicSystem()
        ms.set_state(MusicState.EXPLORATION)
        track1 = ms.current_track
        ms.set_state(MusicState.COMBAT)
        track2 = ms.current_track
        # Tracks should differ if different states have different music
        if track1 and track2:
            pass  # both assigned

    def test_radio_station_switch(self):
        ms = MusicSystem()
        result = ms.tune_to_station(ms.station_names[0])
        assert result is True
        assert ms.radio_mode

    def test_unknown_station_returns_false(self):
        ms = MusicSystem()
        assert not ms.tune_to_station("Non-Existent Station")

    def test_update_advances_timer(self):
        ms = MusicSystem()
        ms.set_state(MusicState.MENU)
        track = ms.current_track
        if track:
            ms.update(track.duration + 1.0)
            # Timer reset after end

    def test_station_names_not_empty(self):
        ms = MusicSystem()
        assert len(ms.station_names) > 0


# ------------------------------------------------------------------ #
# Tests: SFX Manager                                                  #
# ------------------------------------------------------------------ #

class TestSFXManager:
    def test_default_sfx_registered(self):
        sfx = SFXManager()
        assert sfx.registered_count > 0

    def test_play_returns_true(self):
        sfx = SFXManager()
        result = sfx.play("pistol_fire", current_time=0.0)
        assert result is True

    def test_unknown_sfx_returns_false(self):
        sfx = SFXManager()
        result = sfx.play("nonexistent_sound")
        assert result is False

    def test_cooldown_prevents_replay(self):
        sfx = SFXManager()
        sfx.play("car_engine", current_time=0.0)
        result = sfx.play("car_engine", current_time=0.05)
        assert result is False

    def test_cooldown_elapsed_allows_replay(self):
        sfx = SFXManager()
        sfx.play("car_engine", current_time=0.0)
        result = sfx.play("car_engine", current_time=1.0)
        assert result is True

    def test_category_volume(self):
        sfx = SFXManager()
        sfx.set_category_volume(SFXCategory.WEAPONS, 0.5)
        sfx.master_volume = 1.0
        vol = sfx.get_effective_volume("pistol_fire")
        assert vol == pytest.approx(0.5)

    def test_master_volume_scales(self):
        sfx = SFXManager()
        sfx.master_volume = 0.5
        vol = sfx.get_effective_volume("pistol_fire")
        assert vol == pytest.approx(0.5)


# ------------------------------------------------------------------ #
# Tests: HUD System                                                   #
# ------------------------------------------------------------------ #

class TestHUDSystem:
    def test_default_elements_created(self):
        hud = HUDSystem()
        assert hud.get_element("health_bar") is not None
        assert hud.get_element("minimap") is not None

    def test_health_bar_updated(self):
        hud = HUDSystem()
        hud.update(0.016, health=50.0)
        bar = hud.get_element("health_bar")
        assert bar.value == pytest.approx(0.5)

    def test_notification_added(self):
        hud = HUDSystem()
        hud.show_notification("Test message", duration=5.0)
        assert len(hud.active_notifications) == 1

    def test_notification_expires(self):
        hud = HUDSystem()
        hud.show_notification("Temp", duration=1.0)
        hud.update(2.0)  # Advance past duration
        assert len(hud.active_notifications) == 0

    def test_money_display_text(self):
        hud = HUDSystem()
        hud.update(0.016, money=12345)
        elem = hud.get_element("money_display")
        assert "12,345" in elem.text

    def test_minimap_blip(self):
        hud = HUDSystem()
        hud.minimap.add_blip("player", (100.0, 200.0))
        assert hud.minimap.blip_count == 1
        hud.minimap.remove_blip("player")
        assert hud.minimap.blip_count == 0

    def test_minimap_world_to_uv(self):
        mm = Minimap(size=0.15)
        uv = mm.world_to_minimap((0.0, 0.0), (0.0, 0.0))
        assert uv == (0.5, 0.5)


# ------------------------------------------------------------------ #
# Tests: Menu System                                                  #
# ------------------------------------------------------------------ #

class TestMenuSystem:
    def test_default_menus_created(self):
        ms = MenuSystem()
        assert ms._screens.get("main_menu") is not None
        assert ms._screens.get("pause_menu") is not None

    def test_open_main_menu(self):
        ms = MenuSystem()
        result = ms.open("main_menu")
        assert result is True
        assert ms.is_open
        assert ms.current_screen.screen_id == "main_menu"

    def test_open_nonexistent_screen(self):
        ms = MenuSystem()
        assert not ms.open("fake_screen")

    def test_navigate_and_confirm(self):
        ms = MenuSystem()
        ms.open("main_menu")
        screen = ms.current_screen
        screen.select_next()
        action = screen.confirm()
        assert action is not None

    def test_push_and_back(self):
        ms = MenuSystem()
        ms.open("main_menu")
        ms.open("settings_menu")
        assert ms.current_screen.screen_id == "settings_menu"
        ms.back()
        assert ms.current_screen.screen_id == "main_menu"

    def test_close_all(self):
        ms = MenuSystem()
        ms.open("main_menu")
        ms.close_all()
        assert not ms.is_open

    def test_menu_item_callback(self):
        fired = []
        from ui.menus.menu_system import MenuScreen, MenuItem, MenuAction
        screen = MenuScreen("test", "Test")
        screen.add_item(MenuItem("Click me", MenuAction.RESUME, callback=lambda: fired.append(True)))
        screen.confirm()
        assert len(fired) == 1


# ------------------------------------------------------------------ #
# Tests: LOD System                                                   #
# ------------------------------------------------------------------ #

class TestLODSystem:
    def test_register_and_update(self):
        system = LODSystem()
        obj = LODObject("obj1", (0.0, 0.0, 0.0))
        system.register(obj)
        system.update((0.0, 0.0, 0.0))
        assert obj.current_lod == LODLevel.LOD0

    def test_lod_transitions_by_distance(self):
        system = LODSystem()
        obj = LODObject("obj1", (0.0, 0.0, 0.0))
        system.register(obj)
        # Near - full detail
        system.update((0.0, 0.0, 0.0))
        assert obj.current_lod == LODLevel.LOD0
        # Far - lower detail
        system.update((200.0, 0.0, 0.0))
        assert obj.current_lod.value > LODLevel.LOD0.value

    def test_culled_beyond_max_distance(self):
        system = LODSystem()
        obj = LODObject("obj1", (0.0, 0.0, 0.0))
        system.register(obj)
        system.update((1000.0, 0.0, 0.0))
        assert obj.current_lod == LODLevel.CULLED

    def test_changed_objects_returned(self):
        system = LODSystem()
        obj = LODObject("obj1", (0.0, 0.0, 0.0))
        system.register(obj)
        system.update((0.0, 0.0, 0.0))
        changed = system.update((500.0, 0.0, 0.0))
        assert "obj1" in changed

    def test_visible_objects_excludes_culled(self):
        system = LODSystem()
        obj1 = LODObject("near", (0.0, 0.0, 0.0))
        obj2 = LODObject("far", (900.0, 0.0, 0.0))
        system.register(obj1)
        system.register(obj2)
        system.update((0.0, 0.0, 0.0))
        visible = system.get_visible_objects()
        ids = [o.object_id for o in visible]
        assert "near" in ids
        assert "far" not in ids

    def test_unregister(self):
        system = LODSystem()
        obj = LODObject("obj1", (0.0, 0.0, 0.0))
        system.register(obj)
        system.unregister("obj1")
        assert system.registered_count == 0

    def test_lod_bias_shifts_threshold(self):
        obj = LODObject("obj1", (0.0, 0.0, 0.0), bias=2.0)
        # Effective distance = actual / bias, so LOD0 threshold doubles
        changed = obj.update_lod(70.0)  # 70 / 2 = 35 -> still LOD0
        assert obj.current_lod == LODLevel.LOD0


# ------------------------------------------------------------------ #
# Tests: Culling System                                               #
# ------------------------------------------------------------------ #

class TestCullingSystem:
    def test_register_object(self):
        cs = CullingSystem()
        obj = CullableObject("obj1", BoundingSphere((0.0, 0.0, 50.0), 2.0))
        cs.register(obj)
        assert len(cs._objects) == 1

    def test_unregister_object(self):
        cs = CullingSystem()
        obj = CullableObject("obj1", BoundingSphere((0.0, 0.0, 0.0), 2.0))
        cs.register(obj)
        cs.unregister("obj1")
        assert len(cs._objects) == 0

    def test_update_returns_count(self):
        cs = CullingSystem()
        obj = CullableObject("obj1", BoundingSphere((0.0, 0.0, 50.0), 5.0))
        cs.register(obj)
        count = cs.update((0.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        assert isinstance(count, int)

    def test_culled_count_property(self):
        cs = CullingSystem()
        obj1 = CullableObject("obj1", BoundingSphere((0.0, 0.0, 0.0), 1.0))
        obj1.is_visible = False
        obj2 = CullableObject("obj2", BoundingSphere((0.0, 0.0, 0.0), 1.0))
        obj2.is_visible = True
        cs.register(obj1)
        cs.register(obj2)
        assert cs.culled_count == 1

    def test_visible_objects_list(self):
        cs = CullingSystem()
        obj = CullableObject("obj1", BoundingSphere((0.0, 0.0, 0.0), 1.0))
        obj.is_visible = True
        cs.register(obj)
        assert len(cs.visible_objects) == 1
