"""
Tests for main.py - FastAPI endpoints.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns health status."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "version" in data

    def test_health_endpoint(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "llm_available" in data


class TestGameManagement:
    """Tests for game management endpoints."""

    def test_new_game(self, test_client):
        """Test starting a new game."""
        response = test_client.post(
            "/api/game/new",
            json={"player_name": "TestHero"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "state" in data
        assert data["state"]["player"]["name"] == "TestHero"

    def test_new_game_default_name(self, test_client):
        """Test new game with default name."""
        response = test_client.post(
            "/api/game/new",
            json={}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"]["player"]["name"] == "Adventurer"

    def test_get_state_after_new_game(self, test_client):
        """Test getting state after starting game."""
        # Start new game
        test_client.post("/api/game/new", json={})

        # Get state
        response = test_client.get("/api/game/state")

        assert response.status_code == 200
        data = response.json()
        assert "player" in data
        assert "room" in data
        assert "inventory" in data
        assert "position" in data

    def test_save_game(self, test_client):
        """Test saving game."""
        # Start new game
        test_client.post("/api/game/new", json={})

        # Save
        response = test_client.post("/api/game/save")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


class TestMovement:
    """Tests for movement endpoints."""

    def test_move_valid_direction(self, test_client):
        """Test moving in a valid direction."""
        # Start new game
        new_game_resp = test_client.post("/api/game/new", json={})
        state = new_game_resp.json()["state"]

        # Find an available exit
        exits = state["room"]["exits"]
        valid_direction = None
        for direction, available in exits.items():
            if available:
                valid_direction = direction
                break

        if valid_direction:
            response = test_client.post(
                "/api/game/move",
                json={"direction": valid_direction}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True

    def test_move_invalid_direction(self, test_client):
        """Test moving in an invalid direction."""
        test_client.post("/api/game/new", json={})

        response = test_client.post(
            "/api/game/move",
            json={"direction": "invalid"}
        )

        assert response.status_code == 400

    def test_move_blocked_direction(self, test_client):
        """Test moving where no exit exists."""
        new_game_resp = test_client.post("/api/game/new", json={})
        state = new_game_resp.json()["state"]

        # Find a blocked exit
        exits = state["room"]["exits"]
        blocked_direction = None
        for direction in ["north", "south", "east", "west"]:
            if not exits.get(direction, False):
                blocked_direction = direction
                break

        if blocked_direction:
            response = test_client.post(
                "/api/game/move",
                json={"direction": blocked_direction}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] == False

    def test_move_shorthand_endpoints(self, test_client):
        """Test shorthand movement endpoints."""
        test_client.post("/api/game/new", json={})

        # These may fail if exit doesn't exist, but should return 200
        for direction in ["north", "south", "east", "west"]:
            response = test_client.post(f"/api/game/move/{direction}")
            assert response.status_code == 200


class TestInventory:
    """Tests for inventory endpoints."""

    def test_get_inventory(self, test_client):
        """Test getting inventory."""
        test_client.post("/api/game/new", json={})

        response = test_client.get("/api/game/inventory")

        assert response.status_code == 200
        data = response.json()
        assert "inventory" in data
        assert "gold" in data
        assert isinstance(data["inventory"], list)

    def test_use_item(self, test_client):
        """Test using an item."""
        test_client.post("/api/game/new", json={})

        # Try to use healing potion (starting item)
        response = test_client.post(
            "/api/game/use",
            json={"item_id": "healing_potion"}
        )

        assert response.status_code == 200
        data = response.json()
        # May succeed or fail depending on HP, but should return response
        assert "success" in data

    def test_use_nonexistent_item(self, test_client):
        """Test using item not in inventory."""
        test_client.post("/api/game/new", json={})

        response = test_client.post(
            "/api/game/use",
            json={"item_id": "nonexistent_item"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False


class TestInteractions:
    """Tests for interaction endpoints."""

    def test_talk_no_npc(self, test_client):
        """Test talking when no NPC present."""
        test_client.post("/api/game/new", json={})

        response = test_client.post(
            "/api/game/talk",
            json={"message": "Hello"}
        )

        assert response.status_code == 200
        data = response.json()
        # Should fail gracefully if no NPC
        assert "success" in data

    def test_rest_unsafe_room(self, test_client):
        """Test resting in unsafe room."""
        test_client.post("/api/game/new", json={})

        response = test_client.post("/api/game/rest")

        assert response.status_code == 200
        data = response.json()
        # Starting room may or may not be safe
        assert "success" in data


class TestCombat:
    """Tests for combat endpoints."""

    def test_attack_no_combat(self, test_client):
        """Test attacking when not in combat."""
        test_client.post("/api/game/new", json={})

        response = test_client.post("/api/game/combat/attack")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False

    def test_flee_no_combat(self, test_client):
        """Test fleeing when not in combat."""
        test_client.post("/api/game/new", json={})

        response = test_client.post("/api/game/combat/flee")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
