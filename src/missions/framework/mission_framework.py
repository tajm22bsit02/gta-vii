"""Mission Framework - story mission structure and scripting."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple


class MissionStatus(Enum):
    """Lifecycle states for a mission."""

    LOCKED = auto()       # Prerequisites not met
    AVAILABLE = auto()    # Can be started
    ACTIVE = auto()       # Currently in progress
    COMPLETED = auto()    # Successfully finished
    FAILED = auto()       # Failed and can be retried


class MissionType(Enum):
    """Classification of mission content."""

    STORY = auto()
    SIDE_MISSION = auto()
    HEIST = auto()
    RACE = auto()
    ASSASSINATION = auto()
    ROBBERY = auto()
    DELIVERY = auto()
    SURVIVAL = auto()


@dataclass
class MissionReward:
    """Rewards granted on mission completion."""

    money: int = 0
    experience: int = 0
    unlocked_missions: List[str] = field(default_factory=list)
    unlocked_items: List[str] = field(default_factory=list)


MissionCallback = Callable[["Mission"], None]


@dataclass
class MissionTrigger:
    """Defines the activation zone for a mission."""

    position: Tuple[float, float]
    radius: float = 5.0
    mission_id: str = ""

    def is_triggered(self, player_pos: Tuple[float, float]) -> bool:
        dx = player_pos[0] - self.position[0]
        dy = player_pos[1] - self.position[1]
        return (dx * dx + dy * dy) <= self.radius ** 2


class Mission(ABC):
    """Abstract base class for all game missions.

    Subclasses implement on_start, on_update, on_complete, and on_fail.
    """

    def __init__(
        self,
        mission_id: str,
        name: str,
        description: str,
        mission_type: MissionType = MissionType.STORY,
        reward: Optional[MissionReward] = None,
        prerequisites: Optional[List[str]] = None,
    ) -> None:
        self.mission_id: str = mission_id
        self.name: str = name
        self.description: str = description
        self.mission_type: MissionType = mission_type
        self.reward: MissionReward = reward or MissionReward()
        self.prerequisites: List[str] = prerequisites or []
        self.status: MissionStatus = MissionStatus.LOCKED
        self.elapsed_time: float = 0.0
        self.time_limit: Optional[float] = None
        self._complete_callbacks: List[MissionCallback] = []
        self._fail_callbacks: List[MissionCallback] = []

    def start(self) -> None:
        """Begin the mission."""
        self.status = MissionStatus.ACTIVE
        self.elapsed_time = 0.0
        self.on_start()

    def update(self, delta_time: float) -> None:
        """Advance mission logic."""
        if self.status != MissionStatus.ACTIVE:
            return
        self.elapsed_time += delta_time
        if self.time_limit is not None and self.elapsed_time >= self.time_limit:
            self.fail("Time limit exceeded")
            return
        self.on_update(delta_time)

    def complete(self) -> None:
        """Mark the mission as successfully completed."""
        self.status = MissionStatus.COMPLETED
        self.on_complete()
        for cb in self._complete_callbacks:
            cb(self)

    def fail(self, reason: str = "") -> None:
        """Mark the mission as failed."""
        self.status = MissionStatus.FAILED
        self.on_fail(reason)
        for cb in self._fail_callbacks:
            cb(self)

    def on_complete_callback(self, callback: MissionCallback) -> None:
        self._complete_callbacks.append(callback)

    def on_fail_callback(self, callback: MissionCallback) -> None:
        self._fail_callbacks.append(callback)

    @abstractmethod
    def on_start(self) -> None:
        """Called when the mission begins."""

    @abstractmethod
    def on_update(self, delta_time: float) -> None:
        """Per-frame mission logic."""

    @abstractmethod
    def on_complete(self) -> None:
        """Called on success."""

    def on_fail(self, reason: str) -> None:
        """Called on failure (optional override)."""

    def __repr__(self) -> str:
        return f"Mission({self.mission_id!r}, status={self.status.name})"


class MissionManager:
    """Tracks all missions and handles activation, completion, and rewards."""

    def __init__(self) -> None:
        self._missions: Dict[str, Mission] = {}
        self._active_mission: Optional[Mission] = None
        self._triggers: List[MissionTrigger] = []

    def register(self, mission: Mission) -> None:
        """Register a mission."""
        self._missions[mission.mission_id] = mission

    def unlock(self, mission_id: str) -> bool:
        """Unlock a mission if prerequisites are met."""
        mission = self._missions.get(mission_id)
        if mission is None:
            return False
        if mission.status != MissionStatus.LOCKED:
            return True
        for prereq in mission.prerequisites:
            prereq_mission = self._missions.get(prereq)
            if prereq_mission is None or prereq_mission.status != MissionStatus.COMPLETED:
                return False
        mission.status = MissionStatus.AVAILABLE
        return True

    def start_mission(self, mission_id: str) -> bool:
        """Start a mission by ID."""
        mission = self._missions.get(mission_id)
        if mission is None or mission.status != MissionStatus.AVAILABLE:
            return False
        if self._active_mission is not None:
            return False
        self._active_mission = mission
        mission.start()
        return True

    def update(self, delta_time: float) -> None:
        """Update the currently active mission."""
        if self._active_mission and self._active_mission.status == MissionStatus.ACTIVE:
            self._active_mission.update(delta_time)
            if self._active_mission.status in (
                MissionStatus.COMPLETED, MissionStatus.FAILED
            ):
                self._active_mission = None

    def add_trigger(self, trigger: MissionTrigger) -> None:
        """Add a mission activation trigger."""
        self._triggers.append(trigger)

    def check_triggers(self, player_pos: Tuple[float, float]) -> Optional[str]:
        """Check if player is in any trigger zone.

        Returns:
            Mission ID to start, or None.
        """
        for trigger in self._triggers:
            mission = self._missions.get(trigger.mission_id)
            if (
                mission
                and mission.status == MissionStatus.AVAILABLE
                and trigger.is_triggered(player_pos)
            ):
                return trigger.mission_id
        return None

    def get_available_missions(self) -> List[Mission]:
        return [m for m in self._missions.values() if m.status == MissionStatus.AVAILABLE]

    def get_completed_missions(self) -> List[Mission]:
        return [m for m in self._missions.values() if m.status == MissionStatus.COMPLETED]

    @property
    def active_mission(self) -> Optional[Mission]:
        return self._active_mission

    def __repr__(self) -> str:
        total = len(self._missions)
        completed = len(self.get_completed_missions())
        return f"MissionManager(total={total}, completed={completed}, active={self._active_mission})"
