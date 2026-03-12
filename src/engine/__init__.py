"""Core game engine module."""

from .ecs.entity import Entity
from .ecs.component import Component
from .ecs.system import System
from .ecs.world import ECSWorld
from .scene.scene_manager import SceneManager
from .physics.physics_engine import PhysicsEngine
from .renderer.render_pipeline import RenderPipeline

__all__ = [
    "Entity",
    "Component",
    "System",
    "ECSWorld",
    "SceneManager",
    "PhysicsEngine",
    "RenderPipeline",
]
