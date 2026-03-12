"""Scene Manager - handles scene transitions and lifecycle."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class Scene(ABC):
    """Abstract base class for all game scenes (levels, menus, etc.)."""

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.loaded: bool = False

    def on_enter(self) -> None:
        """Called when this scene becomes active."""

    @abstractmethod
    def update(self, delta_time: float) -> None:
        """Update scene logic.

        Args:
            delta_time: Time elapsed since the last frame in seconds.
        """

    @abstractmethod
    def render(self, renderer: object) -> None:
        """Render the scene.

        Args:
            renderer: The rendering pipeline to draw with.
        """

    def on_exit(self) -> None:
        """Called when the scene is deactivated."""

    def on_pause(self) -> None:
        """Called when the scene is pushed down by another scene."""

    def on_resume(self) -> None:
        """Called when the scene returns to the top of the stack."""

    def __repr__(self) -> str:
        return f"Scene(name={self.name!r}, loaded={self.loaded})"


class SceneManager:
    """Manages a stack of game scenes.

    The top of the stack is the active scene. Scenes below it are paused
    but remain in memory for fast resumption.
    """

    def __init__(self) -> None:
        self._stack: List[Scene] = []
        self._registered: Dict[str, Scene] = {}

    def register(self, scene: Scene) -> None:
        """Register a scene by name for later use.

        Args:
            scene: The scene to register.
        """
        self._registered[scene.name] = scene

    def push(self, scene_or_name: "Scene | str") -> None:
        """Push a scene onto the stack, pausing the current scene.

        Args:
            scene_or_name: Scene instance or registered scene name.
        """
        scene = self._resolve(scene_or_name)
        if self._stack:
            self._stack[-1].on_pause()
        scene.loaded = True
        scene.on_enter()
        self._stack.append(scene)

    def pop(self) -> Optional[Scene]:
        """Remove and return the top scene.

        Returns:
            The scene that was removed, or None if the stack is empty.
        """
        if not self._stack:
            return None
        scene = self._stack.pop()
        scene.on_exit()
        scene.loaded = False
        if self._stack:
            self._stack[-1].on_resume()
        return scene

    def replace(self, scene_or_name: "Scene | str") -> None:
        """Replace the current scene without keeping it in the stack."""
        if self._stack:
            old = self._stack.pop()
            old.on_exit()
            old.loaded = False
        scene = self._resolve(scene_or_name)
        scene.loaded = True
        scene.on_enter()
        self._stack.append(scene)

    def update(self, delta_time: float) -> None:
        """Update the active (top) scene."""
        if self._stack:
            self._stack[-1].update(delta_time)

    def render(self, renderer: object) -> None:
        """Render the active scene."""
        if self._stack:
            self._stack[-1].render(renderer)

    @property
    def current_scene(self) -> Optional[Scene]:
        """Return the currently active scene."""
        return self._stack[-1] if self._stack else None

    @property
    def stack_depth(self) -> int:
        """Return the number of scenes currently in the stack."""
        return len(self._stack)

    def _resolve(self, scene_or_name: "Scene | str") -> Scene:
        """Resolve a scene instance or name to a Scene object."""
        if isinstance(scene_or_name, str):
            if scene_or_name not in self._registered:
                raise KeyError(f"Scene '{scene_or_name}' is not registered.")
            return self._registered[scene_or_name]
        return scene_or_name

    def __repr__(self) -> str:
        current = self.current_scene
        return (
            f"SceneManager(depth={self.stack_depth}, "
            f"current={current.name if current else None!r})"
        )
