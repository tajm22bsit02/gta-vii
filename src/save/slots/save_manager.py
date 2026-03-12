"""Save Manager - game state persistence and multiple save slots."""

from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class GameState:
    """A serialisable snapshot of the entire game state."""

    player_position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    player_health: float = 100.0
    player_armour: float = 0.0
    player_money: int = 500
    player_level: int = 1
    player_xp: int = 0
    wanted_level: int = 0
    current_mission: Optional[str] = None
    completed_missions: List[str] = field(default_factory=list)
    owned_properties: List[str] = field(default_factory=list)
    inventory: Dict[str, Any] = field(default_factory=dict)
    play_time_seconds: float = 0.0
    game_time_hour: float = 12.0
    weather_condition: str = "CLEAR"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GameState":
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


@dataclass
class SaveSlot:
    """Metadata for a single save slot."""

    slot_id: int
    display_name: str
    save_path: str
    timestamp: str = ""
    play_time_seconds: float = 0.0
    player_level: int = 1
    location_name: str = "Downtown"
    is_autosave: bool = False
    state: Optional[GameState] = field(default=None, repr=False)

    @property
    def is_empty(self) -> bool:
        return self.timestamp == ""

    @property
    def formatted_play_time(self) -> str:
        hours = int(self.play_time_seconds // 3600)
        minutes = int((self.play_time_seconds % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"

    def __repr__(self) -> str:
        if self.is_empty:
            return f"SaveSlot(id={self.slot_id}, empty)"
        return (
            f"SaveSlot(id={self.slot_id}, "
            f"'{self.display_name}', "
            f"lv={self.player_level}, "
            f"time={self.formatted_play_time})"
        )


class SaveManager:
    """Manages reading/writing game state to disk.

    Supports multiple save slots (default 5) plus an autosave slot.
    State is stored as JSON for human readability and easy debugging.
    """

    MAX_SLOTS: int = 5
    AUTOSAVE_SLOT_ID: int = 0

    def __init__(self, save_directory: str = "saves") -> None:
        self.save_directory: str = save_directory
        self._slots: Dict[int, SaveSlot] = {}
        self._ensure_save_dir()
        self._init_slots()

    def _ensure_save_dir(self) -> None:
        os.makedirs(self.save_directory, exist_ok=True)

    def _init_slots(self) -> None:
        """Initialise slot metadata from disk (or create empty slots)."""
        for slot_id in range(self.MAX_SLOTS + 1):  # 0 = autosave
            save_path = os.path.join(self.save_directory, f"save_{slot_id:02d}.json")
            is_auto = slot_id == self.AUTOSAVE_SLOT_ID
            name = "Autosave" if is_auto else f"Save {slot_id}"
            slot = SaveSlot(
                slot_id=slot_id,
                display_name=name,
                save_path=save_path,
                is_autosave=is_auto,
            )
            if os.path.exists(save_path):
                try:
                    self._load_slot_metadata(slot, save_path)
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
            self._slots[slot_id] = slot

    def _load_slot_metadata(self, slot: SaveSlot, path: str) -> None:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        slot.timestamp = data.get("timestamp", "")
        slot.play_time_seconds = data.get("state", {}).get("play_time_seconds", 0.0)
        slot.player_level = data.get("state", {}).get("player_level", 1)

    def save(self, slot_id: int, state: GameState, display_name: str = "") -> bool:
        """Write game state to a slot.

        Args:
            slot_id: Slot index (0 = autosave, 1-5 = manual).
            state: The game state to persist.
            display_name: Optional custom slot name.

        Returns:
            True on success, False on error.
        """
        slot = self._slots.get(slot_id)
        if slot is None:
            return False

        timestamp = datetime.now().isoformat()
        if display_name:
            slot.display_name = display_name
        slot.timestamp = timestamp
        slot.play_time_seconds = state.play_time_seconds
        slot.player_level = state.player_level
        slot.state = state

        payload = {
            "timestamp": timestamp,
            "slot_id": slot_id,
            "display_name": slot.display_name,
            "state": state.to_dict(),
        }
        try:
            with open(slot.save_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
            return True
        except OSError:
            return False

    def load(self, slot_id: int) -> Optional[GameState]:
        """Load game state from a slot.

        Returns:
            GameState if successful, None if empty or error.
        """
        slot = self._slots.get(slot_id)
        if slot is None or slot.is_empty:
            return None
        try:
            with open(slot.save_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            state = GameState.from_dict(data.get("state", {}))
            slot.state = state
            return state
        except (OSError, json.JSONDecodeError, KeyError):
            return None

    def delete(self, slot_id: int) -> bool:
        """Delete a save slot."""
        slot = self._slots.get(slot_id)
        if slot is None:
            return False
        try:
            if os.path.exists(slot.save_path):
                os.remove(slot.save_path)
            slot.timestamp = ""
            slot.state = None
            return True
        except OSError:
            return False

    def autosave(self, state: GameState) -> bool:
        """Write an autosave."""
        return self.save(self.AUTOSAVE_SLOT_ID, state)

    def get_slot(self, slot_id: int) -> Optional[SaveSlot]:
        return self._slots.get(slot_id)

    @property
    def all_slots(self) -> List[SaveSlot]:
        return [self._slots[i] for i in sorted(self._slots)]

    @property
    def manual_slots(self) -> List[SaveSlot]:
        return [s for s in self.all_slots if not s.is_autosave]

    def __repr__(self) -> str:
        filled = sum(1 for s in self._slots.values() if not s.is_empty)
        return f"SaveManager(slots={len(self._slots)}, filled={filled})"
