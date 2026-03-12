"""SFX Manager - sound effects registry and playback."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class SFXCategory(Enum):
    """Sound effect categories for volume routing."""

    WEAPONS = auto()
    VEHICLES = auto()
    ENVIRONMENT = auto()
    UI = auto()
    CHARACTER = auto()
    EXPLOSIONS = auto()


@dataclass
class SoundEffect:
    """Metadata for a registered sound effect."""

    sfx_id: str
    name: str
    category: SFXCategory
    file_path: str
    volume: float = 1.0
    pitch_min: float = 0.9
    pitch_max: float = 1.1
    cooldown: float = 0.0     # minimum seconds between repeats


class SFXManager:
    """Sound effect registry and priority-based playback."""

    MAX_CONCURRENT_SFX: int = 32

    def __init__(self) -> None:
        self._registry: Dict[str, SoundEffect] = {}
        self._active: Dict[str, float] = {}  # sfx_id -> last_played_time
        self._category_volumes: Dict[SFXCategory, float] = {
            cat: 1.0 for cat in SFXCategory
        }
        self.master_volume: float = 1.0
        self._play_counter: int = 0
        self._populate_defaults()

    def _populate_defaults(self) -> None:
        """Register default game sound effects."""
        defaults = [
            SoundEffect("pistol_fire", "Pistol Shot", SFXCategory.WEAPONS, "sfx/weapons/pistol.wav"),
            SoundEffect("rifle_fire", "Rifle Shot", SFXCategory.WEAPONS, "sfx/weapons/rifle.wav"),
            SoundEffect("explosion_small", "Small Explosion", SFXCategory.EXPLOSIONS, "sfx/explosion_small.wav"),
            SoundEffect("explosion_large", "Large Explosion", SFXCategory.EXPLOSIONS, "sfx/explosion_large.wav", volume=1.0),
            SoundEffect("car_engine", "Car Engine", SFXCategory.VEHICLES, "sfx/vehicles/car_engine.wav", cooldown=0.1),
            SoundEffect("car_screech", "Tyre Screech", SFXCategory.VEHICLES, "sfx/vehicles/screech.wav"),
            SoundEffect("car_crash", "Car Crash", SFXCategory.VEHICLES, "sfx/vehicles/crash.wav"),
            SoundEffect("footstep_concrete", "Footstep (Concrete)", SFXCategory.CHARACTER, "sfx/footstep_concrete.wav", cooldown=0.3),
            SoundEffect("footstep_grass", "Footstep (Grass)", SFXCategory.CHARACTER, "sfx/footstep_grass.wav", cooldown=0.3),
            SoundEffect("menu_click", "Menu Click", SFXCategory.UI, "sfx/ui/click.wav"),
            SoundEffect("menu_confirm", "Menu Confirm", SFXCategory.UI, "sfx/ui/confirm.wav"),
            SoundEffect("pickup_item", "Item Pickup", SFXCategory.CHARACTER, "sfx/pickup.wav"),
            SoundEffect("rain_ambient", "Rain Ambience", SFXCategory.ENVIRONMENT, "sfx/environment/rain.wav"),
        ]
        for sfx in defaults:
            self.register(sfx)

    def register(self, sfx: SoundEffect) -> None:
        """Register a sound effect."""
        self._registry[sfx.sfx_id] = sfx

    def play(self, sfx_id: str, current_time: float = 0.0) -> bool:
        """Request playback of a sound effect.

        Respects the cooldown and concurrent limit.

        Args:
            sfx_id: The sound effect ID to play.
            current_time: Current game time for cooldown tracking.

        Returns:
            True if the sound will be played.
        """
        sfx = self._registry.get(sfx_id)
        if sfx is None:
            return False

        last_played = self._active.get(sfx_id, -9999.0)
        if current_time - last_played < sfx.cooldown:
            return False

        if len(self._active) >= self.MAX_CONCURRENT_SFX:
            oldest = min(self._active, key=lambda k: self._active[k])
            del self._active[oldest]

        self._active[sfx_id] = current_time
        self._play_counter += 1
        return True

    def set_category_volume(self, category: SFXCategory, volume: float) -> None:
        self._category_volumes[category] = max(0.0, min(1.0, volume))

    def get_effective_volume(self, sfx_id: str) -> float:
        """Return the effective playback volume for an sfx."""
        sfx = self._registry.get(sfx_id)
        if sfx is None:
            return 0.0
        category_vol = self._category_volumes.get(sfx.category, 1.0)
        return sfx.volume * category_vol * self.master_volume

    @property
    def registered_count(self) -> int:
        return len(self._registry)

    def __repr__(self) -> str:
        return (
            f"SFXManager("
            f"registered={self.registered_count}, "
            f"played={self._play_counter})"
        )
