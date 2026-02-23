"""
Combat Engine for Tile-Crawler

Handles all combat-related logic: starting combat, attacking, fleeing,
victory/defeat resolution.
"""

import random
from typing import Optional
from pydantic import BaseModel, Field

from player_state import PlayerState
from narrative_memory import NarrativeMemory
from world_state import WorldState
from inventory_state import InventoryState
from llm_engine import LLMEngine
from exceptions import NotInCombatError


# =============================================================================
# Combat Constants
# =============================================================================

CRITICAL_HIT_CHANCE = 0.05  # 5% chance for critical hit
CRITICAL_HIT_MULTIPLIER = 2  # Damage multiplier on critical
FLEE_BASE_CHANCE = 50  # Base percentage chance to flee
FLEE_SPEED_MODIFIER = 2  # Multiplier for speed difference


class CombatState(BaseModel):
    """Current combat state if in combat."""
    in_combat: bool = False
    enemy_index: int = -1
    enemy_id: str = ""
    enemy_name: str = ""
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_attack: int = 0
    enemy_defense: int = 0
    turn: int = 0


class ActionResult(BaseModel):
    """Result of a game action (imported from game_engine for shared use)."""
    success: bool
    message: str
    narrative: str = ""
    map_update: Optional[list[str]] = None
    state_changes: dict = Field(default_factory=dict)
    combat_data: Optional[dict] = None
    dialogue_data: Optional[dict] = None


class CombatEngine:
    """Handles all combat logic: attack, flee, victory, defeat."""

    def __init__(
        self,
        player: PlayerState,
        narrative: NarrativeMemory,
        world: WorldState,
        llm: LLMEngine,
        enemy_data: dict,
        inventory: InventoryState,
    ):
        self.player = player
        self.narrative = narrative
        self.world = world
        self.llm = llm
        self.enemy_data = enemy_data
        self.inventory = inventory
        self.combat: Optional[CombatState] = None

    def start_combat(self, enemy_index: int, enemy: dict) -> None:
        """Initialize combat with an enemy."""
        enemy_id = enemy.get("id", "unknown")
        enemy_template = self.enemy_data.get(enemy_id, {})

        self.combat = CombatState(
            in_combat=True,
            enemy_index=enemy_index,
            enemy_id=enemy_id,
            enemy_name=enemy.get("name", "Unknown Creature"),
            enemy_hp=enemy.get("hp", enemy_template.get("stats", {}).get("hp", 20)),
            enemy_max_hp=enemy.get("hp", enemy_template.get("stats", {}).get("hp", 20)),
            enemy_attack=enemy.get("attack", enemy_template.get("stats", {}).get("attack", 5)),
            enemy_defense=enemy.get("defense", enemy_template.get("stats", {}).get("defense", 2)),
            turn=1
        )

    async def attack(self) -> ActionResult:
        """Attack the current enemy."""
        if not self.combat or not self.combat.in_combat:
            raise NotInCombatError("Not in combat — there is nothing to attack here.")

        # Calculate player damage (base + status effects + equipment)
        equipment_stats = self.inventory.get_equipped_stats()
        player_attack = self.player.get_effective_stat("attack") + equipment_stats.get("attack", 0)

        # Calculate damage (attack - defense/2, minimum 1)
        damage = max(1, player_attack - self.combat.enemy_defense // 2)

        # Apply critical hit chance
        if random.random() < CRITICAL_HIT_CHANCE:
            damage *= CRITICAL_HIT_MULTIPLIER
            crit_msg = " Critical hit!"
        else:
            crit_msg = ""

        # Apply damage to enemy
        self.combat.enemy_hp -= damage

        # Check if enemy defeated
        if self.combat.enemy_hp <= 0:
            return await self._end_combat_victory()

        # Enemy counterattack — pass raw attack; take_damage applies defense
        enemy_damage = self.combat.enemy_attack
        equip_def = equipment_stats.get("defense", 0)
        actual_damage, is_dead, damage_msg = self.player.take_damage(enemy_damage, self.combat.enemy_name, equip_def)

        # Generate narration
        narration = await self.llm.generate_combat_narration(
            player_action="attack",
            enemy_name=self.combat.enemy_name,
            outcome=f"Dealt {damage} damage.{crit_msg} {damage_msg}",
            player_stats=self.player.get_combat_stats(),
            enemy_stats={"hp": self.combat.enemy_hp, "max_hp": self.combat.enemy_max_hp},
            is_victory=False,
            is_defeat=is_dead
        )

        if is_dead:
            return await self._end_combat_defeat()

        # Process status effects (poison tick, buff expiry, etc.)
        effect_msgs = self.player.process_status_effects()
        if effect_msgs and self.player.stats.current_hp <= 0:
            return await self._end_combat_defeat()

        self.combat.turn += 1

        return ActionResult(
            success=True,
            message=f"Dealt {damage} damage, took {actual_damage} damage",
            narrative=narration.narration,
            combat_data=self.combat.model_dump(),
            state_changes={"player_hp": self.player.stats.current_hp}
        )

    async def _end_combat_victory(self) -> ActionResult:
        """Handle combat victory."""
        enemy_name = self.combat.enemy_name
        enemy_id = self.combat.enemy_id

        # Get XP reward
        enemy_template = self.enemy_data.get(enemy_id, {})
        xp_reward = enemy_template.get("xp_reward", 25)

        # Award XP
        leveled, xp_msg = self.player.gain_experience(xp_reward)
        self.player.record_enemy_defeated()

        # Remove enemy from room
        x, y, z = self.world.current_position
        self.world.remove_enemy_from_room(x, y, z, self.combat.enemy_index)

        # Record event
        self.narrative.add_combat_event(
            enemy_name=enemy_name,
            outcome="Victory!",
            location=(x, y, z),
            details=f"Gained {xp_reward} XP."
        )

        # Generate loot (simplified)
        gold_drop = random.randint(5, 20)
        self.inventory.add_gold(gold_drop)
        loot_msg = f" Found {gold_drop} gold."

        # Generate victory narration
        narration = await self.llm.generate_combat_narration(
            player_action="final blow",
            enemy_name=enemy_name,
            outcome=f"The {enemy_name} falls!",
            player_stats=self.player.get_combat_stats(),
            enemy_stats={"hp": 0, "max_hp": self.combat.enemy_max_hp},
            is_victory=True,
            is_defeat=False
        )

        # Clear combat state
        self.combat = None

        return ActionResult(
            success=True,
            message=f"Defeated {enemy_name}! {xp_msg}{loot_msg}",
            narrative=narration.narration,
            state_changes={
                "combat_ended": True,
                "victory": True,
                "xp_gained": xp_reward,
                "gold_gained": gold_drop
            }
        )

    async def _end_combat_defeat(self) -> ActionResult:
        """Handle combat defeat (player death)."""
        enemy_name = self.combat.enemy_name
        x, y, z = self.world.current_position

        # Record death
        self.narrative.add_death_event(
            cause=f"Slain by {enemy_name}",
            location=(x, y, z)
        )

        # Clear combat
        self.combat = None

        # Handle respawn
        respawn_msg = self.player.respawn()

        # Move to starting position
        self.world.update_position(0, 0, 0)

        # Lose some gold
        gold_lost = self.inventory.gold // 4
        if gold_lost > 0:
            self.inventory.remove_gold(gold_lost)

        return ActionResult(
            success=False,
            message=f"Defeated by {enemy_name}...",
            narrative=f"Darkness claims you. {respawn_msg} You lost {gold_lost} gold.",
            state_changes={
                "combat_ended": True,
                "defeat": True,
                "respawned": True,
                "gold_lost": gold_lost
            }
        )

    async def flee(self) -> ActionResult:
        """Attempt to flee from combat."""
        if not self.combat or not self.combat.in_combat:
            raise NotInCombatError("Not in combat — there is nothing to flee from.")

        # Calculate flee chance (base chance + speed bonus)
        speed_bonus = self.player.get_effective_stat("speed") * FLEE_SPEED_MODIFIER
        flee_chance = FLEE_BASE_CHANCE + speed_bonus
        flee_roll = random.randint(1, 100)

        if flee_roll <= flee_chance:
            # Successful flee
            enemy_name = self.combat.enemy_name if self.combat else "enemy"
            self.combat = None

            return ActionResult(
                success=True,
                message="Escaped!",
                narrative=f"You manage to slip away from the {enemy_name}. It does not pursue.",
                state_changes={"combat_ended": True, "fled": True}
            )
        else:
            # Failed flee - enemy gets free attack
            if self.combat:
                enemy_damage = self.combat.enemy_attack
                equip_def = self.inventory.get_equipped_stats().get("defense", 0)
                actual_damage, is_dead, damage_msg = self.player.take_damage(enemy_damage, self.combat.enemy_name, equip_def)

                if is_dead:
                    return await self._end_combat_defeat()

                return ActionResult(
                    success=False,
                    message=f"Failed to flee! Took {actual_damage} damage.",
                    narrative=f"You try to escape but the {self.combat.enemy_name} blocks your path! {damage_msg}",
                    combat_data=self.combat.model_dump(),
                    state_changes={"player_hp": self.player.stats.current_hp}
                )

            return ActionResult(
                success=False,
                message="Failed to flee!",
                narrative="Your escape attempt fails."
            )
