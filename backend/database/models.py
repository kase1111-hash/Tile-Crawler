"""
Database models for Tile-Crawler

Pydantic models representing game data structures for database storage.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class PlayerData(BaseModel):
    """Player state data for database storage."""
    name: str = "Adventurer"
    level: int = 1
    experience: int = 0
    experience_to_next: int = 100
    stats: dict[str, Any] = Field(default_factory=lambda: {
        "max_hp": 100,
        "current_hp": 100,
        "max_mana": 50,
        "current_mana": 50,
        "base_attack": 5,
        "base_defense": 5,
        "base_speed": 5,
        "base_magic": 5,
    })
    status_effects: list[dict[str, Any]] = Field(default_factory=list)
    deaths: int = 0
    enemies_defeated: int = 0
    steps_taken: int = 0
    is_alive: bool = True


class RoomRecord(BaseModel):
    """Individual room data for storage."""
    x: int
    y: int
    z: int
    biome: str
    description: str
    tiles: list[str]
    exits: dict[str, bool]
    enemies: list[dict[str, Any]]
    items: list[dict[str, Any]]
    npcs: list[str]
    features: list[str]
    visited: bool = False
    cleared: bool = False


class WorldData(BaseModel):
    """World state data for database storage."""
    current_x: int = 0
    current_y: int = 0
    current_z: int = 0
    rooms: list[RoomRecord] = Field(default_factory=list)
    explored_count: int = 0


class InventoryItem(BaseModel):
    """Single inventory item."""
    id: str
    name: str
    description: str = ""
    category: str = "misc"
    quantity: int = 1
    equipped: bool = False
    stats: dict[str, int] = Field(default_factory=dict)


class InventoryData(BaseModel):
    """Inventory state data for database storage."""
    items: list[InventoryItem] = Field(default_factory=list)
    gold: int = 0
    max_slots: int = 20


class NarrativeEvent(BaseModel):
    """Single narrative event."""
    event_type: str
    description: str
    timestamp: str
    location: tuple[int, int, int] = (0, 0, 0)
    actors: list[str] = Field(default_factory=list)  # NPCs/enemies involved
    items: list[str] = Field(default_factory=list)  # Items involved
    importance: int = 1


class NarrativeData(BaseModel):
    """Narrative memory data for database storage."""
    events: list[NarrativeEvent] = Field(default_factory=list)
    story_summary: str = ""
    current_tone: str = "mysterious"
    active_threads: list[str] = Field(default_factory=list)
    discovered_lore: list[str] = Field(default_factory=list)
    max_events: int = 100


class CombatData(BaseModel):
    """Current combat state."""
    in_combat: bool = False
    enemy_index: int = -1
    enemy_id: str = ""
    enemy_name: str = ""
    enemy_hp: int = 0
    enemy_max_hp: int = 0
    enemy_attack: int = 0
    enemy_defense: int = 0
    turn: int = 0


class GameSave(BaseModel):
    """Complete game save data."""
    id: Optional[int] = None
    save_name: str = "default"
    player_id: str = "default"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Game state components
    player: PlayerData = Field(default_factory=PlayerData)
    world: WorldData = Field(default_factory=WorldData)
    inventory: InventoryData = Field(default_factory=InventoryData)
    narrative: NarrativeData = Field(default_factory=NarrativeData)
    combat: Optional[CombatData] = None

    # Metadata
    version: str = "1.0.0"
    playtime_seconds: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
