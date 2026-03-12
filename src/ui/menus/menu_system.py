"""Menu System - main menu, pause menu, and in-game interfaces."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional


class MenuAction(Enum):
    """Actions that can be triggered from menu items."""

    NEW_GAME = auto()
    LOAD_GAME = auto()
    SAVE_GAME = auto()
    RESUME = auto()
    QUIT = auto()
    SETTINGS = auto()
    CREDITS = auto()
    CHARACTER = auto()
    INVENTORY = auto()
    MAP = auto()
    MISSIONS = auto()
    BACK = auto()


@dataclass
class MenuItem:
    """A single selectable item in a menu screen."""

    label: str
    action: MenuAction
    enabled: bool = True
    callback: Optional[Callable[[], None]] = field(default=None, repr=False)

    def activate(self) -> None:
        """Execute this menu item's callback if enabled."""
        if self.enabled and self.callback:
            self.callback()

    def __repr__(self) -> str:
        return f"MenuItem({self.label!r}, action={self.action.name}, enabled={self.enabled})"


class MenuScreen:
    """A single menu screen containing a list of items."""

    def __init__(self, screen_id: str, title: str) -> None:
        self.screen_id: str = screen_id
        self.title: str = title
        self._items: List[MenuItem] = []
        self._selected_index: int = 0

    def add_item(self, item: MenuItem) -> None:
        self._items.append(item)

    def select_next(self) -> None:
        """Move selection down."""
        if self._items:
            self._selected_index = (self._selected_index + 1) % len(self._items)

    def select_prev(self) -> None:
        """Move selection up."""
        if self._items:
            self._selected_index = (self._selected_index - 1) % len(self._items)

    def confirm(self) -> Optional[MenuAction]:
        """Activate the selected item and return its action."""
        if not self._items:
            return None
        item = self._items[self._selected_index]
        item.activate()
        return item.action

    @property
    def selected_item(self) -> Optional[MenuItem]:
        if not self._items:
            return None
        return self._items[self._selected_index]

    @property
    def items(self) -> List[MenuItem]:
        return list(self._items)

    def __repr__(self) -> str:
        return (
            f"MenuScreen({self.screen_id!r}, "
            f"items={len(self._items)}, "
            f"selected={self._selected_index})"
        )


class MenuSystem:
    """Manages the full hierarchy of game menus."""

    def __init__(self) -> None:
        self._screens: Dict[str, MenuScreen] = {}
        self._history: List[MenuScreen] = []
        self._build_default_menus()

    def _build_default_menus(self) -> None:
        """Create the standard menu set."""
        # Main Menu
        main = MenuScreen("main_menu", "GTA VII")
        main.add_item(MenuItem("New Game", MenuAction.NEW_GAME))
        main.add_item(MenuItem("Load Game", MenuAction.LOAD_GAME))
        main.add_item(MenuItem("Settings", MenuAction.SETTINGS))
        main.add_item(MenuItem("Credits", MenuAction.CREDITS))
        main.add_item(MenuItem("Quit", MenuAction.QUIT))
        self.register(main)

        # Pause Menu
        pause = MenuScreen("pause_menu", "Paused")
        pause.add_item(MenuItem("Resume", MenuAction.RESUME))
        pause.add_item(MenuItem("Map", MenuAction.MAP))
        pause.add_item(MenuItem("Inventory", MenuAction.INVENTORY))
        pause.add_item(MenuItem("Missions", MenuAction.MISSIONS))
        pause.add_item(MenuItem("Save Game", MenuAction.SAVE_GAME))
        pause.add_item(MenuItem("Settings", MenuAction.SETTINGS))
        pause.add_item(MenuItem("Quit to Main Menu", MenuAction.QUIT))
        self.register(pause)

        # Settings
        settings = MenuScreen("settings_menu", "Settings")
        settings.add_item(MenuItem("Graphics", MenuAction.SETTINGS))
        settings.add_item(MenuItem("Audio", MenuAction.SETTINGS))
        settings.add_item(MenuItem("Controls", MenuAction.SETTINGS))
        settings.add_item(MenuItem("Back", MenuAction.BACK))
        self.register(settings)

    def register(self, screen: MenuScreen) -> None:
        self._screens[screen.screen_id] = screen

    def open(self, screen_id: str) -> bool:
        """Open a menu screen by ID."""
        screen = self._screens.get(screen_id)
        if screen is None:
            return False
        self._history.append(screen)
        return True

    def back(self) -> Optional[MenuScreen]:
        """Go back to the previous menu screen."""
        if len(self._history) > 1:
            self._history.pop()
        return self.current_screen

    def close_all(self) -> None:
        self._history.clear()

    @property
    def current_screen(self) -> Optional[MenuScreen]:
        return self._history[-1] if self._history else None

    @property
    def is_open(self) -> bool:
        return len(self._history) > 0

    def __repr__(self) -> str:
        current = self.current_screen
        return (
            f"MenuSystem(screens={len(self._screens)}, "
            f"open={self.is_open}, "
            f"current={current.screen_id if current else None!r})"
        )
