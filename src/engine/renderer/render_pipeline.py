"""Render Pipeline - manages the full rendering stack."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional, Tuple

from ..physics.physics_engine import Vector3


class RenderLayer(Enum):
    """Rendering layers in draw order (lowest value drawn first)."""

    BACKGROUND = 0
    WORLD = 10
    CHARACTERS = 20
    VEHICLES = 25
    EFFECTS = 30
    UI = 40
    DEBUG = 50


@dataclass
class Color:
    """RGBA colour (0-255 per channel)."""

    r: int = 255
    g: int = 255
    b: int = 255
    a: int = 255

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)

    def as_rgb(self) -> Tuple[int, int, int]:
        return (self.r, self.g, self.b)

    # Preset colours
    WHITE = None
    BLACK = None
    RED = None
    GREEN = None
    BLUE = None


# Initialise class-level presets after class definition
Color.WHITE = Color(255, 255, 255)
Color.BLACK = Color(0, 0, 0)
Color.RED = Color(255, 0, 0)
Color.GREEN = Color(0, 255, 0)
Color.BLUE = Color(0, 0, 255)


@dataclass
class RenderCommand:
    """A single draw instruction queued in the render pipeline."""

    layer: RenderLayer
    callback: Callable[[], None]
    order_hint: int = 0


class Camera:
    """Represents the game camera (position, zoom, rotation)."""

    def __init__(self) -> None:
        self.position: Vector3 = Vector3()
        self.rotation: float = 0.0
        self.zoom: float = 1.0
        self.fov: float = 90.0
        self.near_clip: float = 0.1
        self.far_clip: float = 10_000.0

    def follow(self, target_position: Vector3, lerp_speed: float = 5.0, delta_time: float = 0.016) -> None:
        """Smoothly follow a target position.

        Args:
            target_position: The position to move towards.
            lerp_speed: How quickly to interpolate (units per second).
            delta_time: Frame time used for lerp.
        """
        alpha = min(lerp_speed * delta_time, 1.0)
        self.position.x += (target_position.x - self.position.x) * alpha
        self.position.y += (target_position.y - self.position.y) * alpha
        self.position.z += (target_position.z - self.position.z) * alpha

    def world_to_screen(
        self, world_pos: Vector3, screen_width: int, screen_height: int
    ) -> Tuple[int, int]:
        """Project a world-space position to screen-space pixels.

        Args:
            world_pos: The 3-D world position.
            screen_width: Current screen width in pixels.
            screen_height: Current screen height in pixels.

        Returns:
            (x, y) pixel coordinates on screen.
        """
        dx = (world_pos.x - self.position.x) * self.zoom
        dz = (world_pos.z - self.position.z) * self.zoom
        sx = int(screen_width / 2 + dx)
        sy = int(screen_height / 2 - dz)
        return (sx, sy)


class Shader:
    """Represents a named shader with a set of uniform parameters."""

    def __init__(self, name: str) -> None:
        self.name: str = name
        self.uniforms: Dict[str, object] = {}

    def set_uniform(self, name: str, value: object) -> None:
        """Set a named uniform parameter."""
        self.uniforms[name] = value

    def get_uniform(self, name: str, default: object = None) -> object:
        """Retrieve a uniform value."""
        return self.uniforms.get(name, default)


class RenderPipeline:
    """Central render pipeline.

    Accumulates draw commands each frame, sorts them by layer and
    order_hint, then dispatches them in order.
    """

    def __init__(self, screen_width: int = 1920, screen_height: int = 1080) -> None:
        self.screen_width: int = screen_width
        self.screen_height: int = screen_height
        self.camera: Camera = Camera()
        self._command_queue: List[RenderCommand] = []
        self._shaders: Dict[str, Shader] = {}
        self.ambient_light: Color = Color(30, 30, 30)
        self.frame_count: int = 0

    # ------------------------------------------------------------------ #
    # Shader registry                                                      #
    # ------------------------------------------------------------------ #

    def register_shader(self, shader: Shader) -> None:
        """Register a shader for use in the pipeline."""
        self._shaders[shader.name] = shader

    def get_shader(self, name: str) -> Optional[Shader]:
        """Retrieve a registered shader by name."""
        return self._shaders.get(name)

    # ------------------------------------------------------------------ #
    # Command queue                                                        #
    # ------------------------------------------------------------------ #

    def submit(
        self,
        layer: RenderLayer,
        callback: Callable[[], None],
        order_hint: int = 0,
    ) -> None:
        """Submit a render command to be executed this frame.

        Args:
            layer: The render layer this command belongs to.
            callback: Zero-argument callable that performs the actual draw.
            order_hint: Fine-grained sort key within the same layer.
        """
        self._command_queue.append(
            RenderCommand(layer=layer, callback=callback, order_hint=order_hint)
        )

    def flush(self) -> None:
        """Sort and execute all queued render commands, then clear the queue."""
        self._command_queue.sort(
            key=lambda cmd: (cmd.layer.value, cmd.order_hint)
        )
        for command in self._command_queue:
            command.callback()
        self._command_queue.clear()
        self.frame_count += 1

    def begin_frame(self) -> None:
        """Called at the start of each frame to prepare the pipeline."""
        self._command_queue.clear()

    def end_frame(self) -> None:
        """Called at the end of each frame to flush the pipeline."""
        self.flush()

    @property
    def pending_command_count(self) -> int:
        """Return the number of commands pending in the queue."""
        return len(self._command_queue)

    def __repr__(self) -> str:
        return (
            f"RenderPipeline(size={self.screen_width}x{self.screen_height}, "
            f"frame={self.frame_count}, "
            f"pending={self.pending_command_count})"
        )
