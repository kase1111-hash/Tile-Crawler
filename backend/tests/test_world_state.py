"""
Tests for world_state.py - Room and map persistence.
"""

import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from world_state import WorldState, RoomData


class TestRoomData:
    """Tests for RoomData model."""

    def test_create_room_data_minimal(self):
        """Test creating room data with minimal fields."""
        room = RoomData(x=0, y=0)
        assert room.x == 0
        assert room.y == 0
        assert room.z == 0
        assert room.map == []
        assert room.description == ""
        assert room.biome == "dungeon"

    def test_create_room_data_full(self, sample_room_data):
        """Test creating room data with all fields."""
        room = RoomData(**sample_room_data)
        assert room.x == 0
        assert room.y == 0
        assert room.description == "A test room"
        assert len(room.map) == 7
        assert room.exits["south"] == True
        assert len(room.items) == 1


class TestWorldState:
    """Tests for WorldState manager."""

    def test_init_default(self, temp_dir):
        """Test initializing world state with defaults."""
        ws = WorldState(save_path=os.path.join(temp_dir, "world.json"))
        assert ws.rooms == {}
        assert ws.current_position == (0, 0, 0)
        assert ws.explored_count == 0

    def test_coord_key(self, temp_dir):
        """Test coordinate key generation."""
        ws = WorldState(save_path=os.path.join(temp_dir, "world.json"))
        assert ws._coord_key(1, 2, 3) == "1,2,3"
        assert ws._coord_key(0, 0, 0) == "0,0,0"
        assert ws._coord_key(-1, -2, 0) == "-1,-2,0"

    def test_set_and_get_room(self, temp_dir, sample_room_data):
        """Test setting and getting room data."""
        ws = WorldState(save_path=os.path.join(temp_dir, "world.json"))
        room = RoomData(**sample_room_data)

        ws.set_room(room)

        retrieved = ws.get_room(0, 0, 0)
        assert retrieved is not None
        assert retrieved.description == "A test room"
        assert ws.explored_count == 1

    def test_room_exists(self, temp_dir, sample_room_data):
        """Test checking if room exists."""
        ws = WorldState(save_path=os.path.join(temp_dir, "world.json"))

        assert ws.room_exists(0, 0, 0) == False

        room = RoomData(**sample_room_data)
        ws.set_room(room)

        assert ws.room_exists(0, 0, 0) == True
        assert ws.room_exists(1, 0, 0) == False

    def test_update_position(self, temp_dir, sample_room_data):
        """Test updating player position."""
        ws = WorldState(save_path=os.path.join(temp_dir, "world.json"))
        room = RoomData(**sample_room_data)
        ws.set_room(room)

        ws.update_position(0, 0, 0)

        assert ws.current_position == (0, 0, 0)
        room = ws.get_room(0, 0, 0)
        assert room.visited == True

    def test_save_and_load(self, temp_dir, sample_room_data):
        """Test saving and loading world state."""
        save_path = os.path.join(temp_dir, "world.json")
        ws = WorldState(save_path=save_path)

        room = RoomData(**sample_room_data)
        ws.set_room(room)
        ws.update_position(0, 0, 0)
        ws.save()

        # Create new instance to load
        ws2 = WorldState(save_path=save_path)
        assert ws2.explored_count == 1
        assert ws2.current_position == (0, 0, 0)

        loaded_room = ws2.get_room(0, 0, 0)
        assert loaded_room is not None
        assert loaded_room.description == "A test room"

    def test_remove_item_from_room(self, temp_dir, sample_room_data):
        """Test removing items from a room."""
        ws = WorldState(save_path=os.path.join(temp_dir, "world.json"))
        room = RoomData(**sample_room_data)
        ws.set_room(room)

        result = ws.remove_item_from_room(0, 0, 0, "healing_potion")
        assert result == True

        room = ws.get_room(0, 0, 0)
        assert len(room.items) == 0

    def test_mark_cleared(self, temp_dir, sample_room_data):
        """Test marking room as cleared."""
        ws = WorldState(save_path=os.path.join(temp_dir, "world.json"))
        sample_room_data["enemies"] = [{"id": "goblin", "name": "Goblin", "hp": 10}]
        room = RoomData(**sample_room_data)
        ws.set_room(room)

        ws.mark_cleared(0, 0, 0)

        room = ws.get_room(0, 0, 0)
        assert room.cleared == True
        assert room.enemies == []

    def test_reset(self, temp_dir, sample_room_data):
        """Test resetting world state."""
        save_path = os.path.join(temp_dir, "world.json")
        ws = WorldState(save_path=save_path)

        room = RoomData(**sample_room_data)
        ws.set_room(room)
        ws.save()

        ws.reset()

        assert ws.rooms == {}
        assert ws.explored_count == 0
        assert not os.path.exists(save_path)
