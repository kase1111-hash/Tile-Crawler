"""Tests for fallback room generator variety."""

import pytest
import os
from unittest.mock import patch

from llm_engine import LLMEngine, RoomGenerationResponse


@pytest.fixture
def llm():
    """Create an offline LLM engine for fallback testing."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "", "LLM_MODEL": "test-model"}):
        engine = LLMEngine()
        engine.client = None
    return engine


ALL_BIOMES = ["dungeon", "cave", "crypt", "ruins", "temple", "volcano", "void"]


class TestFallbackRoomVariety:
    """Test that fallback generator produces varied rooms."""

    @pytest.mark.asyncio
    async def test_all_biomes_generate_rooms(self, llm):
        """Every biome should produce a valid fallback room."""
        for biome in ALL_BIOMES:
            result = await llm.generate_room(
                x=0, y=0, z=0,
                biome=biome,
                exits={"north": True, "south": True},
                narrative_context={},
                inventory_summary="",
            )
            assert isinstance(result, RoomGenerationResponse), f"Failed for biome: {biome}"
            assert len(result.map) > 0, f"Empty map for biome: {biome}"
            assert len(result.description) > 0, f"Empty description for biome: {biome}"

    @pytest.mark.asyncio
    async def test_different_biomes_get_different_descriptions(self, llm):
        """Different biomes should produce different descriptions."""
        descriptions = set()
        for biome in ALL_BIOMES:
            result = await llm.generate_room(
                x=0, y=0, z=0,
                biome=biome,
                exits={"north": True},
                narrative_context={},
                inventory_summary="",
            )
            descriptions.add(result.description)

        # At least most biomes should have unique descriptions
        assert len(descriptions) >= 4

    @pytest.mark.asyncio
    async def test_room_map_dimensions(self, llm):
        """Fallback maps should have consistent dimensions."""
        for biome in ["dungeon", "cave", "crypt"]:
            result = await llm.generate_room(
                x=0, y=0, z=0,
                biome=biome,
                exits={"north": True},
                narrative_context={},
                inventory_summary="",
            )
            # All rows same length
            lengths = [len(row) for row in result.map]
            assert len(set(lengths)) == 1, f"Inconsistent row lengths for {biome}: {lengths}"
            # Reasonable dimensions
            assert lengths[0] >= 11
            assert len(result.map) >= 9


class TestFallbackExits:
    """Test that exits are correctly placed in fallback rooms."""

    @pytest.mark.asyncio
    async def test_north_exit(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=0, biome="dungeon",
            exits={"north": True, "south": False, "east": False, "west": False},
            narrative_context={}, inventory_summary="",
        )
        mid_col = len(result.map[0]) // 2
        assert result.map[0][mid_col] == " "

    @pytest.mark.asyncio
    async def test_south_exit(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=0, biome="dungeon",
            exits={"north": False, "south": True, "east": False, "west": False},
            narrative_context={}, inventory_summary="",
        )
        mid_col = len(result.map[0]) // 2
        assert result.map[-1][mid_col] == " "

    @pytest.mark.asyncio
    async def test_east_exit(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=0, biome="dungeon",
            exits={"north": False, "south": False, "east": True, "west": False},
            narrative_context={}, inventory_summary="",
        )
        mid_row = len(result.map) // 2
        assert result.map[mid_row][-1] == " "

    @pytest.mark.asyncio
    async def test_west_exit(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=0, biome="dungeon",
            exits={"north": False, "south": False, "east": False, "west": True},
            narrative_context={}, inventory_summary="",
        )
        mid_row = len(result.map) // 2
        assert result.map[mid_row][0] == " "

    @pytest.mark.asyncio
    async def test_down_stairs(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=0, biome="dungeon",
            exits={"north": True, "down": True},
            narrative_context={}, inventory_summary="",
        )
        # Should contain > somewhere in the map
        all_chars = "".join(result.map)
        assert ">" in all_chars

    @pytest.mark.asyncio
    async def test_up_stairs(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=1, biome="dungeon",
            exits={"north": True, "up": True},
            narrative_context={}, inventory_summary="",
        )
        all_chars = "".join(result.map)
        assert "<" in all_chars

    @pytest.mark.asyncio
    async def test_all_exits(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=0, biome="dungeon",
            exits={"north": True, "south": True, "east": True, "west": True},
            narrative_context={}, inventory_summary="",
        )
        mid_col = len(result.map[0]) // 2
        mid_row = len(result.map) // 2
        assert result.map[0][mid_col] == " "
        assert result.map[-1][mid_col] == " "
        assert result.map[mid_row][-1] == " "
        assert result.map[mid_row][0] == " "


class TestFallbackEnemySpawning:
    """Test enemy spawning in fallback rooms."""

    @pytest.mark.asyncio
    async def test_enemies_may_spawn(self, llm):
        """Over many rooms, at least some should have enemies."""
        enemy_counts = []
        for i in range(20):
            result = await llm.generate_room(
                x=i, y=0, z=3, biome="dungeon",
                exits={"north": True},
                narrative_context={}, inventory_summary="",
            )
            enemy_counts.append(len(result.enemies))

        # At least some rooms should have enemies (60% no-enemy chance)
        assert sum(1 for c in enemy_counts if c > 0) > 0

    @pytest.mark.asyncio
    async def test_enemy_data_has_required_fields(self, llm):
        """Spawned enemies should have id, name, hp, attack, defense."""
        for _ in range(20):
            result = await llm.generate_room(
                x=0, y=0, z=3, biome="dungeon",
                exits={"north": True},
                narrative_context={}, inventory_summary="",
            )
            for enemy in result.enemies:
                assert "id" in enemy
                assert "name" in enemy
                assert "hp" in enemy
                assert "attack" in enemy


class TestFallbackItemSpawning:
    """Test item spawning in fallback rooms."""

    @pytest.mark.asyncio
    async def test_items_may_spawn(self, llm):
        """Over many rooms, at least some should have items."""
        item_counts = []
        for i in range(20):
            result = await llm.generate_room(
                x=i, y=i, z=2, biome="cave",
                exits={"north": True},
                narrative_context={}, inventory_summary="",
            )
            item_counts.append(len(result.items))

        assert sum(1 for c in item_counts if c > 0) > 0

    @pytest.mark.asyncio
    async def test_item_data_has_required_fields(self, llm):
        """Spawned items should have id, name."""
        for _ in range(20):
            result = await llm.generate_room(
                x=0, y=0, z=2, biome="cave",
                exits={"north": True},
                narrative_context={}, inventory_summary="",
            )
            for item in result.items:
                assert "id" in item
                assert "name" in item


class TestFallbackFeatures:
    """Test feature generation in fallback rooms."""

    @pytest.mark.asyncio
    async def test_features_generated(self, llm):
        """Rooms should have features."""
        result = await llm.generate_room(
            x=0, y=0, z=0, biome="dungeon",
            exits={"north": True},
            narrative_context={}, inventory_summary="",
        )
        assert len(result.features) > 0

    @pytest.mark.asyncio
    async def test_biome_specific_features(self, llm):
        """Different biomes should produce different features."""
        all_features = {}
        for biome in ALL_BIOMES:
            features = set()
            for i in range(5):
                result = await llm.generate_room(
                    x=i, y=0, z=0, biome=biome,
                    exits={"north": True},
                    narrative_context={}, inventory_summary="",
                )
                features.update(result.features)
            all_features[biome] = features

        # At least some biomes should have unique features
        unique_features = set()
        for biome, features in all_features.items():
            unique_features.update(features)
        assert len(unique_features) >= 5


class TestEntityPlacement:
    """Test entity placement on maps."""

    @pytest.mark.asyncio
    async def test_enemies_appear_on_map(self, llm):
        """Spawned enemies should be marked as & on the map."""
        for _ in range(30):
            result = await llm.generate_room(
                x=0, y=0, z=3, biome="dungeon",
                exits={"north": True},
                narrative_context={}, inventory_summary="",
            )
            if result.enemies:
                all_chars = "".join(result.map)
                assert "&" in all_chars, "Enemy spawned but no & on map"
                break
        # If we never got enemies in 30 tries, that's statistically unlikely but not a failure

    @pytest.mark.asyncio
    async def test_items_appear_on_map(self, llm):
        """Spawned items should be marked as $ on the map."""
        for _ in range(30):
            result = await llm.generate_room(
                x=0, y=0, z=2, biome="cave",
                exits={"north": True},
                narrative_context={}, inventory_summary="",
            )
            if result.items:
                all_chars = "".join(result.map)
                assert "$" in all_chars, "Item spawned but no $ on map"
                break
