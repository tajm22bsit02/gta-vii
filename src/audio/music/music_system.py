"""Music System - dynamic adaptive music based on game state."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class MusicState(Enum):
    """Game states that drive music selection."""

    EXPLORATION = auto()
    MISSION = auto()
    COMBAT = auto()
    CHASE = auto()
    WANTED = auto()
    VEHICLE = auto()
    CUTSCENE = auto()
    MENU = auto()
    AMBIENT = auto()


@dataclass
class MusicTrack:
    """Metadata for a single music track."""

    track_id: str
    title: str
    artist: str
    duration: float        # seconds
    bpm: float = 120.0
    mood: MusicState = MusicState.EXPLORATION
    volume: float = 1.0
    loop: bool = True
    file_path: str = ""

    @property
    def duration_str(self) -> str:
        minutes = int(self.duration // 60)
        seconds = int(self.duration % 60)
        return f"{minutes}:{seconds:02d}"

    def __repr__(self) -> str:
        return f"MusicTrack({self.title!r} by {self.artist!r}, {self.duration_str})"


class RadioStation:
    """A virtual in-game radio station with a playlist."""

    def __init__(self, name: str, genre: str) -> None:
        self.name: str = name
        self.genre: str = genre
        self._playlist: List[MusicTrack] = []
        self._current_index: int = 0

    def add_track(self, track: MusicTrack) -> None:
        self._playlist.append(track)

    def next_track(self) -> Optional[MusicTrack]:
        if not self._playlist:
            return None
        track = self._playlist[self._current_index]
        self._current_index = (self._current_index + 1) % len(self._playlist)
        return track

    @property
    def track_count(self) -> int:
        return len(self._playlist)


class MusicSystem:
    """Dynamic music manager with state-based track selection and radio stations."""

    CROSSFADE_DURATION: float = 3.0

    def __init__(self) -> None:
        self._stations: Dict[str, RadioStation] = {}
        self._state_tracks: Dict[MusicState, List[MusicTrack]] = {}
        self._current_state: MusicState = MusicState.EXPLORATION
        self._current_track: Optional[MusicTrack] = None
        self._current_station: Optional[RadioStation] = None
        self._track_timer: float = 0.0
        self.music_volume: float = 0.8
        self.radio_mode: bool = False
        self._populate_default_tracks()
        self._populate_default_stations()

    def _populate_default_tracks(self) -> None:
        """Define the default adaptive music library."""
        tracks = [
            MusicTrack("ambient_city_day", "Vice City Days", "Synthwave Collective",
                       240.0, 90.0, MusicState.EXPLORATION),
            MusicTrack("ambient_city_night", "Neon Nights", "The Electric Dreams",
                       200.0, 95.0, MusicState.AMBIENT),
            MusicTrack("combat_intense", "Full Auto", "Metal Forge",
                       180.0, 160.0, MusicState.COMBAT),
            MusicTrack("chase_pursuit", "Hot Pursuit", "DJ Velocity",
                       150.0, 140.0, MusicState.CHASE),
            MusicTrack("mission_dramatic", "Last Stand", "Orchestral Unit",
                       300.0, 80.0, MusicState.MISSION),
            MusicTrack("menu_theme", "Vice City VII Theme", "The Composer",
                       120.0, 75.0, MusicState.MENU),
        ]
        for track in tracks:
            self._state_tracks.setdefault(track.mood, []).append(track)

    def _populate_default_stations(self) -> None:
        """Create default in-game radio stations."""
        stations = [
            RadioStation("Vice FM", "Electronic"),
            RadioStation("Talk Radio GTA", "Talk/Comedy"),
            RadioStation("Classic Rock City", "Classic Rock"),
            RadioStation("Hip-Hop Vice", "Hip-Hop"),
        ]
        sample_tracks = [
            MusicTrack(f"station_track_{i}", f"Track {i}", "Various Artists", 200.0)
            for i in range(4)
        ]
        for i, station in enumerate(stations):
            station.add_track(sample_tracks[i % len(sample_tracks)])
            self._stations[station.name] = station

    def set_state(self, state: MusicState) -> None:
        """Transition to a new music state (triggers track change if needed)."""
        if state != self._current_state:
            self._current_state = state
            self._select_track_for_state(state)

    def _select_track_for_state(self, state: MusicState) -> None:
        tracks = self._state_tracks.get(state, [])
        if tracks:
            import random
            self._current_track = random.choice(tracks)
            self._track_timer = 0.0

    def tune_to_station(self, station_name: str) -> bool:
        """Switch to a radio station."""
        station = self._stations.get(station_name)
        if station is None:
            return False
        self._current_station = station
        self._current_track = station.next_track()
        self.radio_mode = True
        return True

    def update(self, delta_time: float) -> None:
        """Advance the track timer and auto-advance finished tracks."""
        if self._current_track is None:
            return
        self._track_timer += delta_time
        if self._track_timer >= self._current_track.duration:
            self._track_timer = 0.0
            if self.radio_mode and self._current_station:
                self._current_track = self._current_station.next_track()
            else:
                self._select_track_for_state(self._current_state)

    @property
    def current_track(self) -> Optional[MusicTrack]:
        return self._current_track

    @property
    def station_names(self) -> List[str]:
        return sorted(self._stations.keys())

    def __repr__(self) -> str:
        track_name = self._current_track.title if self._current_track else "None"
        return (
            f"MusicSystem(state={self._current_state.name}, "
            f"track={track_name!r}, "
            f"radio={self.radio_mode})"
        )
