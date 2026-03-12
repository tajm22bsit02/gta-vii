"""Inventory System - item management, weapons, and equipment."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class ItemCategory(Enum):
    """Broad categories of inventory items."""

    WEAPON = auto()
    AMMO = auto()
    HEALTH = auto()
    ARMOUR = auto()
    KEY_ITEM = auto()
    MISC = auto()
    CLOTHING = auto()


@dataclass
class InventoryItem:
    """A generic item held in the player's inventory."""

    item_id: str
    name: str
    category: ItemCategory
    quantity: int = 1
    max_stack: int = 99
    weight: float = 0.1  # kg
    value: int = 0        # in-game currency

    def can_stack(self, other: "InventoryItem") -> bool:
        """Return True if other can be merged into this stack."""
        return (
            self.item_id == other.item_id
            and self.quantity < self.max_stack
        )

    def __repr__(self) -> str:
        return f"InventoryItem({self.name!r} x{self.quantity})"


@dataclass
class WeaponItem(InventoryItem):
    """A weapon item with ammo and firing stats."""

    damage: float = 10.0
    fire_rate: float = 1.0       # rounds per second
    range_: float = 50.0         # effective range in metres
    ammo_type: str = "pistol"
    magazine_size: int = 12
    current_ammo: int = 12
    reserved_ammo: int = 60
    is_automatic: bool = False
    reload_time: float = 2.0     # seconds

    def __post_init__(self) -> None:
        self.category = ItemCategory.WEAPON
        self.max_stack = 1

    @property
    def needs_reload(self) -> bool:
        return self.current_ammo == 0

    @property
    def total_ammo(self) -> int:
        return self.current_ammo + self.reserved_ammo

    def fire(self) -> bool:
        """Consume one round if available.

        Returns:
            True if a round was fired, False if empty.
        """
        if self.current_ammo <= 0:
            return False
        self.current_ammo -= 1
        return True

    def reload(self) -> int:
        """Reload from reserved ammo.

        Returns:
            Number of rounds loaded.
        """
        needed = self.magazine_size - self.current_ammo
        available = min(needed, self.reserved_ammo)
        self.current_ammo += available
        self.reserved_ammo -= available
        return available

    def add_ammo(self, amount: int) -> None:
        """Add ammo to the reserved pool."""
        self.reserved_ammo += amount

    def __repr__(self) -> str:
        return (
            f"WeaponItem({self.name!r}, "
            f"ammo={self.current_ammo}/{self.reserved_ammo})"
        )


class InventorySystem:
    """Manages the player's full inventory including weapons and items.

    Enforces weight limits, handles stacking, and exposes a weapon
    selection API for the combat system.
    """

    MAX_WEIGHT_KG: float = 50.0

    def __init__(self) -> None:
        self._items: Dict[str, InventoryItem] = {}
        self._weapon_slots: Dict[int, Optional[WeaponItem]] = {
            i: None for i in range(1, 9)
        }
        self._selected_slot: int = 1
        self.money: int = 0

    # ------------------------------------------------------------------ #
    # Item management                                                      #
    # ------------------------------------------------------------------ #

    def add_item(self, item: InventoryItem) -> bool:
        """Add an item to the inventory.

        Attempts to stack with existing items before creating a new slot.

        Args:
            item: The item to add.

        Returns:
            True if the item was added, False if inventory is overweight.
        """
        if self.current_weight + item.weight > self.MAX_WEIGHT_KG:
            return False

        if item.item_id in self._items and item.category != ItemCategory.WEAPON:
            existing = self._items[item.item_id]
            if existing.can_stack(item):
                space = existing.max_stack - existing.quantity
                added = min(space, item.quantity)
                existing.quantity += added
                item.quantity -= added
                if item.quantity == 0:
                    return True

        self._items[item.item_id] = item
        if isinstance(item, WeaponItem):
            self._auto_equip_weapon(item)
        return True

    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """Remove items by ID and quantity.

        Returns:
            True if removed, False if not found or insufficient quantity.
        """
        item = self._items.get(item_id)
        if item is None or item.quantity < quantity:
            return False
        item.quantity -= quantity
        if item.quantity <= 0:
            del self._items[item_id]
        return True

    def has_item(self, item_id: str) -> bool:
        return item_id in self._items

    def get_item(self, item_id: str) -> Optional[InventoryItem]:
        return self._items.get(item_id)

    # ------------------------------------------------------------------ #
    # Weapon management                                                    #
    # ------------------------------------------------------------------ #

    def equip_weapon(self, weapon: WeaponItem, slot: int) -> bool:
        """Equip a weapon to a numbered slot (1-8)."""
        if slot < 1 or slot > 8:
            return False
        self._weapon_slots[slot] = weapon
        return True

    def select_weapon(self, slot: int) -> Optional[WeaponItem]:
        """Switch the active weapon slot."""
        if 1 <= slot <= 8:
            self._selected_slot = slot
        return self.current_weapon

    @property
    def current_weapon(self) -> Optional[WeaponItem]:
        """Return the currently selected weapon."""
        return self._weapon_slots.get(self._selected_slot)

    def _auto_equip_weapon(self, weapon: WeaponItem) -> None:
        """Fill the first empty weapon slot."""
        for slot in range(1, 9):
            if self._weapon_slots[slot] is None:
                self._weapon_slots[slot] = weapon
                return

    # ------------------------------------------------------------------ #
    # Economy                                                              #
    # ------------------------------------------------------------------ #

    def add_money(self, amount: int) -> None:
        """Add in-game currency."""
        if amount > 0:
            self.money += amount

    def spend_money(self, amount: int) -> bool:
        """Deduct currency if sufficient funds exist."""
        if self.money >= amount:
            self.money -= amount
            return True
        return False

    # ------------------------------------------------------------------ #
    # Utility                                                              #
    # ------------------------------------------------------------------ #

    @property
    def current_weight(self) -> float:
        return sum(i.weight * i.quantity for i in self._items.values())

    @property
    def item_count(self) -> int:
        return len(self._items)

    def get_weapons(self) -> List[WeaponItem]:
        """Return all weapon items in inventory."""
        return [i for i in self._items.values() if isinstance(i, WeaponItem)]

    def __repr__(self) -> str:
        return (
            f"InventorySystem("
            f"items={self.item_count}, "
            f"weight={self.current_weight:.1f}/{self.MAX_WEIGHT_KG}kg, "
            f"money=${self.money})"
        )
