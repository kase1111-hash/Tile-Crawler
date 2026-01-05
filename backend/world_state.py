"""
World State Management for Tile-Crawler

Handles persistent storage of explored rooms, map data, and world coordinates.
Each room is stored by its coordinate key (x,y) to prevent re-generation
of previously visited areas.
"""

import json
import os
from typing import Optional
from pydantic import BaseModel, Field


class RoomData(BaseModel):
    """Data structure for a single room."""
    x: int
    y: int
    z: int = 0  # Floor/depth level
    map: list[str] = Field(default_factory=list)
    description: str = ""
    biome: str = "dungeon"
    exits: dict[str, bool] = Field(default_factory=dict)
    enemies: list[dict] = Field(default_factory=list)
    items: list[dict] = Field(default_factory=list)
    npcs: list[str] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    visited: bool = False
    cleared: bool = False


class WorldState:
    """
    Manages the persistent world state including all explored rooms.

    Rooms are indexed by coordinate strings "x,y,z" for efficient lookup.
    """

    def __init__(self, save_path: str = "world_state.json"):
        self.save_path = save_path
        self.rooms: dict[str, RoomData] = {}
        self.current_position: tuple[int, int, int] = (0, 0, 0)
        self.explored_count: int = 0
        self.world_seed: Optional[str] = None
        self._load()

    def _coord_key(self, x: int, y: int, z: int = 0) -> str:
        """Generate a coordinate key string."""
        return f"{x},{y},{z}"

    def _parse_coord_key(self, key: str) -> tuple[int, int, int]:
        """Parse a coordinate key string back to tuple."""
        parts = key.split(",")
        return (int(parts[0]), int(parts[1]), int(parts[2]) if len(parts) > 2 else 0)

    def _load(self) -> None:
        """Load world state from disk."""
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r') as f:
                    data = json.load(f)
                    self.rooms = {
                        k: RoomData(**v) for k, v in data.get("rooms", {}).items()
                    }
                    self.current_position = tuple(data.get("current_position", [0, 0, 0]))
                    self.explored_count = data.get("explored_count", 0)
                    self.world_seed = data.get("world_seed")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load world state: {e}")
                self._init_default()
        else:
            self._init_default()

    def _init_default(self) -> None:
        """Initialize default world state."""
        self.rooms = {}
        self.current_position = (0, 0, 0)
        self.explored_count = 0
        self.world_seed = None

    def save(self) -> None:
        """Save world state to disk."""
        data = {
            "rooms": {k: v.model_dump() for k, v in self.rooms.items()},
            "current_position": list(self.current_position),
            "explored_count": self.explored_count,
            "world_seed": self.world_seed
        }
        with open(self.save_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_room(self, x: int, y: int, z: int = 0) -> Optional[RoomData]:
        """Get room data at specified coordinates."""
        key = self._coord_key(x, y, z)
        return self.rooms.get(key)

    def set_room(self, room: RoomData) -> None:
        """Store room data at its coordinates."""
        key = self._coord_key(room.x, room.y, room.z)
        is_new = key not in self.rooms
        self.rooms[key] = room
        if is_new:
            self.explored_count += 1

    def room_exists(self, x: int, y: int, z: int = 0) -> bool:
        """Check if a room has been generated at coordinates."""
        return self._coord_key(x, y, z) in self.rooms

    def mark_visited(self, x: int, y: int, z: int = 0) -> None:
        """Mark a room as visited by the player."""
        room = self.get_room(x, y, z)
        if room:
            room.visited = True

    def mark_cleared(self, x: int, y: int, z: int = 0) -> None:
        """Mark a room as cleared of enemies."""
        room = self.get_room(x, y, z)
        if room:
            room.cleared = True
            room.enemies = []

    def update_position(self, x: int, y: int, z: int = 0) -> None:
        """Update current player position."""
        self.current_position = (x, y, z)
        self.mark_visited(x, y, z)

    def get_current_room(self) -> Optional[RoomData]:
        """Get the room at current position."""
        x, y, z = self.current_position
        return self.get_room(x, y, z)

    def get_adjacent_rooms(self) -> dict[str, Optional[RoomData]]:
        """Get all adjacent room data (if explored)."""
        x, y, z = self.current_position
        return {
            "north": self.get_room(x, y - 1, z),
            "south": self.get_room(x, y + 1, z),
            "east": self.get_room(x + 1, y, z),
            "west": self.get_room(x - 1, y, z),
            "up": self.get_room(x, y, z - 1),
            "down": self.get_room(x, y, z + 1),
        }

    def remove_item_from_room(self, x: int, y: int, z: int, item_id: str) -> bool:
        """Remove an item from a room (when picked up)."""
        room = self.get_room(x, y, z)
        if room:
            for i, item in enumerate(room.items):
                if item.get("id") == item_id:
                    room.items.pop(i)
                    return True
        return False

    def remove_enemy_from_room(self, x: int, y: int, z: int, enemy_index: int) -> bool:
        """Remove an enemy from a room (when defeated)."""
        room = self.get_room(x, y, z)
        if room and 0 <= enemy_index < len(room.enemies):
            room.enemies.pop(enemy_index)
            if not room.enemies:
                room.cleared = True
            return True
        return False

    def get_explored_rooms_summary(self) -> list[dict]:
        """Get a summary of all explored rooms for the map."""
        summary = []
        for key, room in self.rooms.items():
            summary.append({
                "coords": self._parse_coord_key(key),
                "biome": room.biome,
                "visited": room.visited,
                "cleared": room.cleared,
                "has_enemies": len(room.enemies) > 0,
                "has_items": len(room.items) > 0,
                "has_npcs": len(room.npcs) > 0
            })
        return summary

    def reset(self) -> None:
        """Reset the world state for a new game."""
        self._init_default()
        if os.path.exists(self.save_path):
            os.remove(self.save_path)


# Global instance
_world_state: Optional[WorldState] = None


def get_world_state() -> WorldState:
    """Get the global world state instance."""
    global _world_state
    if _world_state is None:
        _world_state = WorldState()
    return _world_state


def reset_world_state() -> WorldState:
    """Reset and return a fresh world state."""
    global _world_state
    if _world_state:
        _world_state.reset()
    _world_state = WorldState()
    return _world_state
