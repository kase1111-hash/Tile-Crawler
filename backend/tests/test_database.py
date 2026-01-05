"""Tests for database layer."""

import os
import tempfile
import pytest
from datetime import datetime

# Add parent directory to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import (
    GameSave, PlayerData, WorldData, InventoryData, NarrativeData,
    CombatData, RoomRecord, InventoryItem, NarrativeEvent
)
from database.repository import (
    SQLiteRepository, GameRepository, get_repository, reset_repository
)


class TestDatabaseModels:
    """Tests for database models."""

    def test_player_data_default(self):
        """Test PlayerData with defaults."""
        player = PlayerData()
        assert player.name == "Adventurer"
        assert player.level == 1
        assert player.stats["max_hp"] == 100
        assert player.is_alive is True

    def test_player_data_custom(self):
        """Test PlayerData with custom values."""
        player = PlayerData(
            name="Hero",
            level=5,
            experience=450,
            deaths=2
        )
        assert player.name == "Hero"
        assert player.level == 5
        assert player.experience == 450
        assert player.deaths == 2

    def test_world_data_default(self):
        """Test WorldData with defaults."""
        world = WorldData()
        assert world.current_x == 0
        assert world.current_y == 0
        assert world.rooms == []

    def test_room_record(self):
        """Test RoomRecord model."""
        room = RoomRecord(
            x=1, y=2, z=0,
            biome="dungeon",
            description="A dark room",
            tiles=["###", "#.#", "###"],
            exits={"north": True, "south": False},
            enemies=[],
            items=[],
            npcs=[],
            features=["torch"]
        )
        assert room.x == 1
        assert room.biome == "dungeon"
        assert room.exits["north"] is True

    def test_inventory_data_default(self):
        """Test InventoryData with defaults."""
        inv = InventoryData()
        assert inv.items == []
        assert inv.gold == 0
        assert inv.max_slots == 20

    def test_inventory_item(self):
        """Test InventoryItem model."""
        item = InventoryItem(
            id="sword",
            name="Iron Sword",
            description="A basic sword",
            category="weapon",
            quantity=1,
            equipped=True
        )
        assert item.id == "sword"
        assert item.equipped is True

    def test_narrative_data_default(self):
        """Test NarrativeData with defaults."""
        narrative = NarrativeData()
        assert narrative.events == []
        assert narrative.current_tone == "mysterious"

    def test_combat_data(self):
        """Test CombatData model."""
        combat = CombatData(
            in_combat=True,
            enemy_name="Goblin",
            enemy_hp=30,
            enemy_max_hp=30
        )
        assert combat.in_combat is True
        assert combat.enemy_name == "Goblin"

    def test_game_save(self):
        """Test GameSave model."""
        save = GameSave(
            save_name="test_save",
            player_id="player123"
        )
        assert save.save_name == "test_save"
        assert save.player_id == "player123"
        assert isinstance(save.player, PlayerData)
        assert isinstance(save.world, WorldData)


class TestSQLiteRepository:
    """Tests for SQLite repository."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def repo(self, temp_db):
        """Create a repository with temp database."""
        return SQLiteRepository(db_path=temp_db)

    def test_initialize(self, repo):
        """Test database initialization."""
        repo.initialize()
        # Should not raise
        assert repo._initialized is True

    def test_save_and_load_game(self, repo):
        """Test saving and loading a game."""
        # Create a save
        save = GameSave(
            player_id="test_player",
            save_name="test_save",
            player=PlayerData(name="TestHero", level=5),
            inventory=InventoryData(gold=100),
        )

        # Save it
        save_id = repo.save_game(save)
        assert save_id > 0

        # Load it back
        loaded = repo.load_game(save_id)
        assert loaded is not None
        assert loaded.player.name == "TestHero"
        assert loaded.player.level == 5
        assert loaded.inventory.gold == 100

    def test_load_most_recent(self, repo):
        """Test loading most recent save for player."""
        # Create multiple saves
        for i in range(3):
            save = GameSave(
                player_id="player1",
                save_name=f"save_{i}",
                player=PlayerData(level=i + 1),
            )
            repo.save_game(save)

        # Load most recent
        loaded = repo.load_game(player_id="player1")
        assert loaded is not None
        assert loaded.player.level == 3  # Last save

    def test_load_nonexistent(self, repo):
        """Test loading nonexistent save."""
        repo.initialize()
        loaded = repo.load_game(save_id=9999)
        assert loaded is None

    def test_update_existing_save(self, repo):
        """Test updating an existing save."""
        # Create initial save
        save = GameSave(
            player_id="player1",
            save_name="save1",
            player=PlayerData(level=1),
        )
        save_id = repo.save_game(save)

        # Update it
        save.id = save_id
        save.player.level = 10
        repo.save_game(save)

        # Verify update
        loaded = repo.load_game(save_id)
        assert loaded.player.level == 10

    def test_delete_game(self, repo):
        """Test deleting a saved game."""
        save = GameSave(player_id="player1", save_name="to_delete")
        save_id = repo.save_game(save)

        # Delete it
        result = repo.delete_game(save_id)
        assert result is True

        # Verify deletion
        loaded = repo.load_game(save_id)
        assert loaded is None

    def test_delete_nonexistent(self, repo):
        """Test deleting nonexistent save."""
        repo.initialize()
        result = repo.delete_game(9999)
        assert result is False

    def test_list_saves(self, repo):
        """Test listing saves for a player."""
        # Create saves for different players
        repo.save_game(GameSave(player_id="player1", save_name="save1"))
        repo.save_game(GameSave(player_id="player1", save_name="save2"))
        repo.save_game(GameSave(player_id="player2", save_name="save3"))

        # List player1's saves
        saves = repo.list_saves("player1")
        assert len(saves) == 2
        assert all(s["save_name"] in ["save1", "save2"] for s in saves)

    def test_get_save_count(self, repo):
        """Test counting saves for a player."""
        repo.save_game(GameSave(player_id="player1", save_name="save1"))
        repo.save_game(GameSave(player_id="player1", save_name="save2"))
        repo.save_game(GameSave(player_id="player2", save_name="save3"))

        count = repo.get_save_count("player1")
        assert count == 2

    def test_save_with_combat(self, repo):
        """Test saving game with combat state."""
        save = GameSave(
            player_id="player1",
            save_name="combat_save",
            combat=CombatData(
                in_combat=True,
                enemy_name="Dragon",
                enemy_hp=500,
                enemy_max_hp=500
            )
        )
        save_id = repo.save_game(save)

        loaded = repo.load_game(save_id)
        assert loaded.combat is not None
        assert loaded.combat.in_combat is True
        assert loaded.combat.enemy_name == "Dragon"

    def test_save_with_rooms(self, repo):
        """Test saving game with world rooms."""
        save = GameSave(
            player_id="player1",
            save_name="world_save",
            world=WorldData(
                current_x=5,
                current_y=3,
                rooms=[
                    RoomRecord(
                        x=0, y=0, z=0,
                        biome="forest",
                        description="Starting area",
                        tiles=["..."],
                        exits={"north": True},
                        enemies=[],
                        items=[{"id": "coin", "name": "Gold Coin"}],
                        npcs=["merchant"],
                        features=[]
                    )
                ]
            )
        )
        save_id = repo.save_game(save)

        loaded = repo.load_game(save_id)
        assert loaded.world.current_x == 5
        assert len(loaded.world.rooms) == 1
        assert loaded.world.rooms[0].biome == "forest"


class TestGameRepository:
    """Tests for unified GameRepository."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_create_sqlite_repo(self, temp_db):
        """Test creating SQLite repository."""
        repo = GameRepository(backend="sqlite", db_path=temp_db)
        assert repo.backend == "sqlite"

    def test_create_with_invalid_backend(self):
        """Test creating with invalid backend."""
        with pytest.raises(ValueError):
            GameRepository(backend="invalid")

    def test_quick_save(self, temp_db):
        """Test quick save creation."""
        repo = GameRepository(backend="sqlite", db_path=temp_db)
        save = repo.quick_save("player1")
        assert save.player_id == "player1"
        assert save.save_name == "quicksave"


class TestSingleton:
    """Tests for singleton management."""

    def test_get_repository_returns_same_instance(self):
        """Test that get_repository returns singleton."""
        reset_repository()
        repo1 = get_repository()
        repo2 = get_repository()
        assert repo1 is repo2

    def test_reset_repository(self):
        """Test that reset creates new instance."""
        repo1 = get_repository()
        reset_repository()
        repo2 = get_repository()
        assert repo1 is not repo2

    def teardown_method(self):
        """Clean up after each test."""
        reset_repository()
        # Clean up test database
        if os.path.exists("game_data.db"):
            os.unlink("game_data.db")
