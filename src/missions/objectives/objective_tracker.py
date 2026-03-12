"""Objective Tracker - mission objective management and progress tracking."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional


class ObjectiveType(Enum):
    """Types of mission objectives."""

    REACH_LOCATION = auto()
    ELIMINATE_TARGET = auto()
    COLLECT_ITEM = auto()
    DELIVER_ITEM = auto()
    PROTECT_TARGET = auto()
    ESCAPE_AREA = auto()
    SURVIVE_TIMER = auto()
    HACK_TERMINAL = auto()
    INTERROGATE_NPC = auto()
    STEAL_VEHICLE = auto()
    TAKE_PHOTO = auto()


class ObjectiveStatus(Enum):
    """Lifecycle of an objective."""

    PENDING = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()


@dataclass
class Objective:
    """A single trackable mission objective."""

    objective_id: str
    objective_type: ObjectiveType
    description: str
    target_value: float = 1.0      # e.g. required count
    current_value: float = 0.0
    is_optional: bool = False
    status: ObjectiveStatus = ObjectiveStatus.PENDING
    hint: str = ""
    on_complete: Optional[Callable[["Objective"], None]] = field(default=None, repr=False)

    @property
    def progress_percentage(self) -> float:
        if self.target_value <= 0:
            return 100.0
        return min(100.0, (self.current_value / self.target_value) * 100.0)

    @property
    def is_done(self) -> bool:
        return self.status in (
            ObjectiveStatus.COMPLETED,
            ObjectiveStatus.FAILED,
            ObjectiveStatus.SKIPPED,
        )

    def advance(self, amount: float = 1.0) -> bool:
        """Increment progress towards the target.

        Returns:
            True if this advance completed the objective.
        """
        if self.is_done or self.status == ObjectiveStatus.PENDING:
            return False
        self.current_value = min(self.target_value, self.current_value + amount)
        if self.current_value >= self.target_value:
            self.mark_complete()
            return True
        return False

    def mark_complete(self) -> None:
        """Directly mark as completed."""
        self.status = ObjectiveStatus.COMPLETED
        if self.on_complete:
            self.on_complete(self)

    def mark_failed(self) -> None:
        """Directly mark as failed."""
        self.status = ObjectiveStatus.FAILED

    def activate(self) -> None:
        """Start tracking this objective."""
        self.status = ObjectiveStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"Objective({self.description!r}, "
            f"{self.current_value:.0f}/{self.target_value:.0f}, "
            f"{self.status.name})"
        )


class ObjectiveTracker:
    """Manages a list of objectives for the current mission.

    Objectives are tracked sequentially or in parallel depending on
    the mission design. Progress is exposed to the HUD.
    """

    def __init__(self, sequential: bool = True) -> None:
        self._objectives: List[Objective] = []
        self.sequential: bool = sequential
        self._completed_callbacks: List[Callable[[], None]] = []

    def add_objective(self, objective: Objective) -> None:
        """Append an objective to the tracker."""
        self._objectives.append(objective)
        if not self.sequential or len(self._objectives) == 1:
            objective.activate()

    def update(self) -> None:
        """Advance sequential activation and check overall completion."""
        if self.sequential:
            for obj in self._objectives:
                if obj.status == ObjectiveStatus.PENDING:
                    # Check if the previous one is done
                    idx = self._objectives.index(obj)
                    if idx == 0 or self._objectives[idx - 1].status == ObjectiveStatus.COMPLETED:
                        obj.activate()
                    break

        if self.all_required_complete:
            for cb in self._completed_callbacks:
                cb()

    def on_all_complete(self, callback: Callable[[], None]) -> None:
        """Register a callback for when all required objectives are done."""
        self._completed_callbacks.append(callback)

    def get_active_objectives(self) -> List[Objective]:
        return [o for o in self._objectives if o.status == ObjectiveStatus.ACTIVE]

    def get_objective(self, objective_id: str) -> Optional[Objective]:
        for obj in self._objectives:
            if obj.objective_id == objective_id:
                return obj
        return None

    @property
    def all_required_complete(self) -> bool:
        return all(
            o.status == ObjectiveStatus.COMPLETED
            for o in self._objectives
            if not o.is_optional
        )

    @property
    def has_failed_objective(self) -> bool:
        return any(o.status == ObjectiveStatus.FAILED for o in self._objectives)

    @property
    def progress_summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {s.name: 0 for s in ObjectiveStatus}
        for obj in self._objectives:
            counts[obj.status.name] += 1
        return counts

    def __repr__(self) -> str:
        summary = self.progress_summary
        return (
            f"ObjectiveTracker("
            f"total={len(self._objectives)}, "
            f"active={summary.get('ACTIVE', 0)}, "
            f"completed={summary.get('COMPLETED', 0)})"
        )
