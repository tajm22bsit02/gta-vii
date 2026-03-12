"""Property System - real-estate ownership and passive income."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple


class PropertyType(Enum):
    """Categories of purchasable properties."""

    SAFE_HOUSE = auto()
    BUSINESS = auto()
    WAREHOUSE = auto()
    NIGHTCLUB = auto()
    CAR_DEALERSHIP = auto()
    GARAGE = auto()
    AIRPORT_HANGAR = auto()
    MARINA = auto()
    PENTHOUSE = auto()


@dataclass
class Property:
    """A purchasable real-estate asset."""

    property_id: str
    name: str
    property_type: PropertyType
    location: Tuple[float, float]
    purchase_price: int
    weekly_income: int = 0
    upgrade_level: int = 0
    max_upgrade_level: int = 3
    is_owned: bool = False
    description: str = ""
    vehicle_storage_slots: int = 0
    weapon_storage: bool = False

    @property
    def is_upgradable(self) -> bool:
        return self.upgrade_level < self.max_upgrade_level

    def upgrade(self, cost: int) -> bool:
        """Upgrade this property if eligible.

        Returns:
            True if upgrade applied.
        """
        if not self.is_upgradable:
            return False
        self.upgrade_level += 1
        self.weekly_income = int(self.weekly_income * 1.25)
        return True

    def __repr__(self) -> str:
        return (
            f"Property({self.name!r}, "
            f"type={self.property_type.name}, "
            f"owned={self.is_owned}, "
            f"income=${self.weekly_income}/wk)"
        )


PropertyPurchaseCallback = Callable[[Property], None]


class PropertySystem:
    """Manages property ownership, purchasing, and passive income."""

    def __init__(self) -> None:
        self._properties: Dict[str, Property] = {}
        self._purchase_callbacks: List[PropertyPurchaseCallback] = []
        self._income_timer: float = 0.0
        self.INCOME_INTERVAL: float = 300.0  # 5 min real-time = ~1 game week

        self._populate_default_properties()

    def _populate_default_properties(self) -> None:
        """Add the default property catalogue."""
        defaults = [
            Property("safehouse_downtown", "Downtown Apartment", PropertyType.SAFE_HOUSE,
                     (100.0, 200.0), 50_000, 0),
            Property("garage_industrial", "Industrial Garage", PropertyType.GARAGE,
                     (-500.0, 100.0), 30_000, 500, vehicle_storage_slots=10),
            Property("nightclub_beach", "Neon Vice Nightclub", PropertyType.NIGHTCLUB,
                     (1_500.0, -300.0), 250_000, 8_000),
            Property("warehouse_harbor", "Harbor Warehouse", PropertyType.WAREHOUSE,
                     (2_800.0, 800.0), 120_000, 3_000),
            Property("penthouse_tower", "Skyline Penthouse", PropertyType.PENTHOUSE,
                     (50.0, 50.0), 1_200_000, 0),
            Property("car_dealership", "AutoVice Motors", PropertyType.CAR_DEALERSHIP,
                     (-200.0, -500.0), 400_000, 12_000),
            Property("airport_hangar", "Airport Hangar", PropertyType.AIRPORT_HANGAR,
                     (-1_200.0, 2_300.0), 600_000, 0, vehicle_storage_slots=5),
        ]
        for prop in defaults:
            self._properties[prop.property_id] = prop

    def purchase(self, property_id: str, buyer_balance: int) -> Optional[Property]:
        """Attempt to purchase a property.

        Args:
            property_id: The property to buy.
            buyer_balance: Buyer's available funds (checked externally).

        Returns:
            The purchased Property, or None if unavailable / already owned.
        """
        prop = self._properties.get(property_id)
        if prop is None or prop.is_owned or buyer_balance < prop.purchase_price:
            return None
        prop.is_owned = True
        for cb in self._purchase_callbacks:
            cb(prop)
        return prop

    def on_purchase(self, callback: PropertyPurchaseCallback) -> None:
        self._purchase_callbacks.append(callback)

    def update(self, delta_time: float) -> int:
        """Advance income timer.

        Returns:
            Total passive income earned this tick (0 if no interval elapsed).
        """
        self._income_timer += delta_time
        if self._income_timer >= self.INCOME_INTERVAL:
            self._income_timer = 0.0
            return self._collect_income()
        return 0

    def _collect_income(self) -> int:
        return sum(p.weekly_income for p in self._properties.values() if p.is_owned)

    @property
    def owned_properties(self) -> List[Property]:
        return [p for p in self._properties.values() if p.is_owned]

    @property
    def available_properties(self) -> List[Property]:
        return [p for p in self._properties.values() if not p.is_owned]

    @property
    def total_weekly_income(self) -> int:
        return sum(p.weekly_income for p in self.owned_properties)

    def get_property(self, property_id: str) -> Optional[Property]:
        return self._properties.get(property_id)

    def __repr__(self) -> str:
        return (
            f"PropertySystem(owned={len(self.owned_properties)}, "
            f"income=${self.total_weekly_income}/wk)"
        )
