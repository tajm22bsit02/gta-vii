"""City Manager - manages districts, landmarks, and the open-world map."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class DistrictType(Enum):
    """Types of city districts with distinct visual and gameplay characteristics."""

    DOWNTOWN = auto()
    SUBURBS = auto()
    INDUSTRIAL = auto()
    BEACHFRONT = auto()
    AIRPORT = auto()
    HARBOR = auto()
    COUNTRYSIDE = auto()


@dataclass
class Building:
    """Represents a building in the city."""

    name: str
    position: Tuple[float, float]
    width: float
    height: float
    floors: int
    is_enterable: bool = False


@dataclass
class Road:
    """Represents a road segment connecting two positions."""

    start: Tuple[float, float]
    end: Tuple[float, float]
    lanes: int = 2
    speed_limit: float = 50.0
    is_highway: bool = False


@dataclass
class District:
    """A named area of the city with buildings, roads, and metadata."""

    name: str
    district_type: DistrictType
    center: Tuple[float, float]
    radius: float
    buildings: List[Building] = field(default_factory=list)
    roads: List[Road] = field(default_factory=list)
    crime_level: float = 0.5  # 0.0 = peaceful, 1.0 = very dangerous
    population_density: float = 0.5  # 0.0 = empty, 1.0 = packed

    def contains_point(self, x: float, y: float) -> bool:
        """Return True if (x, y) is within this district's radius."""
        dx, dy = x - self.center[0], y - self.center[1]
        return (dx * dx + dy * dy) <= self.radius ** 2

    def add_building(self, building: Building) -> None:
        """Add a building to this district."""
        self.buildings.append(building)

    def add_road(self, road: Road) -> None:
        """Add a road to this district."""
        self.roads.append(road)


class CityManager:
    """Manages the entire city layout.

    Handles district registration, player location queries, landmark
    lookup, and procedural city generation.
    """

    def __init__(self) -> None:
        self._districts: Dict[str, District] = {}
        self._total_area: Tuple[float, float] = (10_000.0, 10_000.0)

        self._generate_default_city()

    # ------------------------------------------------------------------ #
    # City generation                                                      #
    # ------------------------------------------------------------------ #

    def _generate_default_city(self) -> None:
        """Generate the default Vice City map layout."""
        district_configs = [
            ("Downtown", DistrictType.DOWNTOWN, (0.0, 0.0), 1_500.0, 0.3, 0.9),
            ("Beachfront", DistrictType.BEACHFRONT, (2_000.0, -500.0), 1_200.0, 0.2, 0.7),
            ("Industrial Zone", DistrictType.INDUSTRIAL, (-2_000.0, 0.0), 1_000.0, 0.7, 0.4),
            ("Suburbs North", DistrictType.SUBURBS, (500.0, 2_000.0), 1_500.0, 0.4, 0.6),
            ("Suburbs South", DistrictType.SUBURBS, (500.0, -2_000.0), 1_500.0, 0.4, 0.5),
            ("International Airport", DistrictType.AIRPORT, (-1_500.0, 2_500.0), 800.0, 0.1, 0.3),
            ("Harbor District", DistrictType.HARBOR, (3_000.0, 1_000.0), 900.0, 0.5, 0.4),
            ("Countryside", DistrictType.COUNTRYSIDE, (0.0, 4_000.0), 3_000.0, 0.2, 0.1),
        ]

        for name, dtype, center, radius, crime, density in district_configs:
            district = District(
                name=name,
                district_type=dtype,
                center=center,
                radius=radius,
                crime_level=crime,
                population_density=density,
            )
            self._add_sample_buildings(district)
            self._add_sample_roads(district)
            self.register_district(district)

    def _add_sample_buildings(self, district: District) -> None:
        """Add representative buildings based on district type."""
        cx, cy = district.center
        count_map = {
            DistrictType.DOWNTOWN: 20,
            DistrictType.SUBURBS: 10,
            DistrictType.INDUSTRIAL: 8,
            DistrictType.BEACHFRONT: 6,
            DistrictType.AIRPORT: 3,
            DistrictType.HARBOR: 5,
            DistrictType.COUNTRYSIDE: 2,
        }
        count = count_map.get(district.district_type, 5)
        import math
        for i in range(count):
            angle = (2 * math.pi / count) * i
            offset = district.radius * 0.5
            bx = cx + math.cos(angle) * offset
            by = cy + math.sin(angle) * offset
            floors = 20 if district.district_type == DistrictType.DOWNTOWN else 5
            district.add_building(
                Building(
                    name=f"{district.name}_Building_{i+1}",
                    position=(bx, by),
                    width=20.0,
                    height=float(floors * 3),
                    floors=floors,
                    is_enterable=(i % 3 == 0),
                )
            )

    def _add_sample_roads(self, district: District) -> None:
        """Add a simple grid of roads to the district."""
        cx, cy = district.center
        r = district.radius * 0.8
        district.add_road(Road(start=(cx - r, cy), end=(cx + r, cy), lanes=4))
        district.add_road(Road(start=(cx, cy - r), end=(cx, cy + r), lanes=4))

    # ------------------------------------------------------------------ #
    # District registry                                                    #
    # ------------------------------------------------------------------ #

    def register_district(self, district: District) -> None:
        """Register a district with the city manager."""
        self._districts[district.name] = district

    def get_district(self, name: str) -> Optional[District]:
        """Retrieve a district by name."""
        return self._districts.get(name)

    def get_district_at(self, x: float, y: float) -> Optional[District]:
        """Return the district containing point (x, y), or None."""
        for district in self._districts.values():
            if district.contains_point(x, y):
                return district
        return None

    @property
    def district_names(self) -> List[str]:
        """Return a sorted list of all district names."""
        return sorted(self._districts.keys())

    @property
    def total_buildings(self) -> int:
        """Return the total number of buildings across all districts."""
        return sum(len(d.buildings) for d in self._districts.values())

    @property
    def total_roads(self) -> int:
        """Return the total number of road segments across all districts."""
        return sum(len(d.roads) for d in self._districts.values())

    def __repr__(self) -> str:
        return (
            f"CityManager(districts={len(self._districts)}, "
            f"buildings={self.total_buildings}, "
            f"roads={self.total_roads})"
        )
