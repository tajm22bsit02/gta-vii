"""Weapon System - weapon firing, reloading, and projectile simulation."""

from __future__ import annotations
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple


class WeaponType(Enum):
    """Weapon classification."""

    PISTOL = auto()
    SMG = auto()
    ASSAULT_RIFLE = auto()
    SNIPER_RIFLE = auto()
    SHOTGUN = auto()
    RPG = auto()
    GRENADE_LAUNCHER = auto()
    MINIGUN = auto()
    MELEE = auto()
    THROWING_KNIFE = auto()


@dataclass
class WeaponStats:
    """Tunable parameters for a weapon type."""

    damage: float = 20.0
    fire_rate: float = 2.0       # rounds/second
    range_: float = 50.0         # effective range in metres
    spread: float = 2.0          # accuracy spread in degrees
    magazine_size: int = 12
    reload_time: float = 2.0     # seconds
    is_automatic: bool = False
    penetration: float = 0.0     # 0=none, 1=full wall penetration
    projectile_speed: float = 300.0  # m/s (0 = instant hitscan)
    splash_radius: float = 0.0   # 0 = no splash


@dataclass
class BulletTracer:
    """Active projectile in the world."""

    bullet_id: str
    origin: Tuple[float, float, float]
    direction: Tuple[float, float, float]
    speed: float
    damage: float
    max_range: float
    traveled: float = 0.0
    active: bool = True

    def update(self, delta_time: float) -> Tuple[float, float, float]:
        """Advance bullet position.

        Returns:
            Current world position.
        """
        self.traveled += self.speed * delta_time
        if self.traveled >= self.max_range:
            self.active = False
        dx, dy, dz = self.direction
        dist = self.traveled
        return (
            self.origin[0] + dx * dist,
            self.origin[1] + dy * dist,
            self.origin[2] + dz * dist,
        )


@dataclass
class Weapon:
    """A fully-configured weapon instance."""

    weapon_id: str
    weapon_type: WeaponType
    name: str
    stats: WeaponStats = field(default_factory=WeaponStats)
    current_ammo: int = field(init=False)
    reserved_ammo: int = 120
    is_reloading: bool = False
    reload_timer: float = 0.0
    fire_timer: float = 0.0       # cooldown between shots

    def __post_init__(self) -> None:
        self.current_ammo = self.stats.magazine_size

    @property
    def can_fire(self) -> bool:
        return (
            not self.is_reloading
            and self.fire_timer <= 0.0
            and self.current_ammo > 0
        )

    def update(self, delta_time: float) -> None:
        """Advance cooldown and reload timers."""
        if self.fire_timer > 0:
            self.fire_timer = max(0.0, self.fire_timer - delta_time)
        if self.is_reloading:
            self.reload_timer -= delta_time
            if self.reload_timer <= 0.0:
                self._finish_reload()

    def fire(self, origin: Tuple[float, float, float], aim_direction: Tuple[float, float, float]) -> Optional[BulletTracer]:
        """Attempt to fire the weapon.

        Args:
            origin: Muzzle world position.
            aim_direction: Normalised aim direction.

        Returns:
            BulletTracer if fired, None if unable to fire.
        """
        if not self.can_fire:
            return None

        self.current_ammo -= 1
        self.fire_timer = 1.0 / self.stats.fire_rate

        # Apply spread
        spread_rad = math.radians(self.stats.spread)
        dx = aim_direction[0] + random.uniform(-spread_rad, spread_rad)
        dy = aim_direction[1]
        dz = aim_direction[2] + random.uniform(-spread_rad, spread_rad)
        mag = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        direction = (dx / mag, dy / mag, dz / mag)

        bullet_id = f"bullet_{id(self)}_{self.current_ammo}"
        return BulletTracer(
            bullet_id=bullet_id,
            origin=origin,
            direction=direction,
            speed=self.stats.projectile_speed,
            damage=self.stats.damage,
            max_range=self.stats.range_,
        )

    def reload(self) -> bool:
        """Initiate a reload if ammo is available."""
        if self.is_reloading or self.reserved_ammo <= 0:
            return False
        self.is_reloading = True
        self.reload_timer = self.stats.reload_time
        return True

    def _finish_reload(self) -> None:
        needed = self.stats.magazine_size - self.current_ammo
        available = min(needed, self.reserved_ammo)
        self.current_ammo += available
        self.reserved_ammo -= available
        self.is_reloading = False


HitCallback = Callable[[BulletTracer, Tuple[float, float, float]], None]


class WeaponSystem:
    """Manages all active weapons and projectiles in the game world."""

    def __init__(self) -> None:
        self._weapons: Dict[str, Weapon] = {}
        self._bullets: Dict[str, BulletTracer] = {}
        self._hit_callbacks: List[HitCallback] = []
        self._bullet_counter: int = 0

    def register_weapon(self, weapon: Weapon) -> None:
        self._weapons[weapon.weapon_id] = weapon

    def fire_weapon(
        self,
        weapon_id: str,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
    ) -> Optional[BulletTracer]:
        """Fire a registered weapon and track the bullet."""
        weapon = self._weapons.get(weapon_id)
        if weapon is None:
            return None
        bullet = weapon.fire(origin, direction)
        if bullet:
            self._bullets[bullet.bullet_id] = bullet
        return bullet

    def update(self, delta_time: float) -> None:
        """Advance all weapon and bullet states."""
        for weapon in self._weapons.values():
            weapon.update(delta_time)

        expired = []
        for bid, bullet in self._bullets.items():
            pos = bullet.update(delta_time)
            if not bullet.active:
                expired.append(bid)
        for bid in expired:
            del self._bullets[bid]

    def add_hit_callback(self, callback: HitCallback) -> None:
        self._hit_callbacks.append(callback)

    @property
    def active_bullet_count(self) -> int:
        return len(self._bullets)

    # ------------------------------------------------------------------ #
    # Weapon catalogue                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_catalogue() -> Dict[str, Weapon]:
        """Return a catalogue of all available weapons."""
        return {
            "pistol": Weapon(
                "pistol", WeaponType.PISTOL, "Beretta M9",
                WeaponStats(damage=25, fire_rate=3, range_=40, magazine_size=15),
                reserved_ammo=90,
            ),
            "assault_rifle": Weapon(
                "assault_rifle", WeaponType.ASSAULT_RIFLE, "AK-47",
                WeaponStats(damage=35, fire_rate=10, range_=80, spread=3.0,
                            magazine_size=30, is_automatic=True, reload_time=2.5),
                reserved_ammo=180,
            ),
            "sniper": Weapon(
                "sniper", WeaponType.SNIPER_RIFLE, "L115A3",
                WeaponStats(damage=150, fire_rate=0.5, range_=500, spread=0.1,
                            magazine_size=5, reload_time=3.5),
                reserved_ammo=25,
            ),
            "shotgun": Weapon(
                "shotgun", WeaponType.SHOTGUN, "Remington 870",
                WeaponStats(damage=80, fire_rate=1.5, range_=20, spread=15.0,
                            magazine_size=8, reload_time=3.0),
                reserved_ammo=48,
            ),
            "rpg": Weapon(
                "rpg", WeaponType.RPG, "RPG-7",
                WeaponStats(damage=500, fire_rate=0.5, range_=200, splash_radius=8.0,
                            magazine_size=1, reload_time=5.0, projectile_speed=100.0),
                reserved_ammo=6,
            ),
        }

    def __repr__(self) -> str:
        return (
            f"WeaponSystem(weapons={len(self._weapons)}, "
            f"bullets={self.active_bullet_count})"
        )
