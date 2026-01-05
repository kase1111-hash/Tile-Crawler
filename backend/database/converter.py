"""
State Converter for Tile-Crawler

Converts between game state classes and database models.
"""

from typing import Optional

from .models import (
    GameSave, PlayerData, WorldData, InventoryData, NarrativeData,
    CombatData, RoomRecord, InventoryItem, NarrativeEvent
)


class StateConverter:
    """Converts between game state objects and database models."""

    @staticmethod
    def player_to_data(player_state) -> PlayerData:
        """Convert PlayerState to PlayerData."""
        return PlayerData(
            name=player_state.name,
            level=player_state.level,
            experience=player_state.experience,
            experience_to_next=player_state.experience_to_next,
            stats={
                "max_hp": player_state.stats.max_hp,
                "current_hp": player_state.stats.current_hp,
                "max_mana": player_state.stats.max_mana,
                "current_mana": player_state.stats.current_mana,
                "base_attack": player_state.stats.base_attack,
                "base_defense": player_state.stats.base_defense,
                "base_speed": player_state.stats.base_speed,
                "base_magic": player_state.stats.base_magic,
            },
            status_effects=[
                {
                    "id": e.id,
                    "name": e.name,
                    "effect_type": e.effect_type,
                    "stat_modifiers": e.stat_modifiers,
                    "damage_per_turn": e.damage_per_turn,
                    "heal_per_turn": e.heal_per_turn,
                    "duration": e.duration,
                    "source": e.source,
                }
                for e in player_state.status_effects
            ],
            deaths=player_state.deaths,
            enemies_defeated=player_state.enemies_defeated,
            steps_taken=player_state.steps_taken,
            is_alive=player_state.is_alive,
        )

    @staticmethod
    def data_to_player(data: PlayerData, player_state) -> None:
        """Load PlayerData into PlayerState."""
        from player_state import PlayerStats, StatusEffect

        player_state.name = data.name
        player_state.level = data.level
        player_state.experience = data.experience
        player_state.experience_to_next = data.experience_to_next
        player_state.stats = PlayerStats(**data.stats)
        player_state.status_effects = [
            StatusEffect(**e) for e in data.status_effects
        ]
        player_state.deaths = data.deaths
        player_state.enemies_defeated = data.enemies_defeated
        player_state.steps_taken = data.steps_taken
        player_state.is_alive = data.is_alive

    @staticmethod
    def world_to_data(world_state) -> WorldData:
        """Convert WorldState to WorldData."""
        rooms = []
        for coord_key, room in world_state.rooms.items():
            # Parse coordinate from key
            parts = coord_key.split(",")
            x, y, z = int(parts[0]), int(parts[1]), int(parts[2])

            rooms.append(RoomRecord(
                x=x, y=y, z=z,
                biome=room.biome,
                description=room.description,
                tiles=room.map,  # RoomData uses 'map' field
                exits=room.exits,
                enemies=[e if isinstance(e, dict) else e.model_dump() for e in room.enemies],
                items=[i if isinstance(i, dict) else i.model_dump() if hasattr(i, 'model_dump') else i for i in room.items],
                npcs=room.npcs,
                features=room.features,
                visited=room.visited,
                cleared=room.cleared,
            ))

        # WorldState uses current_position tuple
        pos = world_state.current_position
        return WorldData(
            current_x=pos[0],
            current_y=pos[1],
            current_z=pos[2],
            rooms=rooms,
            explored_count=world_state.explored_count,
        )

    @staticmethod
    def data_to_world(data: WorldData, world_state) -> None:
        """Load WorldData into WorldState."""
        from world_state import RoomData

        # WorldState uses current_position tuple
        world_state.current_position = (data.current_x, data.current_y, data.current_z)
        world_state.explored_count = data.explored_count
        world_state.rooms = {}

        for room in data.rooms:
            key = f"{room.x},{room.y},{room.z}"
            world_state.rooms[key] = RoomData(
                x=room.x,
                y=room.y,
                z=room.z,
                biome=room.biome,
                description=room.description,
                map=room.tiles,  # RoomData uses 'map' field
                exits=room.exits,
                enemies=room.enemies,
                items=room.items,
                npcs=room.npcs,
                features=room.features,
                visited=room.visited,
                cleared=room.cleared,
            )

    @staticmethod
    def inventory_to_data(inventory_state) -> InventoryData:
        """Convert InventoryState to InventoryData."""
        items = []
        for item in inventory_state.items.values():
            items.append(InventoryItem(
                id=item.id,
                name=item.name,
                description=item.description,
                category=item.category,
                quantity=item.quantity,
                equipped=item.equipped,
                stats={},  # InventoryItem doesn't have stats field
            ))

        return InventoryData(
            items=items,
            gold=inventory_state.gold,
            max_slots=inventory_state.max_slots,
        )

    @staticmethod
    def data_to_inventory(data: InventoryData, inventory_state) -> None:
        """Load InventoryData into InventoryState."""
        from inventory_state import InventoryItem as InvItem

        inventory_state.items = {}
        inventory_state.gold = data.gold
        inventory_state.max_slots = data.max_slots

        for item in data.items:
            inventory_state.items[item.id] = InvItem(
                id=item.id,
                name=item.name,
                description=item.description,
                category=item.category,
                quantity=item.quantity,
                equipped=item.equipped,
            )

    @staticmethod
    def narrative_to_data(narrative_memory) -> NarrativeData:
        """Convert NarrativeMemory to NarrativeData."""
        events = []
        for event in narrative_memory.events:
            events.append(NarrativeEvent(
                event_type=event.event_type,
                description=event.description,
                timestamp=event.timestamp,
                location=event.location,
                actors=event.actors,
                items=event.items,
                importance=event.importance,
            ))

        return NarrativeData(
            events=events,
            story_summary=narrative_memory.story_summary,
            current_tone=narrative_memory.current_tone,
            active_threads=narrative_memory.active_threads,
            discovered_lore=narrative_memory.discovered_lore,
            max_events=narrative_memory.max_events,
        )

    @staticmethod
    def data_to_narrative(data: NarrativeData, narrative_memory) -> None:
        """Load NarrativeData into NarrativeMemory."""
        from narrative_memory import NarrativeEvent as NarrEvent

        narrative_memory.events = [
            NarrEvent(
                event_type=e.event_type,
                description=e.description,
                timestamp=e.timestamp,
                location=e.location,
                actors=e.actors,
                items=e.items,
                importance=e.importance,
            )
            for e in data.events
        ]
        narrative_memory.story_summary = data.story_summary
        narrative_memory.current_tone = data.current_tone
        narrative_memory.active_threads = data.active_threads
        narrative_memory.discovered_lore = data.discovered_lore
        narrative_memory.max_events = data.max_events

    @staticmethod
    def combat_to_data(combat_state) -> Optional[CombatData]:
        """Convert CombatState to CombatData."""
        if combat_state is None:
            return None

        return CombatData(
            in_combat=combat_state.in_combat,
            enemy_index=combat_state.enemy_index,
            enemy_id=combat_state.enemy_id,
            enemy_name=combat_state.enemy_name,
            enemy_hp=combat_state.enemy_hp,
            enemy_max_hp=combat_state.enemy_max_hp,
            enemy_attack=combat_state.enemy_attack,
            enemy_defense=combat_state.enemy_defense,
            turn=combat_state.turn,
        )

    @staticmethod
    def data_to_combat(data: Optional[CombatData]):
        """Convert CombatData to CombatState."""
        if data is None:
            return None

        from game_engine import CombatState

        return CombatState(
            in_combat=data.in_combat,
            enemy_index=data.enemy_index,
            enemy_id=data.enemy_id,
            enemy_name=data.enemy_name,
            enemy_hp=data.enemy_hp,
            enemy_max_hp=data.enemy_max_hp,
            enemy_attack=data.enemy_attack,
            enemy_defense=data.enemy_defense,
            turn=data.turn,
        )
