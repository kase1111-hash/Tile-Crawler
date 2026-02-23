"""
Game Engine for Tile-Crawler

Core game orchestration: new game, movement, room generation, state management.
Delegates combat to CombatEngine and interactions to InteractionEngine.
"""

import json
import logging
import os
import random
from typing import Optional

logger = logging.getLogger(__name__)

from world_state import WorldState, RoomData
from narrative_memory import NarrativeMemory
from inventory_state import InventoryState
from player_state import PlayerState
from llm_engine import get_llm_engine
from database import get_repository, GameSave
from database.converter import StateConverter
from combat_engine import CombatEngine, CombatState, ActionResult
from interaction_engine import InteractionEngine
from exceptions import CombatActiveError, InvalidDirectionError, NoExitError, RoomGenerationError


# =============================================================================
# Dungeon Generation Constants
# =============================================================================

# 50% new-exit chance produces ~2-3 exits per room on average, giving
# the dungeon a branching-corridor feel without becoming an open grid.
# Lower values make linear hallways; higher values make open plazas.
NEW_EXIT_CHANCE = 0.5
STAIRS_SPAWN_CHANCE = 0.1  # 10% — stairs are rare enough to feel like events
MAX_DUNGEON_DEPTH = 10


class GameEngine:
    """
    Main game engine orchestrating all game logic.

    Delegates combat to CombatEngine and interactions to InteractionEngine.
    Owns game flow: new game, movement, room generation, save/load.
    """

    def __init__(
        self,
        world: WorldState,
        narrative: NarrativeMemory,
        inventory: InventoryState,
        player: PlayerState,
    ):
        self.world = world
        self.narrative = narrative
        self.inventory = inventory
        self.player = player
        self.llm = get_llm_engine()

        # Load data files
        self.item_data = self._load_item_data()
        self.enemy_data = self._load_enemy_data()

        # Create sub-engines
        self.combat_engine = CombatEngine(
            player=self.player,
            narrative=self.narrative,
            world=self.world,
            llm=self.llm,
            enemy_data=self.enemy_data,
            inventory=self.inventory,
        )
        self.interaction_engine = InteractionEngine(
            player=self.player,
            narrative=self.narrative,
            world=self.world,
            llm=self.llm,
            item_data=self.item_data,
            inventory=self.inventory,
            combat_engine=self.combat_engine,
        )

    # ---- Backward-compatible property for combat state ----

    @property
    def combat(self) -> Optional[CombatState]:
        return self.combat_engine.combat

    @combat.setter
    def combat(self, value: Optional[CombatState]):
        self.combat_engine.combat = value

    # ---- Backward-compatible properties for interaction state ----

    @property
    def current_dialogue_npc(self) -> Optional[str]:
        return self.interaction_engine.current_dialogue_npc

    @current_dialogue_npc.setter
    def current_dialogue_npc(self, value: Optional[str]):
        self.interaction_engine.current_dialogue_npc = value

    @property
    def dialogue_history(self) -> list[str]:
        return self.interaction_engine.dialogue_history

    @dialogue_history.setter
    def dialogue_history(self, value: list[str]):
        self.interaction_engine.dialogue_history = value

    # ---- Data loading ----

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

    # =========================================================================
    # Game flow: new game, movement, room generation
    # =========================================================================

    async def new_game(self, player_name: str = "Adventurer") -> ActionResult:
        """Start a new game."""
        # Reset state in-place so session-specific objects are preserved
        # (calling global reset_*() functions would replace session state
        # with shared singletons, breaking multi-user isolation)
        self.world.reset()
        self.narrative.reset()
        self.inventory.reset()
        self.player.reset()

        self.player.name = player_name
        self.combat = None
        self.current_dialogue_npc = None
        self.dialogue_history = []

        # Re-bind sub-engines (references unchanged but keeps things consistent)
        self._rebind_sub_engines()

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
            raise CombatActiveError("Cannot move while in combat.")

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
            raise InvalidDirectionError(f"Invalid direction: {direction}")

        # Check if exit exists
        if current_room and not current_room.exits.get(direction, False):
            raise NoExitError(f"Cannot go {direction} — no exit in that direction.")

        # Calculate new coordinates
        dx, dy, dz = direction_map[direction]
        new_x, new_y, new_z = x + dx, y + dy, z + dz

        # Check if room exists, generate if not
        if not self.world.room_exists(new_x, new_y, new_z):
            biome = self._determine_biome(new_z)
            exits = self._determine_exits(new_x, new_y, new_z, direction)
            room = await self._generate_room(new_x, new_y, new_z, biome, exits)
            if not room:
                raise RoomGenerationError("Failed to generate room.")

        # Move player
        self.world.update_position(new_x, new_y, new_z)
        self.player.record_step()

        # Tick status effects (poison, buff expiry, etc.)
        self.player.process_status_effects()

        # Get new room
        new_room = self.world.get_current_room()

        # Record movement
        self.narrative.add_movement_event(
            direction=direction,
            from_loc=(x, y, z),
            to_loc=(new_x, new_y, new_z),
            room_description=new_room.description if new_room else ""
        )

        # Track features for theme detection
        if new_room and new_room.features:
            self.narrative.track_features(new_room.features)

        # Check for enemies
        combat_msg = ""
        has_combat = bool(new_room and new_room.enemies)
        if has_combat:
            enemy = new_room.enemies[0]
            combat_msg = f"\n\nA {enemy.get('name', 'creature')} blocks your path!"
            self.combat_engine.start_combat(0, enemy)

        # Track danger escalation
        self.narrative.record_room_entered(has_combat)

        # Trigger story summary update every 10 rooms
        if self.narrative.should_update_summary():
            recent_text = self.narrative.get_recent_events_text(10)
            if recent_text:
                new_summary = await self.llm.summarize_story(
                    events=recent_text.split("\n"),
                    current_summary=self.narrative.story_summary
                )
                self.narrative.update_summary(new_summary)
                self.narrative.mark_summary_updated()

        self._save_all()

        return ActionResult(
            success=True,
            message=f"Moved {direction}",
            narrative=(new_room.description if new_room else "You enter a new area.") + combat_msg,
            map_update=new_room.map if new_room else None,
            state_changes={"position": [new_x, new_y, new_z]},
            combat_data=self.combat.model_dump() if self.combat and self.combat.in_combat else None
        )

    # =========================================================================
    # Room generation helpers
    # =========================================================================

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
        opposite = {"north": "south", "south": "north", "east": "west", "west": "east", "up": "down", "down": "up"}
        exits = {opposite.get(from_direction, "south"): True}

        for direction in ["north", "south", "east", "west"]:
            if direction not in exits:
                dx, dy = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[direction]
                adj_room = self.world.get_room(x + dx, y + dy, z)
                if adj_room and adj_room.exits.get(opposite[direction], False):
                    exits[direction] = True
                elif random.random() < NEW_EXIT_CHANCE:
                    exits[direction] = True

        if z < MAX_DUNGEON_DEPTH and random.random() < STAIRS_SPAWN_CHANCE:
            exits["down"] = True
        if z > 0 and random.random() < STAIRS_SPAWN_CHANCE:
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
        narrative_context = self.narrative.get_context_for_llm()
        inventory_summary = self.inventory.get_inventory_summary()

        llm_response = await self.llm.generate_room(
            x, y, z, biome, exits, narrative_context, inventory_summary
        )

        if not llm_response:
            return None

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

    # =========================================================================
    # Delegated actions (combat + interactions)
    # =========================================================================

    async def attack(self) -> ActionResult:
        """Attack the current enemy (delegates to CombatEngine)."""
        result = await self.combat_engine.attack()
        self._save_all()
        return result

    async def flee(self) -> ActionResult:
        """Attempt to flee from combat (delegates to CombatEngine)."""
        result = await self.combat_engine.flee()
        self._save_all()
        return result

    async def take_item(self, item_id: str) -> ActionResult:
        """Pick up an item (delegates to InteractionEngine)."""
        result = await self.interaction_engine.take_item(item_id)
        self._save_all()
        return result

    async def use_item(self, item_id: str) -> ActionResult:
        """Use an item (delegates to InteractionEngine)."""
        result = await self.interaction_engine.use_item(item_id)
        self._save_all()
        return result

    async def talk(self, player_input: str = "") -> ActionResult:
        """Talk to an NPC (delegates to InteractionEngine)."""
        result = await self.interaction_engine.talk(player_input)
        self._save_all()
        return result

    async def rest(self) -> ActionResult:
        """Rest to recover (delegates to InteractionEngine)."""
        result = await self.interaction_engine.rest()
        self._save_all()
        return result

    # =========================================================================
    # State management
    # =========================================================================

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

    def _rebind_sub_engines(self) -> None:
        """Re-bind sub-engines to current state objects after reset."""
        self.combat_engine.player = self.player
        self.combat_engine.narrative = self.narrative
        self.combat_engine.world = self.world
        self.combat_engine.inventory = self.inventory

        self.interaction_engine.player = self.player
        self.interaction_engine.narrative = self.narrative
        self.interaction_engine.world = self.world
        self.interaction_engine.inventory = self.inventory

    # =========================================================================
    # Save/Load (database)
    # =========================================================================

    def save_to_database(self, player_id: str = "default", save_name: str = "autosave") -> int:
        """Save game state to database."""
        repo = get_repository()

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
        """Load game state from database."""
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

        # Update sub-engine references
        self._rebind_sub_engines()

        return True

    def list_saves(self, player_id: str = "default") -> list[dict]:
        """List all saves for a player."""
        repo = get_repository()
        return repo.list_saves(player_id)

    def delete_save(self, save_id: int) -> bool:
        """Delete a saved game."""
        repo = get_repository()
        return repo.delete_game(save_id)

    async def prefetch_adjacent_rooms(self) -> dict[str, bool]:
        """Pre-generate rooms for all available exits."""
        if self.combat and self.combat.in_combat:
            return {}

        current_room = self.world.get_current_room()
        if not current_room:
            return {}

        x, y, z = self.world.current_position
        results = {}

        direction_map = {
            "north": (0, -1, 0),
            "south": (0, 1, 0),
            "east": (1, 0, 0),
            "west": (-1, 0, 0),
            "up": (0, 0, -1),
            "down": (0, 0, 1)
        }

        for direction, (dx, dy, dz) in direction_map.items():
            if not current_room.exits.get(direction, False):
                continue

            new_x, new_y, new_z = x + dx, y + dy, z + dz

            if self.world.room_exists(new_x, new_y, new_z):
                results[direction] = True
                continue

            # TODO: rate-limit prefetch per session to prevent abuse
            try:
                biome = self._determine_biome(new_z)
                exits = self._determine_exits(new_x, new_y, new_z, direction)
                room = await self._generate_room(new_x, new_y, new_z, biome, exits)
                results[direction] = room is not None
            except Exception as e:
                logger.warning("Prefetch failed for %s: %s", direction, e)
                results[direction] = False

        return results


# =============================================================================
# Session-based game engine management
# =============================================================================

from session_manager import get_session_manager, GameSession

# Cache of game engines per session
_session_engines: dict[str, "GameEngine"] = {}
_engines_lock = None  # Will be initialized on first use


def _get_engines_lock():
    """Get or create the engines lock."""
    global _engines_lock
    import asyncio
    if _engines_lock is None:
        _engines_lock = asyncio.Lock()
    return _engines_lock


async def get_game_engine_for_session(session_id: str) -> "GameEngine":
    """
    Get a game engine for a specific session.
    Ensures each user has their own isolated game state.
    """
    lock = _get_engines_lock()
    async with lock:
        if session_id not in _session_engines:
            session_mgr = get_session_manager()
            session = await session_mgr.get_session(session_id)

            engine = GameEngine(
                world=session.world,
                narrative=session.narrative,
                inventory=session.inventory,
                player=session.player,
            )
            _session_engines[session_id] = engine

        return _session_engines[session_id]


async def reset_game_engine_for_session(session_id: str) -> "GameEngine":
    """Reset and return fresh game engine for a session."""
    lock = _get_engines_lock()
    async with lock:
        session_mgr = get_session_manager()
        session = await session_mgr.create_new_session(session_id)

        engine = GameEngine(
            world=session.world,
            narrative=session.narrative,
            inventory=session.inventory,
            player=session.player,
        )
        _session_engines[session_id] = engine
        return engine


def clear_session_engine(session_id: str) -> None:
    """Remove a session's engine from cache."""
    if session_id in _session_engines:
        del _session_engines[session_id]
