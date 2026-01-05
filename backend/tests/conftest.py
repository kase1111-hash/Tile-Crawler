"""
Pytest configuration and shared fixtures for Tile-Crawler tests.
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient


@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for test files."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath)


@pytest.fixture(scope="function")
def clean_state(temp_dir):
    """Reset all game state modules to use temp directory."""
    import world_state
    import narrative_memory
    import inventory_state
    import player_state

    # Reset global instances
    world_state._world_state = None
    narrative_memory._narrative_memory = None
    inventory_state._inventory_state = None
    player_state._player_state = None

    # Create new instances with temp paths
    ws = world_state.WorldState(save_path=os.path.join(temp_dir, "world.json"))
    nm = narrative_memory.NarrativeMemory(save_path=os.path.join(temp_dir, "narrative.json"))
    inv = inventory_state.InventoryState(save_path=os.path.join(temp_dir, "inventory.json"))
    ps = player_state.PlayerState(save_path=os.path.join(temp_dir, "player.json"))

    # Set as global instances
    world_state._world_state = ws
    narrative_memory._narrative_memory = nm
    inventory_state._inventory_state = inv
    player_state._player_state = ps

    yield {
        "world": ws,
        "narrative": nm,
        "inventory": inv,
        "player": ps,
        "temp_dir": temp_dir
    }

    # Cleanup
    world_state._world_state = None
    narrative_memory._narrative_memory = None
    inventory_state._inventory_state = None
    player_state._player_state = None


@pytest.fixture(scope="function")
def test_client(clean_state):
    """Create a test client for the FastAPI app."""
    from main import app

    # Reset game engine to use clean state
    import game_engine
    game_engine._game_engine = None

    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_room_data():
    """Sample room data for testing."""
    return {
        "x": 0,
        "y": 0,
        "z": 0,
        "map": [
            "▓▓▓▓▓▓▓▓▓▓▓",
            "▓░░░░░░░░░▓",
            "▓░░░░░░░░░▓",
            "▓░░░░@░░░░▓",
            "▓░░░░░░░░░▓",
            "▓░░░░░░░░░▓",
            "▓▓▓▓▓ ▓▓▓▓▓"
        ],
        "description": "A test room",
        "biome": "dungeon",
        "exits": {"south": True},
        "enemies": [],
        "items": [{"id": "healing_potion", "name": "Healing Potion"}],
        "npcs": [],
        "features": ["torch_sconce"]
    }


@pytest.fixture
def sample_enemy():
    """Sample enemy data for testing."""
    return {
        "id": "goblin",
        "name": "Goblin",
        "hp": 15,
        "attack": 5,
        "defense": 2
    }


@pytest.fixture
def sample_item():
    """Sample item data for testing."""
    return {
        "id": "healing_potion",
        "name": "Healing Potion",
        "description": "Restores 30 HP",
        "category": "consumable",
        "quantity": 1,
        "stackable": True,
        "max_stack": 10
    }
