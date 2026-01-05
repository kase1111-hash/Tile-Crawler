"""
Game Engine for Tile-Crawler

Core game logic including movement, combat, interactions, and game state management.
"""

import json
import os
import random
from typing import Optional
from pydantic import BaseModel, Field

from world_state import get_world_state, reset_world_state, RoomData
from narrative_memory import get_narrative_memory, reset_narrative_memory
from inventory_state import get_inventory_state, reset_inventory_state
from player_state import get_player_state, reset_player_state, StatusEffect
from llm_engine import get_llm_engine
from database import get_repository, GameSave
from database.converter import StateConverter


class ActionResult(BaseModel):
    """Result of a game action."""
    success: bool
    message: str
    narrative: str = ""
    map_update: Optional[list[str]] = None
    state_changes: dict = Field(default_factory=dict)
    combat_data: Optional[dict] = None
    dialogue_data: Optional[dict] = None


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


class GameEngine:
    """
    Main game engine handling all game logic.
    """

    def __init__(self):
        self.world = get_world_state()
        self.narrative = get_narrative_memory()
        self.inventory = get_inventory_state()
        self.player = get_player_state()
        self.llm = get_llm_engine()

        self.combat: Optional[CombatState] = None
        self.current_dialogue_npc: Optional[str] = None
        self.dialogue_history: list[str] = []

        # Load item data for effects
        self.item_data = self._load_item_data()
        self.enemy_data = self._load_enemy_data()

    def _load_item_data(self) -> dict:
        """Load item definitions."""
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "items.json")
        if os.path.exists(data_path):
            with open(data_path, 'r') as f:
                return json.load(f).get("items", {})
        return {}

    def _load_enemy_data(self) -> dict:
        """Load enemy definitions."""
        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "enemies.json")
        if os.path.exists(data_path):
            with open(data_path, 'r') as f:
                return json.load(f).get("enemies", {})
        return {}

    async def new_game(self, player_name: str = "Adventurer") -> ActionResult:
        """Start a new game."""
        # Reset all states
        self.world = reset_world_state()
        self.narrative = reset_narrative_memory()
        self.inventory = reset_inventory_state()
        self.player = reset_player_state()

        self.player.name = player_name
        self.combat = None
        self.current_dialogue_npc = None
        self.dialogue_history = []

        # Generate starting room
        result = await self._generate_room(0, 0, 0, "dungeon", {"south": True})

        self.narrative.add_event(
            event_type="discovery",
            description=f"{player_name} enters the dungeon, beginning their descent into darkness.",
            location=(0, 0, 0),
            importance=5
        )

        self._save_all()

        return ActionResult(
            success=True,
            message="A new adventure begins...",
            narrative=result.description if result else "You stand at the entrance of an ancient dungeon.",
            map_update=result.map if result else None,
            state_changes={"new_game": True}
        )

    async def move(self, direction: str) -> ActionResult:
        """Move the player in a direction."""
        if self.combat and self.combat.in_combat:
            return ActionResult(
                success=False,
                message="Cannot move while in combat!",
                narrative="You must defeat the enemy or flee before moving on."
            )

        # Get current position and room
        x, y, z = self.world.current_position
        current_room = self.world.get_current_room()

        # Calculate new position
        direction_map = {
            "north": (0, -1, 0),
            "south": (0, 1, 0),
            "east": (1, 0, 0),
            "west": (-1, 0, 0),
            "up": (0, 0, -1),
            "down": (0, 0, 1)
        }

        if direction not in direction_map:
            return ActionResult(
                success=False,
                message=f"Invalid direction: {direction}",
                narrative="You're not sure which way that is."
            )

        # Check if exit exists
        if current_room and not current_room.exits.get(direction, False):
            return ActionResult(
                success=False,
                message=f"Cannot go {direction} - no exit.",
                narrative="A solid wall blocks your path in that direction."
            )

        # Calculate new coordinates
        dx, dy, dz = direction_map[direction]
        new_x, new_y, new_z = x + dx, y + dy, z + dz

        # Check if room exists, generate if not
        if not self.world.room_exists(new_x, new_y, new_z):
            # Determine biome (for now, inherit or use depth)
            biome = self._determine_biome(new_z)
            exits = self._determine_exits(new_x, new_y, new_z, direction)
            room = await self._generate_room(new_x, new_y, new_z, biome, exits)
            if not room:
                return ActionResult(
                    success=False,
                    message="Failed to generate room",
                    narrative="Something blocks your path. The dungeon itself seems to resist."
                )

        # Move player
        self.world.update_position(new_x, new_y, new_z)
        self.player.record_step()

        # Get new room
        new_room = self.world.get_current_room()

        # Record movement
        self.narrative.add_movement_event(
            direction=direction,
            from_loc=(x, y, z),
            to_loc=(new_x, new_y, new_z),
            room_description=new_room.description if new_room else ""
        )

        # Check for enemies
        combat_msg = ""
        if new_room and new_room.enemies:
            enemy = new_room.enemies[0]
            combat_msg = f"\n\nA {enemy.get('name', 'creature')} blocks your path!"
            self._start_combat(0, enemy)

        self._save_all()

        return ActionResult(
            success=True,
            message=f"Moved {direction}",
            narrative=(new_room.description if new_room else "You enter a new area.") + combat_msg,
            map_update=new_room.map if new_room else None,
            state_changes={"position": [new_x, new_y, new_z]},
            combat_data=self.combat.model_dump() if self.combat and self.combat.in_combat else None
        )

    def _determine_biome(self, depth: int) -> str:
        """Determine biome based on depth."""
        if depth <= 2:
            return random.choice(["dungeon", "cave"])
        elif depth <= 5:
            return random.choice(["dungeon", "crypt", "ruins"])
        elif depth <= 7:
            return random.choice(["temple", "ruins", "crypt"])
        elif depth <= 9:
            return random.choice(["volcano", "temple"])
        else:
            return "void"

    def _determine_exits(self, x: int, y: int, z: int, from_direction: str) -> dict[str, bool]:
        """Determine available exits for a new room."""
        # Always have the entrance we came from
        opposite = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
        exits = {opposite.get(from_direction, "south"): True}

        # Random chance for other exits
        for direction in ["north", "south", "east", "west"]:
            if direction not in exits:
                # Check if adjacent room exists and has matching exit
                dx, dy = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[direction]
                adj_room = self.world.get_room(x + dx, y + dy, z)
                if adj_room and adj_room.exits.get(opposite[direction], False):
                    exits[direction] = True
                elif random.random() < 0.5:  # 50% chance for new exits
                    exits[direction] = True

        # Chance for stairs
        if z < 10 and random.random() < 0.1:
            exits["down"] = True
        if z > 0 and random.random() < 0.1:
            exits["up"] = True

        return exits

    async def _generate_room(
        self,
        x: int,
        y: int,
        z: int,
        biome: str,
        exits: dict[str, bool]
    ) -> Optional[RoomData]:
        """Generate a new room using the LLM."""
        # Get context
        narrative_context = self.narrative.get_context_for_llm()
        inventory_summary = self.inventory.get_inventory_summary()

        # Generate via LLM
        llm_response = await self.llm.generate_room(
            x, y, z, biome, exits, narrative_context, inventory_summary
        )

        if not llm_response:
            return None

        # Create room data
        room = RoomData(
            x=x, y=y, z=z,
            map=llm_response.map,
            description=llm_response.description,
            biome=biome,
            exits=exits,
            enemies=llm_response.enemies,
            items=llm_response.items,
            npcs=llm_response.npcs,
            features=llm_response.features,
            visited=True
        )

        self.world.set_room(room)
        return room

    def _start_combat(self, enemy_index: int, enemy: dict) -> None:
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
            return ActionResult(
                success=False,
                message="Not in combat!",
                narrative="There is nothing to attack here."
            )

        # Calculate player damage
        player_attack = self.player.get_effective_stat("attack")
        # Add equipment bonuses here when implemented

        # Calculate damage (attack - defense/2, minimum 1)
        damage = max(1, player_attack - self.combat.enemy_defense // 2)

        # Apply critical hit chance
        if random.random() < 0.05:  # 5% crit chance
            damage *= 2
            crit_msg = " Critical hit!"
        else:
            crit_msg = ""

        # Apply damage to enemy
        self.combat.enemy_hp -= damage

        # Check if enemy defeated
        if self.combat.enemy_hp <= 0:
            return await self._end_combat_victory()

        # Enemy counterattack
        enemy_damage = max(1, self.combat.enemy_attack - self.player.get_effective_stat("defense") // 2)
        actual_damage, is_dead, damage_msg = self.player.take_damage(enemy_damage, self.combat.enemy_name)

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

        self.combat.turn += 1
        self._save_all()

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
        loot_msg = ""
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

        self._save_all()

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

        # Move to starting position (simplified - would ideally be last safe room)
        self.world.update_position(0, 0, 0)

        # Lose some gold
        gold_lost = self.inventory.gold // 4
        if gold_lost > 0:
            self.inventory.remove_gold(gold_lost)

        self._save_all()

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
            return ActionResult(
                success=False,
                message="Not in combat!",
                narrative="There's nothing to flee from."
            )

        # Calculate flee chance (base 50% + speed bonus)
        flee_chance = 50 + self.player.get_effective_stat("speed") * 5
        flee_roll = random.randint(1, 100)

        if flee_roll <= flee_chance:
            # Successful flee
            self.combat = None

            # Take one hit on the way out
            enemy_name = self.combat.enemy_name if self.combat else "enemy"

            self._save_all()

            return ActionResult(
                success=True,
                message="Escaped!",
                narrative=f"You manage to slip away from the {enemy_name}. It does not pursue.",
                state_changes={"combat_ended": True, "fled": True}
            )
        else:
            # Failed flee - enemy gets free attack
            if self.combat:
                enemy_damage = max(1, self.combat.enemy_attack)
                actual_damage, is_dead, damage_msg = self.player.take_damage(enemy_damage, self.combat.enemy_name)

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

    async def take_item(self, item_id: str) -> ActionResult:
        """Pick up an item from the current room."""
        if self.combat and self.combat.in_combat:
            return ActionResult(
                success=False,
                message="Cannot pick up items during combat!",
                narrative="Focus on the battle at hand!"
            )

        room = self.world.get_current_room()
        if not room:
            return ActionResult(
                success=False,
                message="No room found",
                narrative="Something is wrong..."
            )

        # Find item in room
        item_found = None
        for item in room.items:
            if item.get("id") == item_id:
                item_found = item
                break

        if not item_found:
            return ActionResult(
                success=False,
                message=f"Item '{item_id}' not found in this room",
                narrative="You don't see that item here."
            )

        # Get item data
        item_template = self.item_data.get(item_id, {})
        item_name = item_found.get("name", item_template.get("name", item_id))
        item_desc = item_template.get("description", "")
        category = item_template.get("category", "misc")
        stackable = item_template.get("stackable", True)
        max_stack = item_template.get("max_stack", 99)
        slot = item_template.get("slot")

        # Add to inventory
        success, msg = self.inventory.add_item(
            item_id=item_id,
            name=item_name,
            description=item_desc,
            category=category,
            quantity=item_found.get("quantity", 1),
            stackable=stackable,
            max_stack=max_stack,
            slot=slot
        )

        if success:
            # Remove from room
            x, y, z = self.world.current_position
            self.world.remove_item_from_room(x, y, z, item_id)

            # Record event
            self.narrative.add_item_event(
                action="picked up",
                item_name=item_name,
                location=(x, y, z)
            )

            # Generate description
            desc = await self.llm.generate_item_description(
                item_id, item_name, f"Picked up in a {room.biome} room"
            )

            self._save_all()

            return ActionResult(
                success=True,
                message=msg,
                narrative=desc,
                state_changes={"item_added": item_id}
            )

        return ActionResult(
            success=False,
            message=msg,
            narrative="You couldn't pick that up."
        )

    async def use_item(self, item_id: str) -> ActionResult:
        """Use an item from inventory."""
        success, msg, effect_data = self.inventory.use_item(item_id)

        if not success:
            return ActionResult(
                success=False,
                message=msg,
                narrative="You can't use that."
            )

        # Process item effect
        item_template = self.item_data.get(item_id, {})
        effect = item_template.get("effect", {})
        effect_type = effect.get("type", "")
        effect_msg = ""

        if effect_type == "heal":
            heal_amount = effect.get("value", 30)
            actual_heal, heal_msg = self.player.heal(heal_amount, effect_data["item_name"])
            effect_msg = heal_msg

        elif effect_type == "restore_mana":
            mana_amount = effect.get("value", 25)
            actual_restore, mana_msg = self.player.restore_mana(mana_amount)
            effect_msg = mana_msg

        elif effect_type == "cure_poison":
            self.player.remove_status_effect("poison")
            effect_msg = "The poison fades from your system."

        elif effect_type == "buff":
            stat = effect.get("stat", "attack")
            value = effect.get("value", 5)
            duration = effect.get("duration", 10)
            buff = StatusEffect(
                id=f"buff_{stat}",
                name=f"{stat.capitalize()} Boost",
                effect_type="buff",
                stat_modifiers={stat: value},
                duration=duration,
                source=effect_data["item_name"]
            )
            effect_msg = self.player.add_status_effect(buff)

        elif effect_type == "escape":
            if self.combat and self.combat.in_combat:
                # Guaranteed escape with smoke bomb etc
                self.combat = None
                effect_msg = "You vanish in a cloud of smoke and escape!"
            else:
                effect_msg = "The smoke dissipates uselessly."

        # Record event
        x, y, z = self.world.current_position
        self.narrative.add_item_event(
            action="used",
            item_name=effect_data["item_name"],
            location=(x, y, z),
            effect=effect_msg
        )

        self._save_all()

        return ActionResult(
            success=True,
            message=msg,
            narrative=effect_msg or f"You used the {effect_data['item_name']}.",
            state_changes={"item_used": item_id}
        )

    async def talk(self, player_input: str = "") -> ActionResult:
        """Talk to an NPC in the current room."""
        if self.combat and self.combat.in_combat:
            return ActionResult(
                success=False,
                message="Cannot talk during combat!",
                narrative="Now is not the time for conversation!"
            )

        room = self.world.get_current_room()
        if not room or not room.npcs:
            return ActionResult(
                success=False,
                message="No one to talk to here",
                narrative="You speak to the empty room. The dungeon does not answer."
            )

        # Get NPC data
        npc_id = room.npcs[0]  # Talk to first NPC
        npc_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "npcs.json")
        npc_data = {}
        if os.path.exists(npc_data_path):
            with open(npc_data_path, 'r') as f:
                all_npcs = json.load(f)
                npc_data = all_npcs.get("npcs", {}).get(npc_id, {})

        npc_name = npc_data.get("name", "Stranger")
        personality = npc_data.get("personality", "mysterious")

        # Generate dialogue
        narrative_context = self.narrative.get_context_for_llm()
        response = await self.llm.generate_dialogue(
            npc_id=npc_id,
            npc_name=npc_name,
            personality=personality,
            player_input=player_input or "Hello",
            narrative_context=narrative_context,
            dialogue_history=self.dialogue_history
        )

        # Record in history
        if player_input:
            self.dialogue_history.append(f"You: {player_input}")
        self.dialogue_history.append(f"{npc_name}: {response.speech}")

        # Keep history manageable
        if len(self.dialogue_history) > 10:
            self.dialogue_history = self.dialogue_history[-10:]

        # Record event
        x, y, z = self.world.current_position
        self.narrative.add_dialogue_event(
            npc_name=npc_name,
            summary=response.speech[:100],
            location=(x, y, z)
        )

        self._save_all()

        return ActionResult(
            success=True,
            message=f"Talking to {npc_name}",
            narrative=f'{npc_name}: "{response.speech}"',
            dialogue_data={
                "npc_id": npc_id,
                "npc_name": npc_name,
                "speech": response.speech,
                "mood": response.mood,
                "hints": response.hints,
                "trade_available": response.trade_available
            }
        )

    def rest(self) -> ActionResult:
        """Rest to recover HP/mana (only in safe rooms)."""
        room = self.world.get_current_room()

        # Check if room is safe (has campfire or is designated safe)
        is_safe = room and ("campfire" in room.features or "safe_room" in room.features)

        if not is_safe:
            return ActionResult(
                success=False,
                message="Cannot rest here - not safe!",
                narrative="This place is too dangerous to rest. Find a safe room first."
            )

        if self.combat and self.combat.in_combat:
            return ActionResult(
                success=False,
                message="Cannot rest during combat!",
                narrative="The enemy won't let you rest!"
            )

        rest_msg = self.player.full_rest()

        x, y, z = self.world.current_position
        self.narrative.add_event(
            event_type="rest",
            description="Rested at a safe location.",
            location=(x, y, z)
        )

        self._save_all()

        return ActionResult(
            success=True,
            message="Rested and recovered",
            narrative=f"You rest by the fire, recovering your strength. {rest_msg}",
            state_changes={"rested": True}
        )

    def get_game_state(self) -> dict:
        """Get the complete current game state for the frontend."""
        room = self.world.get_current_room()

        return {
            "player": self.player.get_stats_summary(),
            "position": list(self.world.current_position),
            "room": {
                "map": room.map if room else [],
                "description": room.description if room else "",
                "biome": room.biome if room else "unknown",
                "exits": room.exits if room else {},
                "enemies": room.enemies if room else [],
                "items": room.items if room else [],
                "npcs": room.npcs if room else [],
                "features": room.features if room else []
            },
            "inventory": self.inventory.get_inventory_list(),
            "gold": self.inventory.gold,
            "combat": self.combat.model_dump() if self.combat and self.combat.in_combat else None,
            "narrative": {
                "recent_events": self.narrative.get_recent_events_text(5),
                "story_summary": self.narrative.story_summary
            },
            "stats": {
                "rooms_explored": self.world.explored_count,
                "enemies_defeated": self.player.enemies_defeated,
                "steps_taken": self.player.steps_taken,
                "deaths": self.player.deaths
            }
        }

    def _save_all(self) -> None:
        """Save all game state to JSON files (legacy method)."""
        self.world.save()
        self.narrative.save()
        self.inventory.save()
        self.player.save()

    def save_to_database(self, player_id: str = "default", save_name: str = "autosave") -> int:
        """
        Save game state to database.

        Args:
            player_id: Unique identifier for the player
            save_name: Name for the save slot

        Returns:
            Save ID in database
        """
        repo = get_repository()

        # Convert current state to database models
        game_save = GameSave(
            player_id=player_id,
            save_name=save_name,
            player=StateConverter.player_to_data(self.player),
            world=StateConverter.world_to_data(self.world),
            inventory=StateConverter.inventory_to_data(self.inventory),
            narrative=StateConverter.narrative_to_data(self.narrative),
            combat=StateConverter.combat_to_data(self.combat),
        )

        return repo.save_game(game_save)

    def load_from_database(self, save_id: Optional[int] = None, player_id: str = "default") -> bool:
        """
        Load game state from database.

        Args:
            save_id: Specific save ID to load, or None for most recent
            player_id: Player ID to load saves for

        Returns:
            True if load was successful
        """
        repo = get_repository()
        save = repo.load_game(save_id, player_id)

        if save is None:
            return False

        # Restore state from database
        StateConverter.data_to_player(save.player, self.player)
        StateConverter.data_to_world(save.world, self.world)
        StateConverter.data_to_inventory(save.inventory, self.inventory)
        StateConverter.data_to_narrative(save.narrative, self.narrative)
        self.combat = StateConverter.data_to_combat(save.combat)

        # Update internal references
        self._player_state = self.player
        self._world_state = self.world
        self._inventory_state = self.inventory
        self._narrative_memory = self.narrative

        return True

    def list_saves(self, player_id: str = "default") -> list[dict]:
        """List all saves for a player."""
        repo = get_repository()
        return repo.list_saves(player_id)

    def delete_save(self, save_id: int) -> bool:
        """Delete a saved game."""
        repo = get_repository()
        return repo.delete_game(save_id)


# Global instance
_game_engine: Optional[GameEngine] = None


def get_game_engine() -> GameEngine:
    """Get the global game engine instance."""
    global _game_engine
    if _game_engine is None:
        _game_engine = GameEngine()
    return _game_engine


def reset_game_engine() -> GameEngine:
    """Reset and return fresh game engine."""
    global _game_engine
    _game_engine = GameEngine()
    return _game_engine
