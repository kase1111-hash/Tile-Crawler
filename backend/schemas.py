"""
Pydantic request/response models for the Tile-Crawler API.
"""

import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NewGameRequest(BaseModel):
    """Request to start a new game session."""
    model_config = ConfigDict(json_schema_extra={"example": {"player_name": "Brave Hero"}})

    player_name: str = Field(
        default="Adventurer",
        description="The name of the player character (alphanumeric, spaces, hyphens, underscores only)",
        min_length=1,
        max_length=50,
        json_schema_extra={"example": "Brave Hero"}
    )

    @field_validator("player_name")
    @classmethod
    def sanitize_player_name(cls, v: str) -> str:
        """Sanitize player name to prevent injection and path traversal."""
        v = v.strip()

        if not re.match(r"^[a-zA-Z0-9\s\-_']+$", v):
            raise ValueError(
                "Player name can only contain letters, numbers, spaces, hyphens, underscores, and apostrophes"
            )

        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Invalid characters in player name")

        return v


class MoveRequest(BaseModel):
    """Request to move the player in a direction."""
    model_config = ConfigDict(json_schema_extra={"example": {"direction": "north"}})

    direction: str = Field(
        description="Direction to move: north, south, east, west, up, or down",
        json_schema_extra={"example": "north"}
    )


class TakeItemRequest(BaseModel):
    """Request to pick up an item from the current room."""
    model_config = ConfigDict(json_schema_extra={"example": {"item_id": "healing_potion"}})

    item_id: str = Field(
        description="The unique identifier of the item to pick up",
        json_schema_extra={"example": "rusty_sword"}
    )


class UseItemRequest(BaseModel):
    """Request to use an item from inventory."""
    model_config = ConfigDict(json_schema_extra={"example": {"item_id": "healing_potion"}})

    item_id: str = Field(
        description="The unique identifier of the item to use",
        json_schema_extra={"example": "healing_potion"}
    )


class TalkRequest(BaseModel):
    """Request to talk to an NPC."""
    model_config = ConfigDict(json_schema_extra={"example": {"message": "Hello, what news do you have?"}})

    message: str = Field(
        default="",
        description="Optional message to say to the NPC",
        json_schema_extra={"example": "Hello, what news do you have?"}
    )


class ChangePasswordRequest(BaseModel):
    """Request to change user password."""
    model_config = ConfigDict(json_schema_extra={"example": {"old_password": "current123", "new_password": "newsecure456"}})

    old_password: str = Field(
        description="Current password for verification",
        json_schema_extra={"example": "current123"}
    )
    new_password: str = Field(
        min_length=6,
        description="New password (minimum 6 characters)",
        json_schema_extra={"example": "newsecure456"}
    )


class ActionResponse(BaseModel):
    """Standard response for game actions."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "You move north into a dark corridor.",
            "narrative": "The ancient stones crumble beneath your feet as you venture deeper into the dungeon."
        }
    })

    success: bool = Field(description="Whether the action was successful")
    message: str = Field(description="Human-readable result message")
    narrative: str = Field(default="", description="LLM-generated narrative text")
    map: Optional[list[str]] = Field(default=None, description="ASCII map of current room (11x15 grid)")
    state: Optional[dict] = Field(default=None, description="Full game state snapshot")
    combat: Optional[dict] = Field(default=None, description="Combat state if in battle")
    dialogue: Optional[dict] = Field(default=None, description="NPC dialogue data if talking")


class GameStateResponse(BaseModel):
    """Complete game state snapshot."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "player": {"name": "Brave Hero", "level": 1, "hp": "100/100", "mana": "50/50", "attack": 10, "defense": 5},
            "position": [0, 0, 1],
            "room": {"biome": "dungeon", "description": "A cold stone chamber...", "exits": {"north": True, "south": False, "east": True, "west": False}},
            "inventory": [{"id": "torch", "name": "Torch", "quantity": 1}],
            "gold": 20, "combat": None,
            "narrative": {"story_summary": "A brave adventurer enters the dungeon..."},
            "stats": {"rooms_explored": 1, "enemies_defeated": 0}
        }
    })

    player: dict = Field(description="Player stats including HP, level, attributes")
    position: list[int] = Field(description="Current [x, y, z] coordinates")
    room: dict = Field(description="Current room data including map, enemies, items")
    inventory: list[dict] = Field(description="List of items in player's inventory")
    gold: int = Field(description="Amount of gold the player has")
    combat: Optional[dict] = Field(default=None, description="Combat state if currently in battle")
    narrative: dict = Field(description="Narrative context and recent events")
    stats: dict = Field(description="Game statistics (rooms explored, enemies defeated, etc.)")


class HealthResponse(BaseModel):
    """API health check response."""
    model_config = ConfigDict(json_schema_extra={"example": {"status": "healthy", "llm_available": True, "version": "0.1.0"}})

    status: str = Field(description="Service status: online, healthy, degraded")
    llm_available: bool = Field(description="Whether the LLM engine is available")
    version: str = Field(description="API version string")


class InventoryResponse(BaseModel):
    """Player inventory response."""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "inventory": [{"id": "torch", "name": "Torch", "category": "tool", "quantity": 1}, {"id": "healing_potion", "name": "Healing Potion", "category": "consumable", "quantity": 2}],
            "gold": 20
        }
    })

    inventory: list[dict] = Field(description="List of inventory items")
    gold: int = Field(description="Current gold amount")


class SaveLoadResponse(BaseModel):
    """Response for save/load operations."""
    model_config = ConfigDict(json_schema_extra={"example": {"success": True, "message": "Game saved successfully", "state": None}})

    success: bool = Field(description="Whether the operation succeeded")
    message: str = Field(description="Result message")
    state: Optional[dict] = Field(default=None, description="Game state (for load operations)")
