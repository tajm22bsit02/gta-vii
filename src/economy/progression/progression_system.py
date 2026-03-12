"""Progression System - XP, skills, and character advancement."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Dict, List, Optional


class SkillCategory(Enum):
    """Groupings for character skills."""

    COMBAT = auto()
    DRIVING = auto()
    STEALTH = auto()
    ATHLETICS = auto()
    CHARISMA = auto()
    HACKING = auto()
    PILOTING = auto()


@dataclass
class Skill:
    """A single learnable skill."""

    skill_id: str
    name: str
    category: SkillCategory
    description: str
    level: int = 0
    max_level: int = 5
    xp_per_level: int = 1000
    current_xp: int = 0
    is_unlocked: bool = False
    prerequisites: List[str] = field(default_factory=list)

    @property
    def is_maxed(self) -> bool:
        return self.level >= self.max_level

    @property
    def xp_to_next_level(self) -> int:
        if self.is_maxed:
            return 0
        return self.xp_per_level * (self.level + 1) - self.current_xp

    @property
    def total_xp_required(self) -> int:
        return self.xp_per_level * self.max_level

    def add_xp(self, amount: int) -> int:
        """Add XP and return the number of levels gained."""
        if self.is_maxed or not self.is_unlocked:
            return 0
        self.current_xp += amount
        levels_gained = 0
        while not self.is_maxed and self.current_xp >= self.xp_per_level * (self.level + 1):
            self.level += 1
            levels_gained += 1
        return levels_gained

    def __repr__(self) -> str:
        return f"Skill({self.name!r}, lv={self.level}/{self.max_level})"


LevelUpCallback = Callable[[Skill, int], None]  # (skill, new_level)


class SkillTree:
    """A named tree of related skills (e.g. the Combat tree)."""

    def __init__(self, name: str, category: SkillCategory) -> None:
        self.name: str = name
        self.category: SkillCategory = category
        self._skills: Dict[str, Skill] = {}

    def add_skill(self, skill: Skill) -> None:
        self._skills[skill.skill_id] = skill

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    @property
    def skills(self) -> List[Skill]:
        return list(self._skills.values())


class ProgressionSystem:
    """Manages player XP, level, and skill trees.

    Provides XP grant, skill unlocking, and perk activation
    based on the player's development path.
    """

    XP_PER_LEVEL: int = 5_000

    def __init__(self) -> None:
        self.player_level: int = 1
        self.player_xp: int = 0
        self._skill_trees: Dict[str, SkillTree] = {}
        self._all_skills: Dict[str, Skill] = {}
        self._level_up_callbacks: List[Callable[[int], None]] = []
        self._skill_level_up_callbacks: List[LevelUpCallback] = []
        self._build_default_skill_trees()

    def _build_default_skill_trees(self) -> None:
        """Create the default skill trees."""
        combat_tree = SkillTree("Combat Mastery", SkillCategory.COMBAT)
        combat_tree.add_skill(Skill(
            "faster_reload", "Faster Reload", SkillCategory.COMBAT,
            "Reduce reload time by 20% per level.", max_level=5, is_unlocked=True,
        ))
        combat_tree.add_skill(Skill(
            "improved_accuracy", "Improved Accuracy", SkillCategory.COMBAT,
            "Reduce weapon spread by 15% per level.", max_level=5,
            prerequisites=["faster_reload"],
        ))
        combat_tree.add_skill(Skill(
            "body_armour_boost", "Body Armour Boost", SkillCategory.COMBAT,
            "Increase armour capacity by 25% per level.", max_level=3, is_unlocked=True,
        ))

        driving_tree = SkillTree("Driving Expert", SkillCategory.DRIVING)
        driving_tree.add_skill(Skill(
            "speed_boost", "Speed Boost", SkillCategory.DRIVING,
            "Increase vehicle top speed by 5% per level.", max_level=5, is_unlocked=True,
        ))
        driving_tree.add_skill(Skill(
            "handling_master", "Handling Master", SkillCategory.DRIVING,
            "Improve handling rating by 10% per level.", max_level=5,
            prerequisites=["speed_boost"],
        ))

        stealth_tree = SkillTree("Shadow Ops", SkillCategory.STEALTH)
        stealth_tree.add_skill(Skill(
            "silent_takedown", "Silent Takedown", SkillCategory.STEALTH,
            "Execute undetected takedowns.", max_level=3, is_unlocked=True,
        ))

        for tree in (combat_tree, driving_tree, stealth_tree):
            self._skill_trees[tree.name] = tree
            for skill in tree.skills:
                self._all_skills[skill.skill_id] = skill

    def grant_xp(self, amount: int) -> int:
        """Award XP to the player.

        Returns:
            Number of player levels gained.
        """
        self.player_xp += amount
        levels_gained = 0
        while self.player_xp >= self.XP_PER_LEVEL * self.player_level:
            self.player_level += 1
            levels_gained += 1
            self._unlock_skills_for_level(self.player_level)
            for cb in self._level_up_callbacks:
                cb(self.player_level)
        return levels_gained

    def grant_skill_xp(self, skill_id: str, amount: int) -> int:
        """Grant XP to a specific skill.

        Returns:
            Number of skill levels gained.
        """
        skill = self._all_skills.get(skill_id)
        if skill is None:
            return 0
        levels = skill.add_xp(amount)
        for cb in self._skill_level_up_callbacks:
            cb(skill, skill.level)
        return levels

    def unlock_skill(self, skill_id: str) -> bool:
        """Manually unlock a skill if prerequisites are met."""
        skill = self._all_skills.get(skill_id)
        if skill is None or skill.is_unlocked:
            return False
        for prereq_id in skill.prerequisites:
            prereq = self._all_skills.get(prereq_id)
            if prereq is None or not prereq.is_unlocked or prereq.level < 1:
                return False
        skill.is_unlocked = True
        return True

    def _unlock_skills_for_level(self, level: int) -> None:
        """Auto-unlock skills tied to player level milestones."""
        milestone_unlocks: Dict[int, List[str]] = {
            3: ["improved_accuracy"],
            5: ["handling_master"],
        }
        for skill_id in milestone_unlocks.get(level, []):
            self.unlock_skill(skill_id)

    def on_level_up(self, callback: Callable[[int], None]) -> None:
        self._level_up_callbacks.append(callback)

    def on_skill_level_up(self, callback: LevelUpCallback) -> None:
        self._skill_level_up_callbacks.append(callback)

    @property
    def xp_to_next_level(self) -> int:
        return self.XP_PER_LEVEL * self.player_level - self.player_xp

    @property
    def unlocked_skills(self) -> List[Skill]:
        return [s for s in self._all_skills.values() if s.is_unlocked]

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self._all_skills.get(skill_id)

    def __repr__(self) -> str:
        return (
            f"ProgressionSystem("
            f"level={self.player_level}, "
            f"xp={self.player_xp}, "
            f"skills={len(self.unlocked_skills)} unlocked)"
        )
