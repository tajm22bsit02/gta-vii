"""3D Spatial Audio - positional audio source and listener system."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class AudioListener:
    """Represents the audio receiver (usually the player camera)."""

    position: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    forward: Tuple[float, float, float] = (0.0, 0.0, 1.0)
    up: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class AudioSource:
    """A positional audio emitter in the 3D world."""

    source_id: str
    sound_name: str
    position: Tuple[float, float, float] = field(default_factory=lambda: (0.0, 0.0, 0.0))
    volume: float = 1.0           # 0.0-1.0
    pitch: float = 1.0            # multiplier
    min_distance: float = 5.0    # Full volume within this radius
    max_distance: float = 100.0  # Silence beyond this radius
    is_looping: bool = False
    is_playing: bool = False
    _elapsed: float = field(default=0.0, init=False, repr=False)

    def play(self) -> None:
        self.is_playing = True
        self._elapsed = 0.0

    def stop(self) -> None:
        self.is_playing = False

    def calculate_volume_at(self, listener: AudioListener) -> float:
        """Compute the perceived volume at the listener position.

        Uses linear distance attenuation between min and max distance.

        Args:
            listener: The audio listener to calculate for.

        Returns:
            Perceived volume in [0.0, 1.0].
        """
        dist = math.sqrt(
            (listener.position[0] - self.position[0]) ** 2
            + (listener.position[1] - self.position[1]) ** 2
            + (listener.position[2] - self.position[2]) ** 2
        )
        if dist <= self.min_distance:
            return self.volume
        if dist >= self.max_distance:
            return 0.0
        atten = 1.0 - (dist - self.min_distance) / (self.max_distance - self.min_distance)
        return self.volume * atten

    def calculate_pan_at(self, listener: AudioListener) -> float:
        """Compute stereo panning (-1=left, 0=center, 1=right).

        Args:
            listener: The audio listener.

        Returns:
            Stereo pan value in [-1.0, 1.0].
        """
        dx = self.position[0] - listener.position[0]
        dz = self.position[2] - listener.position[2]
        fx, fz = listener.forward[0], listener.forward[2]
        right_x = -fz
        right_z = fx
        dot = dx * right_x + dz * right_z
        dist = math.sqrt(dx * dx + dz * dz) or 1.0
        return max(-1.0, min(1.0, dot / dist))


class Audio3DSystem:
    """Manages all 3D audio sources and the single listener."""

    MAX_ACTIVE_SOURCES: int = 64

    def __init__(self) -> None:
        self._sources: Dict[str, AudioSource] = {}
        self.listener: AudioListener = AudioListener()
        self.master_volume: float = 1.0

    def create_source(
        self,
        source_id: str,
        sound_name: str,
        position: Tuple[float, float, float],
        **kwargs,
    ) -> AudioSource:
        """Create and register a new audio source."""
        source = AudioSource(source_id=source_id, sound_name=sound_name, position=position, **kwargs)
        self._sources[source_id] = source
        return source

    def play_at(
        self,
        sound_name: str,
        position: Tuple[float, float, float],
        volume: float = 1.0,
        looping: bool = False,
    ) -> Optional[AudioSource]:
        """Play a one-shot sound at a world position."""
        if len(self._sources) >= self.MAX_ACTIVE_SOURCES:
            self._evict_oldest()
        source_id = f"src_{sound_name}_{len(self._sources)}"
        source = self.create_source(source_id, sound_name, position, volume=volume, is_looping=looping)
        source.play()
        return source

    def stop_source(self, source_id: str) -> None:
        source = self._sources.get(source_id)
        if source:
            source.stop()

    def remove_source(self, source_id: str) -> None:
        self._sources.pop(source_id, None)

    def update(self, delta_time: float) -> None:
        """Remove non-looping stopped sources."""
        to_remove = [
            sid for sid, src in self._sources.items()
            if not src.is_playing and not src.is_looping
        ]
        for sid in to_remove:
            del self._sources[sid]

    def get_active_sources(self) -> List[AudioSource]:
        return [s for s in self._sources.values() if s.is_playing]

    def _evict_oldest(self) -> None:
        if self._sources:
            oldest_id = next(iter(self._sources))
            del self._sources[oldest_id]

    def __repr__(self) -> str:
        return (
            f"Audio3DSystem(sources={len(self._sources)}, "
            f"master_vol={self.master_volume:.2f})"
        )
