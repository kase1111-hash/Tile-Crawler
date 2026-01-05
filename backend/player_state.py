"""
Player State Management for Tile-Crawler

Handles player stats, health, experience, leveling, and status effects.
"""

import json
import os
from typing import Optional
from pydantic import BaseModel, Field


class StatusEffect(BaseModel):
    """An active status effect on the player."""
    id: str
    name: str
    effect_type: str  # buff, debuff, dot, hot
    stat_modifiers: dict[str, int] = Field(default_factory=dict)
    damage_per_turn: int = 0
    heal_per_turn: int = 0
    duration: int = 0  # Turns remaining, -1 for permanent
    source: str = ""


class PlayerStats(BaseModel):
    """Player's current stats."""
    max_hp: int = 100
    current_hp: int = 100
    max_mana: int = 50
    current_mana: int = 50
    base_attack: int = 5
    base_defense: int = 5
    base_speed: int = 5
    base_magic: int = 5


class PlayerState:
    """
    Manages the player's state including stats, level, and status effects.
    """

    def __init__(self, save_path: str = "player_state.json"):
        self.save_path = save_path
        self.name: str = "Adventurer"
        self.level: int = 1
        self.experience: int = 0
        self.experience_to_next: int = 100
        self.stats: PlayerStats = PlayerStats()
        self.status_effects: list[StatusEffect] = []
        self.deaths: int = 0
        self.enemies_defeated: int = 0
        self.steps_taken: int = 0
        self.is_alive: bool = True
        self._load()

    def _load(self) -> None:
        """Load player state from disk."""
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r') as f:
                    data = json.load(f)
                    self.name = data.get("name", "Adventurer")
                    self.level = data.get("level", 1)
                    self.experience = data.get("experience", 0)
                    self.experience_to_next = data.get("experience_to_next", 100)
                    self.stats = PlayerStats(**data.get("stats", {}))
                    self.status_effects = [
                        StatusEffect(**e) for e in data.get("status_effects", [])
                    ]
                    self.deaths = data.get("deaths", 0)
                    self.enemies_defeated = data.get("enemies_defeated", 0)
                    self.steps_taken = data.get("steps_taken", 0)
                    self.is_alive = data.get("is_alive", True)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load player state: {e}")
                self._init_default()
        else:
            self._init_default()

    def _init_default(self) -> None:
        """Initialize default player state."""
        self.name = "Adventurer"
        self.level = 1
        self.experience = 0
        self.experience_to_next = 100
        self.stats = PlayerStats()
        self.status_effects = []
        self.deaths = 0
        self.enemies_defeated = 0
        self.steps_taken = 0
        self.is_alive = True

    def save(self) -> None:
        """Save player state to disk."""
        data = {
            "name": self.name,
            "level": self.level,
            "experience": self.experience,
            "experience_to_next": self.experience_to_next,
            "stats": self.stats.model_dump(),
            "status_effects": [e.model_dump() for e in self.status_effects],
            "deaths": self.deaths,
            "enemies_defeated": self.enemies_defeated,
            "steps_taken": self.steps_taken,
            "is_alive": self.is_alive
        }
        with open(self.save_path, 'w') as f:
            json.dump(data, f, indent=2)

    def take_damage(self, amount: int, source: str = "unknown") -> tuple[int, bool, str]:
        """
        Apply damage to the player.
        Returns (actual_damage, is_dead, message).
        """
        # Apply defense reduction
        defense = self.get_effective_stat("defense")
        reduced_damage = max(1, amount - (defense // 2))

        self.stats.current_hp -= reduced_damage

        if self.stats.current_hp <= 0:
            self.stats.current_hp = 0
            self.is_alive = False
            self.deaths += 1
            return reduced_damage, True, f"Took {reduced_damage} damage from {source}. You have fallen!"

        return reduced_damage, False, f"Took {reduced_damage} damage from {source}. HP: {self.stats.current_hp}/{self.stats.max_hp}"

    def heal(self, amount: int, source: str = "unknown") -> tuple[int, str]:
        """
        Heal the player.
        Returns (actual_heal, message).
        """
        if not self.is_alive:
            return 0, "Cannot heal while dead"

        old_hp = self.stats.current_hp
        self.stats.current_hp = min(self.stats.max_hp, self.stats.current_hp + amount)
        actual_heal = self.stats.current_hp - old_hp

        return actual_heal, f"Healed {actual_heal} HP from {source}. HP: {self.stats.current_hp}/{self.stats.max_hp}"

    def use_mana(self, amount: int) -> tuple[bool, str]:
        """
        Use mana for a spell.
        Returns (success, message).
        """
        if self.stats.current_mana >= amount:
            self.stats.current_mana -= amount
            return True, f"Used {amount} mana. Mana: {self.stats.current_mana}/{self.stats.max_mana}"
        return False, f"Not enough mana (have {self.stats.current_mana}, need {amount})"

    def restore_mana(self, amount: int) -> tuple[int, str]:
        """Restore mana."""
        old_mana = self.stats.current_mana
        self.stats.current_mana = min(self.stats.max_mana, self.stats.current_mana + amount)
        actual_restore = self.stats.current_mana - old_mana
        return actual_restore, f"Restored {actual_restore} mana. Mana: {self.stats.current_mana}/{self.stats.max_mana}"

    def gain_experience(self, amount: int) -> tuple[bool, str]:
        """
        Gain experience points.
        Returns (leveled_up, message).
        """
        self.experience += amount
        messages = [f"Gained {amount} XP"]
        leveled_up = False

        while self.experience >= self.experience_to_next:
            self.experience -= self.experience_to_next
            self._level_up()
            leveled_up = True
            messages.append(f"Level up! Now level {self.level}")

        messages.append(f"XP: {self.experience}/{self.experience_to_next}")
        return leveled_up, " ".join(messages)

    def _level_up(self) -> None:
        """Process a level up."""
        self.level += 1

        # Increase stats
        self.stats.max_hp += 10
        self.stats.current_hp = self.stats.max_hp  # Full heal on level up
        self.stats.max_mana += 5
        self.stats.current_mana = self.stats.max_mana
        self.stats.base_attack += 2
        self.stats.base_defense += 2
        self.stats.base_speed += 1
        self.stats.base_magic += 1

        # Increase XP requirement (1.5x scaling)
        self.experience_to_next = int(self.experience_to_next * 1.5)

    def add_status_effect(self, effect: StatusEffect) -> str:
        """Add a status effect."""
        # Check for existing effect of same type
        for i, existing in enumerate(self.status_effects):
            if existing.id == effect.id:
                # Refresh duration
                self.status_effects[i] = effect
                return f"{effect.name} refreshed"

        self.status_effects.append(effect)
        return f"Affected by {effect.name}"

    def remove_status_effect(self, effect_id: str) -> bool:
        """Remove a status effect by ID."""
        for i, effect in enumerate(self.status_effects):
            if effect.id == effect_id:
                self.status_effects.pop(i)
                return True
        return False

    def process_status_effects(self) -> list[str]:
        """
        Process all status effects for a turn.
        Returns list of messages.
        """
        messages = []
        effects_to_remove = []

        for effect in self.status_effects:
            if effect.damage_per_turn > 0:
                damage, dead, msg = self.take_damage(effect.damage_per_turn, effect.name)
                messages.append(msg)
                if dead:
                    break

            if effect.heal_per_turn > 0:
                heal, msg = self.heal(effect.heal_per_turn, effect.name)
                messages.append(msg)

            # Decrease duration
            if effect.duration > 0:
                effect.duration -= 1
                if effect.duration == 0:
                    effects_to_remove.append(effect.id)
                    messages.append(f"{effect.name} wore off")

        for effect_id in effects_to_remove:
            self.remove_status_effect(effect_id)

        return messages

    def get_effective_stat(self, stat_name: str) -> int:
        """Get a stat with all modifiers applied."""
        base_value = getattr(self.stats, f"base_{stat_name}", 0)

        # Apply status effect modifiers
        for effect in self.status_effects:
            if stat_name in effect.stat_modifiers:
                base_value += effect.stat_modifiers[stat_name]

        return max(0, base_value)

    def respawn(self) -> str:
        """Respawn the player after death."""
        self.is_alive = True
        self.stats.current_hp = self.stats.max_hp // 2  # Respawn at half HP
        self.stats.current_mana = self.stats.max_mana // 2
        self.status_effects = []  # Clear all effects
        return "You awaken at the last safe point, weakened but alive."

    def full_rest(self) -> str:
        """Fully restore HP and mana (at safe rooms)."""
        self.stats.current_hp = self.stats.max_hp
        self.stats.current_mana = self.stats.max_mana
        return f"Fully rested. HP: {self.stats.current_hp}, Mana: {self.stats.current_mana}"

    def record_enemy_defeated(self) -> None:
        """Record an enemy defeat for stats."""
        self.enemies_defeated += 1

    def record_step(self) -> None:
        """Record a step taken for stats."""
        self.steps_taken += 1

    def get_stats_summary(self) -> dict:
        """Get player stats for display."""
        return {
            "name": self.name,
            "level": self.level,
            "hp": f"{self.stats.current_hp}/{self.stats.max_hp}",
            "mana": f"{self.stats.current_mana}/{self.stats.max_mana}",
            "xp": f"{self.experience}/{self.experience_to_next}",
            "attack": self.get_effective_stat("attack"),
            "defense": self.get_effective_stat("defense"),
            "speed": self.get_effective_stat("speed"),
            "magic": self.get_effective_stat("magic"),
            "status_effects": [e.name for e in self.status_effects]
        }

    def get_combat_stats(self) -> dict:
        """Get stats relevant for combat calculations."""
        return {
            "hp": self.stats.current_hp,
            "max_hp": self.stats.max_hp,
            "attack": self.get_effective_stat("attack"),
            "defense": self.get_effective_stat("defense"),
            "speed": self.get_effective_stat("speed"),
            "magic": self.get_effective_stat("magic")
        }

    def reset(self) -> None:
        """Reset player state for a new game."""
        self._init_default()
        if os.path.exists(self.save_path):
            os.remove(self.save_path)


# Global instance
_player_state: Optional[PlayerState] = None


def get_player_state() -> PlayerState:
    """Get the global player state instance."""
    global _player_state
    if _player_state is None:
        _player_state = PlayerState()
    return _player_state


def reset_player_state() -> PlayerState:
    """Reset and return fresh player state."""
    global _player_state
    if _player_state:
        _player_state.reset()
    _player_state = PlayerState()
    return _player_state
