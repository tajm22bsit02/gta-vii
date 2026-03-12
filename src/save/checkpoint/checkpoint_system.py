"""Checkpoint System - in-mission checkpoints and autosave triggers."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple


@dataclass
class Checkpoint:
    """A positional checkpoint within a mission or the open world."""

    checkpoint_id: str
    position: Tuple[float, float, float]
    radius: float = 3.0
    mission_id: Optional[str] = None
    is_reached: bool = False
    respawn_position: Optional[Tuple[float, float, float]] = None
    label: str = ""

    def check_player(self, player_position: Tuple[float, float, float]) -> bool:
        """Return True if the player has just reached this checkpoint."""
        if self.is_reached:
            return False
        dist = math.sqrt(
            (player_position[0] - self.position[0]) ** 2
            + (player_position[1] - self.position[1]) ** 2
            + (player_position[2] - self.position[2]) ** 2
        )
        if dist <= self.radius:
            self.is_reached = True
            return True
        return False

    def reset(self) -> None:
        """Allow this checkpoint to be reached again."""
        self.is_reached = False


CheckpointReachedCallback = Callable[[Checkpoint], None]


class CheckpointSystem:
    """Tracks and manages checkpoints across all active missions.

    Fires callbacks when checkpoints are reached and determines the
    last valid respawn position for the player.
    """

    def __init__(self) -> None:
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._reached_callbacks: List[CheckpointReachedCallback] = []
        self._last_checkpoint: Optional[Checkpoint] = None

    def add_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Register a checkpoint."""
        self._checkpoints[checkpoint.checkpoint_id] = checkpoint

    def remove_checkpoint(self, checkpoint_id: str) -> None:
        """Remove a checkpoint."""
        self._checkpoints.pop(checkpoint_id, None)

    def clear_mission_checkpoints(self, mission_id: str) -> None:
        """Remove all checkpoints for a given mission."""
        to_remove = [
            cid
            for cid, cp in self._checkpoints.items()
            if cp.mission_id == mission_id
        ]
        for cid in to_remove:
            del self._checkpoints[cid]

    def update(self, player_position: Tuple[float, float, float]) -> List[Checkpoint]:
        """Check if the player has reached any pending checkpoints.

        Args:
            player_position: Current (x, y, z) world position.

        Returns:
            List of newly reached checkpoints this frame.
        """
        reached = []
        for cp in self._checkpoints.values():
            if cp.check_player(player_position):
                self._last_checkpoint = cp
                reached.append(cp)
                for cb in self._reached_callbacks:
                    cb(cp)
        return reached

    def on_reached(self, callback: CheckpointReachedCallback) -> None:
        """Register a callback for checkpoint reached events."""
        self._reached_callbacks.append(callback)

    @property
    def respawn_position(self) -> Optional[Tuple[float, float, float]]:
        """Return the best available respawn position."""
        if self._last_checkpoint is None:
            return None
        if self._last_checkpoint.respawn_position:
            return self._last_checkpoint.respawn_position
        return self._last_checkpoint.position

    @property
    def pending_count(self) -> int:
        return sum(1 for cp in self._checkpoints.values() if not cp.is_reached)

    @property
    def reached_count(self) -> int:
        return sum(1 for cp in self._checkpoints.values() if cp.is_reached)

    def reset_all(self) -> None:
        """Reset all checkpoints for replay."""
        for cp in self._checkpoints.values():
            cp.reset()
        self._last_checkpoint = None

    def __repr__(self) -> str:
        return (
            f"CheckpointSystem("
            f"total={len(self._checkpoints)}, "
            f"reached={self.reached_count}, "
            f"pending={self.pending_count})"
        )
