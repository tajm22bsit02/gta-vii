"""HUD System - in-game heads-up display elements."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class HUDElementType(Enum):
    """Types of HUD elements."""

    HEALTH_BAR = auto()
    ARMOUR_BAR = auto()
    STAMINA_BAR = auto()
    MINIMAP = auto()
    WANTED_STARS = auto()
    MONEY_DISPLAY = auto()
    AMMO_DISPLAY = auto()
    MISSION_OBJECTIVE = auto()
    NOTIFICATION = auto()
    WAYPOINT_ARROW = auto()
    SPEEDOMETER = auto()
    CROSSHAIR = auto()


@dataclass
class HUDElement:
    """A single element drawn on the HUD."""

    element_id: str
    element_type: HUDElementType
    position: Tuple[float, float]    # screen percentage (0.0-1.0)
    visible: bool = True
    value: float = 1.0               # generic normalised value (0.0-1.0)
    text: str = ""
    color: Tuple[int, int, int, int] = (255, 255, 255, 255)
    size: Tuple[float, float] = (0.1, 0.02)

    def update_value(self, new_value: float) -> None:
        self.value = max(0.0, min(1.0, new_value))


@dataclass
class Notification:
    """A temporary on-screen notification."""

    message: str
    duration: float = 5.0
    color: Tuple[int, int, int] = (255, 215, 0)
    elapsed: float = 0.0

    @property
    def is_expired(self) -> bool:
        return self.elapsed >= self.duration

    @property
    def alpha(self) -> float:
        """Fade out in the last second."""
        remaining = self.duration - self.elapsed
        return min(1.0, remaining)


class Minimap:
    """Mini-map that tracks player position and points of interest."""

    def __init__(self, size: float = 0.15) -> None:
        self.size: float = size
        self.zoom: float = 100.0       # world units visible per minimap edge
        self._blips: Dict[str, dict] = {}

    def add_blip(
        self,
        blip_id: str,
        position: Tuple[float, float],
        color: Tuple[int, int, int] = (255, 255, 0),
        label: str = "",
        blip_type: str = "default",
    ) -> None:
        """Add a map blip."""
        self._blips[blip_id] = {
            "position": position,
            "color": color,
            "label": label,
            "type": blip_type,
        }

    def remove_blip(self, blip_id: str) -> None:
        self._blips.pop(blip_id, None)

    def world_to_minimap(
        self,
        world_pos: Tuple[float, float],
        player_pos: Tuple[float, float],
    ) -> Tuple[float, float]:
        """Convert a world position to minimap UV coordinates."""
        dx = (world_pos[0] - player_pos[0]) / self.zoom
        dy = (world_pos[1] - player_pos[1]) / self.zoom
        return (0.5 + dx, 0.5 - dy)

    @property
    def blip_count(self) -> int:
        return len(self._blips)


class HUDSystem:
    """Manages all HUD elements and notifications."""

    def __init__(self, screen_width: int = 1920, screen_height: int = 1080) -> None:
        self.screen_width = screen_width
        self.screen_height = screen_height
        self._elements: Dict[str, HUDElement] = {}
        self._notifications: List[Notification] = []
        self.minimap: Minimap = Minimap()
        self.visible: bool = True
        self._setup_default_elements()

    def _setup_default_elements(self) -> None:
        """Create the standard HUD layout."""
        defaults = [
            HUDElement("health_bar", HUDElementType.HEALTH_BAR, (0.02, 0.92)),
            HUDElement("armour_bar", HUDElementType.ARMOUR_BAR, (0.02, 0.95)),
            HUDElement("stamina_bar", HUDElementType.STAMINA_BAR, (0.02, 0.89)),
            HUDElement("minimap", HUDElementType.MINIMAP, (0.02, 0.72)),
            HUDElement("wanted_stars", HUDElementType.WANTED_STARS, (0.85, 0.05)),
            HUDElement("money_display", HUDElementType.MONEY_DISPLAY, (0.85, 0.02)),
            HUDElement("ammo_display", HUDElementType.AMMO_DISPLAY, (0.90, 0.92)),
            HUDElement("crosshair", HUDElementType.CROSSHAIR, (0.5, 0.5)),
            HUDElement("speedometer", HUDElementType.SPEEDOMETER, (0.75, 0.88)),
        ]
        for elem in defaults:
            self._elements[elem.element_id] = elem

    def update(
        self,
        delta_time: float,
        health: float = 1.0,
        armour: float = 0.0,
        stamina: float = 1.0,
        money: int = 0,
        ammo: int = 0,
        speed_kmh: float = 0.0,
        wanted_level: int = 0,
    ) -> None:
        """Refresh all HUD element values."""
        updates = {
            "health_bar": health / 100.0,
            "armour_bar": armour / 100.0,
            "stamina_bar": stamina / 100.0,
            "speedometer": min(1.0, speed_kmh / 300.0),
            "wanted_stars": wanted_level / 5.0,
        }
        for elem_id, value in updates.items():
            if elem_id in self._elements:
                self._elements[elem_id].update_value(value)

        money_elem = self._elements.get("money_display")
        if money_elem:
            money_elem.text = f"${money:,}"

        ammo_elem = self._elements.get("ammo_display")
        if ammo_elem:
            ammo_elem.text = str(ammo)

        # Advance notification timers
        for notif in self._notifications:
            notif.elapsed += delta_time
        self._notifications = [n for n in self._notifications if not n.is_expired]

    def show_notification(self, message: str, duration: float = 5.0) -> None:
        """Display a temporary on-screen message."""
        self._notifications.append(Notification(message=message, duration=duration))

    def get_element(self, element_id: str) -> Optional[HUDElement]:
        return self._elements.get(element_id)

    @property
    def active_notifications(self) -> List[Notification]:
        return [n for n in self._notifications if not n.is_expired]

    def __repr__(self) -> str:
        return (
            f"HUDSystem("
            f"elements={len(self._elements)}, "
            f"notifications={len(self.active_notifications)})"
        )
