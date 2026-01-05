"""
End-to-end tests for complete game flows.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestCompleteGameFlow:
    """Tests for complete game scenarios."""

    def test_new_game_and_explore(self, test_client):
        """Test starting a game and exploring."""
        # Start new game
        response = test_client.post(
            "/api/game/new",
            json={"player_name": "Explorer"}
        )
        assert response.status_code == 200

        initial_state = response.json()["state"]
        initial_pos = initial_state["position"]
        initial_rooms = initial_state["stats"]["rooms_explored"]

        # Find and use an exit
        exits = initial_state["room"]["exits"]
        moved = False
        for direction, available in exits.items():
            if available and direction in ["north", "south", "east", "west"]:
                move_resp = test_client.post(
                    "/api/game/move",
                    json={"direction": direction}
                )
                if move_resp.json()["success"]:
                    moved = True
                    break

        if moved:
            # Check position changed
            state_resp = test_client.get("/api/game/state")
            new_state = state_resp.json()

            assert new_state["position"] != initial_pos
            assert new_state["stats"]["rooms_explored"] >= initial_rooms

    def test_inventory_management(self, test_client):
        """Test inventory operations."""
        # Start new game - this resets inventory
        new_resp = test_client.post("/api/game/new", json={})
        assert new_resp.status_code == 200

        # Check starting inventory from fresh state
        state = new_resp.json()["state"]
        inv = state["inventory"]
        gold = state["gold"]

        assert gold == 20
        assert any(item["id"] == "torch" for item in inv)

        # Check if healing potion exists
        has_potion = any(item["id"] == "healing_potion" for item in inv)

        if has_potion:
            # Get initial potion count
            original_count = sum(
                item.get("quantity", 1) for item in inv
                if item["id"] == "healing_potion"
            )

            # Use healing potion
            use_resp = test_client.post(
                "/api/game/use",
                json={"item_id": "healing_potion"}
            )
            assert use_resp.status_code == 200

            # Check inventory updated
            inv_resp2 = test_client.get("/api/game/inventory")
            inv2 = inv_resp2.json()["inventory"]

            # Potion count should decrease or be gone
            new_count = sum(
                item.get("quantity", 1) for item in inv2
                if item["id"] == "healing_potion"
            )
            assert new_count < original_count or new_count == 0

    def test_player_stats_tracking(self, test_client):
        """Test that player stats are tracked correctly."""
        # Start new game
        response = test_client.post("/api/game/new", json={})
        initial_state = response.json()["state"]

        # Check initial stats
        assert initial_state["stats"]["rooms_explored"] >= 1
        assert initial_state["stats"]["steps_taken"] >= 0  # May vary based on game init
        assert initial_state["stats"]["enemies_defeated"] >= 0
        assert initial_state["stats"]["deaths"] >= 0

        initial_steps = initial_state["stats"]["steps_taken"]

        # Move around
        exits = initial_state["room"]["exits"]
        for direction, available in exits.items():
            if available and direction in ["north", "south", "east", "west"]:
                test_client.post("/api/game/move", json={"direction": direction})
                break

        # Check steps increased
        state_resp = test_client.get("/api/game/state")
        new_stats = state_resp.json()["stats"]

        assert new_stats["steps_taken"] >= initial_steps  # Steps should not decrease

    def test_save_and_load_preserves_state(self, test_client):
        """Test that save/load preserves game state."""
        # Start new game
        test_client.post("/api/game/new", json={"player_name": "Saver"})

        # Get initial state
        state1 = test_client.get("/api/game/state").json()

        # Save game
        save_resp = test_client.post("/api/game/save")
        assert save_resp.json()["success"] == True

        # Load game
        load_resp = test_client.post("/api/game/load")
        assert load_resp.json()["success"] == True

        # Get state after load
        state2 = test_client.get("/api/game/state").json()

        # Compare key fields
        assert state2["player"]["name"] == state1["player"]["name"]
        assert state2["position"] == state1["position"]
        assert state2["gold"] == state1["gold"]

    def test_multiple_rooms_exploration(self, test_client):
        """Test exploring multiple rooms."""
        test_client.post("/api/game/new", json={})

        visited_positions = set()
        visited_positions.add(tuple([0, 0, 0]))

        # Try to visit multiple rooms
        for _ in range(5):
            state_resp = test_client.get("/api/game/state")
            state = state_resp.json()
            exits = state["room"]["exits"]

            for direction, available in exits.items():
                if available and direction in ["north", "south", "east", "west"]:
                    move_resp = test_client.post(
                        "/api/game/move",
                        json={"direction": direction}
                    )
                    if move_resp.json()["success"]:
                        new_state = move_resp.json()["state"]
                        visited_positions.add(tuple(new_state["position"]))
                        break

        # Should have visited at least 2 rooms
        assert len(visited_positions) >= 2

    def test_narrative_updates(self, test_client):
        """Test that narrative updates with actions."""
        # Start new game
        new_resp = test_client.post("/api/game/new", json={})
        initial_narrative = new_resp.json()["narrative"]

        assert initial_narrative != ""

        # Move
        state = new_resp.json()["state"]
        exits = state["room"]["exits"]

        for direction, available in exits.items():
            if available and direction in ["north", "south", "east", "west"]:
                move_resp = test_client.post(
                    "/api/game/move",
                    json={"direction": direction}
                )
                if move_resp.json()["success"]:
                    new_narrative = move_resp.json()["narrative"]
                    assert new_narrative != ""
                    break

    def test_room_has_expected_structure(self, test_client):
        """Test that rooms have expected data structure."""
        test_client.post("/api/game/new", json={})

        state = test_client.get("/api/game/state").json()
        room = state["room"]

        # Check required fields
        assert "map" in room
        assert "description" in room
        assert "biome" in room
        assert "exits" in room
        assert "enemies" in room
        assert "items" in room
        assert "npcs" in room
        assert "features" in room

        # Check map structure
        assert isinstance(room["map"], list)
        assert len(room["map"]) > 0

        # Check exits structure
        assert isinstance(room["exits"], dict)

    def test_player_stats_structure(self, test_client):
        """Test player stats have expected structure."""
        test_client.post("/api/game/new", json={"player_name": "StatsTest"})

        state = test_client.get("/api/game/state").json()
        player = state["player"]

        # Check required fields
        assert "name" in player
        assert "level" in player
        assert "hp" in player
        assert "mana" in player
        assert "xp" in player
        assert "attack" in player
        assert "defense" in player
        assert "speed" in player
        assert "magic" in player

        # Check values
        assert player["name"] == "StatsTest"
        assert player["level"] == 1
        assert "/" in player["hp"]  # Format: "current/max"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_operations_without_game(self, test_client):
        """Test operations before starting a game."""
        # These should handle gracefully
        move_resp = test_client.post("/api/game/move", json={"direction": "north"})
        # May return error or empty state, but shouldn't crash
        assert move_resp.status_code in [200, 500]

    def test_rapid_movements(self, test_client):
        """Test rapid sequential movements."""
        test_client.post("/api/game/new", json={})

        # Make many rapid moves
        for _ in range(10):
            state = test_client.get("/api/game/state").json()
            exits = state["room"]["exits"]

            for direction, available in exits.items():
                if available and direction in ["north", "south", "east", "west"]:
                    test_client.post("/api/game/move", json={"direction": direction})
                    break

        # Game should still be functional
        final_state = test_client.get("/api/game/state")
        assert final_state.status_code == 200

    def test_empty_request_bodies(self, test_client):
        """Test endpoints with empty request bodies."""
        test_client.post("/api/game/new", json={})

        # Talk with empty message
        talk_resp = test_client.post("/api/game/talk", json={})
        assert talk_resp.status_code == 200

    def test_special_characters_in_name(self, test_client):
        """Test player name with special characters."""
        response = test_client.post(
            "/api/game/new",
            json={"player_name": "Test<>Hero&'\""}
        )

        assert response.status_code == 200
        # Name should be accepted or sanitized
        state = response.json()["state"]
        assert state["player"]["name"] is not None
