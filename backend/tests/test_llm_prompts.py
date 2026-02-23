"""Tests for LLM prompt construction — no API calls required."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock

from llm_engine import LLMEngine, RoomGenerationResponse, DialogueResponse, CombatNarrationResponse


@pytest.fixture
def llm():
    """Create an LLM engine with no API client (offline mode)."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "", "LLM_MODEL": "test-model"}):
        engine = LLMEngine()
        engine.client = None  # Ensure offline
    return engine


class TestLLMEngineInit:
    """Tests for LLMEngine initialization."""

    def test_is_not_available_without_client(self, llm):
        assert llm.is_available() is False

    def test_temperature_settings(self, llm):
        assert "exploration" in llm.temperatures
        assert "combat" in llm.temperatures
        assert "dialogue" in llm.temperatures
        assert "description" in llm.temperatures
        assert llm.temperatures["combat"] < llm.temperatures["exploration"]

    def test_system_prompt_contains_tile_chars(self, llm):
        assert "▓" in llm.system_prompt
        assert "░" in llm.system_prompt
        assert "@" in llm.system_prompt
        assert "&" in llm.system_prompt

    def test_system_prompt_requests_json(self, llm):
        assert "JSON" in llm.system_prompt


class TestBiomePromptData:
    """Tests for biome prompt template loading."""

    def test_biome_prompts_loaded(self, llm):
        """biomes.json should be loaded into game_data."""
        biome_prompts = llm.game_data.get("biome_prompts", {})
        # If the file exists, it should have content
        prompts_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "biomes.json")
        if os.path.exists(prompts_path):
            assert len(biome_prompts) > 0

    def test_biome_prompts_have_required_fields(self, llm):
        biome_prompts = llm.game_data.get("biome_prompts", {})
        required_fields = ["atmosphere", "tile_vocabulary", "enemy_archetypes", "item_themes"]

        for biome_name, biome_data in biome_prompts.items():
            for field in required_fields:
                assert field in biome_data, f"Biome '{biome_name}' missing field '{field}'"

    def test_biome_tile_vocabulary_has_accents(self, llm):
        biome_prompts = llm.game_data.get("biome_prompts", {})
        for biome_name, biome_data in biome_prompts.items():
            tiles = biome_data.get("tile_vocabulary", {})
            assert "accent_1" in tiles, f"Biome '{biome_name}' missing accent_1"
            assert "accent_2" in tiles, f"Biome '{biome_name}' missing accent_2"


class TestFallbackRoomGeneration:
    """Tests for fallback room generation (no LLM)."""

    @pytest.mark.asyncio
    async def test_fallback_room_returned_when_offline(self, llm):
        """generate_room returns fallback when client is None."""
        result = await llm.generate_room(
            x=0, y=0, z=0,
            biome="dungeon",
            exits={"north": True, "south": True},
            narrative_context={"story_summary": "Test"},
            inventory_summary="Empty",
        )

        assert isinstance(result, RoomGenerationResponse)
        assert len(result.map) > 0
        assert len(result.description) > 0

    @pytest.mark.asyncio
    async def test_fallback_room_has_valid_map(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=0,
            biome="cave",
            exits={"north": True},
            narrative_context={},
            inventory_summary="",
        )

        # Map should have rows, all same length (some biomes use compact 8-row maps)
        assert len(result.map) >= 7
        row_lengths = [len(row) for row in result.map]
        assert len(set(row_lengths)) == 1  # all same length

    @pytest.mark.asyncio
    async def test_fallback_room_respects_exits(self, llm):
        result = await llm.generate_room(
            x=0, y=0, z=0,
            biome="dungeon",
            exits={"north": True, "south": True, "east": False, "west": False},
            narrative_context={},
            inventory_summary="",
        )

        # North exit: top row mid should be space
        mid_col = len(result.map[0]) // 2
        assert result.map[0][mid_col] == " ", "North exit should be open"
        # South exit: bottom row mid should be space
        assert result.map[-1][mid_col] == " ", "South exit should be open"


class TestDialogueFallback:
    """Tests for dialogue fallback when LLM is unavailable."""

    @pytest.mark.asyncio
    async def test_dialogue_fallback(self, llm):
        result = await llm.generate_dialogue(
            npc_id="old_sage",
            npc_name="Old Sage",
            personality="wise",
            player_input="Hello",
            narrative_context={},
            dialogue_history=[],
        )

        assert isinstance(result, DialogueResponse)
        assert "Old Sage" in result.speech
        assert result.mood == "neutral"


class TestCombatNarrationFallback:
    """Tests for combat narration fallback."""

    @pytest.mark.asyncio
    async def test_combat_narration_fallback(self, llm):
        result = await llm.generate_combat_narration(
            player_action="attack",
            enemy_name="Goblin",
            outcome="Dealt 5 damage.",
            player_stats={"hp": 80, "max_hp": 100},
            enemy_stats={"hp": 10, "max_hp": 15},
            is_victory=False,
            is_defeat=False,
        )

        assert isinstance(result, CombatNarrationResponse)
        assert "attack" in result.narration
        assert "Goblin" in result.narration
        assert result.dramatic_moment is False

    @pytest.mark.asyncio
    async def test_combat_narration_victory_is_dramatic(self, llm):
        result = await llm.generate_combat_narration(
            player_action="final blow",
            enemy_name="Dragon",
            outcome="The Dragon falls!",
            player_stats={"hp": 5, "max_hp": 100},
            enemy_stats={"hp": 0, "max_hp": 200},
            is_victory=True,
            is_defeat=False,
        )

        assert result.dramatic_moment is True


class TestItemDescriptionFallback:
    """Tests for item description fallback."""

    @pytest.mark.asyncio
    async def test_item_description_fallback(self, llm):
        result = await llm.generate_item_description(
            item_id="healing_potion",
            item_name="Healing Potion",
            context="Found in a dungeon room",
        )

        assert isinstance(result, str)
        assert "Healing Potion" in result


class TestStorySummaryFallback:
    """Tests for story summary fallback."""

    @pytest.mark.asyncio
    async def test_story_summary_returns_current(self, llm):
        result = await llm.summarize_story(
            events=["Fought a goblin", "Found a potion"],
            current_summary="An adventurer explores the dungeon.",
        )

        assert result == "An adventurer explores the dungeon."


class TestResponseModels:
    """Tests for Pydantic response models."""

    def test_room_response_defaults(self):
        room = RoomGenerationResponse(
            map=["▓▓▓", "▓░▓", "▓▓▓"],
            description="A small room.",
        )
        assert room.enemies == []
        assert room.items == []
        assert room.npcs == []
        assert room.features == []

    def test_dialogue_response_defaults(self):
        resp = DialogueResponse(speech="Hello!")
        assert resp.mood == "neutral"
        assert resp.hints == []
        assert resp.trade_available is False

    def test_combat_narration_response_defaults(self):
        resp = CombatNarrationResponse(narration="You swing your sword.")
        assert resp.dramatic_moment is False
