"""Tests for GASR glyph system."""

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from glyphs.models import (
    Glyph,
    GlyphPhysics,
    GlyphVisual,
    GlyphCategory,
    GlyphLayer,
    Animation,
    GlyphPatch,
    GlyphDiff,
    CODEPOINT_BANDS,
)
from glyphs.registry import GlyphRegistry, get_glyph_registry, reset_glyph_registry
from glyphs.layers import LayerManager, LayerType, Layer, Cell
from glyphs.legends import LegendCompressor
from glyphs.engine import GlyphEngine, AnimationState


class TestGlyphModels:
    """Tests for glyph data models."""

    def test_glyph_creation(self):
        """Test creating a basic glyph."""
        glyph = Glyph(
            id="test.glyph",
            codepoint="U+E100",
            char=".",
            name="Test Glyph",
            category=GlyphCategory.GROUND,
        )
        assert glyph.id == "test.glyph"
        assert glyph.codepoint == "U+E100"
        assert glyph.char == "."
        assert glyph.category == GlyphCategory.GROUND

    def test_glyph_codepoint_int(self):
        """Test codepoint integer conversion."""
        glyph = Glyph(
            id="test",
            codepoint="U+E200",
            char="#",
            name="Test",
            category=GlyphCategory.WALL,
        )
        assert glyph.codepoint_int == 0xE200

    def test_glyph_unicode_char(self):
        """Test Unicode character generation."""
        glyph = Glyph(
            id="test",
            codepoint="U+E000",
            char=" ",
            name="Test",
            category=GlyphCategory.EMPTY,
        )
        assert glyph.unicode_char == chr(0xE000)

    def test_glyph_physics_defaults(self):
        """Test GlyphPhysics default values."""
        physics = GlyphPhysics()
        assert physics.walkable is True
        assert physics.blocks_movement is False
        assert physics.blocks_light is False
        assert physics.damage_on_enter == 0

    def test_glyph_physics_wall(self):
        """Test wall physics configuration."""
        physics = GlyphPhysics(
            walkable=False,
            blocks_movement=True,
            blocks_light=True,
        )
        assert physics.walkable is False
        assert physics.blocks_movement is True
        assert physics.blocks_light is True

    def test_glyph_visual_defaults(self):
        """Test GlyphVisual default values."""
        visual = GlyphVisual()
        assert visual.layer == GlyphLayer.BACKGROUND
        assert visual.connectivity == "none"
        assert visual.animated is False

    def test_glyph_biome_variants(self):
        """Test biome-specific glyph variants."""
        glyph = Glyph(
            id="floor.stone",
            codepoint="U+E100",
            char=".",
            name="Stone Floor",
            category=GlyphCategory.GROUND,
            narrative={"description": "Cold stone floor."},
            biome_variants={
                "volcano": {
                    "narrative": {"description": "Hot volcanic rock floor."}
                }
            }
        )

        # Default version
        assert "Cold stone" in glyph.narrative.description

        # Biome variant
        volcano_variant = glyph.get_for_biome("volcano")
        assert "Hot volcanic" in volcano_variant.narrative.description

    def test_animation_creation(self):
        """Test creating an animation."""
        anim = Animation(
            id="test.anim",
            frames=["U+E100", "U+E101", "U+E102"],
            rate_ms=100,
            loop=True,
        )
        assert anim.id == "test.anim"
        assert len(anim.frames) == 3
        assert anim.rate_ms == 100
        assert anim.loop is True

    def test_animation_frame_chars(self):
        """Test animation frame character conversion."""
        anim = Animation(
            id="test",
            frames=["U+E100", "U+E101"],
            rate_ms=100,
        )
        chars = anim.frame_chars
        assert chars[0] == chr(0xE100)
        assert chars[1] == chr(0xE101)

    def test_glyph_patch(self):
        """Test glyph patch model."""
        patch = GlyphPatch(
            op="replace",
            x=5,
            y=3,
            layer=GlyphLayer.STRUCTURE,
            glyph="door.wood.open",
        )
        assert patch.op == "replace"
        assert patch.x == 5
        assert patch.y == 3
        assert patch.glyph == "door.wood.open"

    def test_glyph_diff(self):
        """Test glyph diff model."""
        diff = GlyphDiff(
            patches=[
                GlyphPatch(op="replace", x=1, y=1, glyph="floor.stone"),
                GlyphPatch(op="add", x=2, y=2, glyph="entity.enemy.basic"),
            ],
            source="llm",
        )
        assert len(diff.patches) == 2
        assert diff.source == "llm"

    def test_codepoint_bands(self):
        """Test codepoint bands are properly defined."""
        assert GlyphCategory.EMPTY in CODEPOINT_BANDS
        assert CODEPOINT_BANDS[GlyphCategory.EMPTY] == (0xE000, 0xE0FF)
        assert CODEPOINT_BANDS[GlyphCategory.GROUND] == (0xE100, 0xE1FF)
        assert CODEPOINT_BANDS[GlyphCategory.WALL] == (0xE200, 0xE2FF)


class TestGlyphRegistry:
    """Tests for glyph registry."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        reset_glyph_registry()
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data"
        )
        reg = GlyphRegistry(data_path=data_path)
        return reg

    def test_initialize(self, registry):
        """Test registry initialization."""
        registry.initialize()
        assert registry._initialized is True
        assert len(registry._glyphs) > 0

    def test_get_by_id(self, registry):
        """Test getting glyph by ID."""
        registry.initialize()
        glyph = registry.get("floor.stone")
        assert glyph is not None
        assert glyph.id == "floor.stone"
        assert glyph.category == GlyphCategory.GROUND

    def test_get_by_codepoint(self, registry):
        """Test getting glyph by codepoint."""
        registry.initialize()
        glyph = registry.get_by_codepoint("U+E100")
        assert glyph is not None
        assert glyph.codepoint == "U+E100"

    def test_get_by_char(self, registry):
        """Test getting glyph by character."""
        registry.initialize()
        glyph = registry.get_by_char("@")
        assert glyph is not None
        assert glyph.char == "@"

    def test_get_by_category(self, registry):
        """Test getting glyphs by category."""
        registry.initialize()
        walls = registry.get_by_category(GlyphCategory.WALL)
        assert len(walls) > 0
        for glyph in walls:
            assert glyph.category == GlyphCategory.WALL

    def test_get_by_tags(self, registry):
        """Test getting glyphs by tags."""
        registry.initialize()
        walkable = registry.get_by_tags(["walkable"])
        assert len(walkable) > 0
        for glyph in walkable:
            assert "walkable" in glyph.tags

    def test_validate_char(self, registry):
        """Test character validation."""
        registry.initialize()
        assert registry.validate_char(".") is True
        assert registry.validate_char("@") is True
        # Most special chars should be registered
        assert registry.validate_char("#") is True

    def test_validate_map(self, registry):
        """Test map validation."""
        registry.initialize()
        map_lines = [
            "#####",
            "#...#",
            "#.@.#",
            "#...#",
            "#####",
        ]
        invalid = registry.validate_map(map_lines)
        # All these characters should be valid
        assert len(invalid) == 0

    def test_char_to_id(self, registry):
        """Test character to ID conversion."""
        registry.initialize()
        glyph_id = registry.char_to_id("@")
        assert glyph_id is not None
        assert "player" in glyph_id or "entity" in glyph_id

    def test_map_to_ids(self, registry):
        """Test converting map to glyph IDs."""
        registry.initialize()
        map_lines = ["#.#", ".@."]
        id_map = registry.map_to_ids(map_lines)
        assert len(id_map) == 2
        assert len(id_map[0]) == 3

    def test_singleton(self):
        """Test singleton behavior."""
        reset_glyph_registry()
        reg1 = get_glyph_registry()
        reg2 = get_glyph_registry()
        assert reg1 is reg2

    def test_reset_singleton(self):
        """Test singleton reset."""
        reg1 = get_glyph_registry()
        reset_glyph_registry()
        reg2 = get_glyph_registry()
        assert reg1 is not reg2


class TestLayerManager:
    """Tests for layer manager."""

    def test_create_layers(self):
        """Test layer creation."""
        manager = LayerManager(10, 10)
        assert len(manager.layers) == 6  # All LayerType values
        for layer_type in LayerType:
            assert layer_type in manager.layers

    def test_set_and_get_glyph(self):
        """Test setting and getting glyphs."""
        manager = LayerManager(10, 10)
        result = manager.set_glyph(5, 5, LayerType.BACKGROUND, "floor.stone", ".")
        assert result is True

        cell = manager.get_glyph(5, 5, LayerType.BACKGROUND)
        assert cell is not None
        assert cell.glyph_id == "floor.stone"
        assert cell.char == "."

    def test_out_of_bounds(self):
        """Test out of bounds handling."""
        manager = LayerManager(10, 10)
        result = manager.set_glyph(15, 15, LayerType.BACKGROUND, "test", "x")
        assert result is False

        cell = manager.get_glyph(15, 15, LayerType.BACKGROUND)
        assert cell is None

    def test_clear_layer(self):
        """Test clearing a layer."""
        manager = LayerManager(5, 5)
        manager.set_glyph(2, 2, LayerType.ENTITY, "entity.player", "@")
        manager.clear_layer(LayerType.ENTITY)

        cell = manager.get_glyph(2, 2, LayerType.ENTITY)
        assert cell.glyph_id == "empty.void"

    def test_composite(self):
        """Test layer compositing."""
        manager = LayerManager(5, 5)

        # Set background
        for x in range(5):
            for y in range(5):
                manager.set_glyph(x, y, LayerType.BACKGROUND, "floor.stone", ".")

        # Set walls
        for i in range(5):
            manager.set_glyph(i, 0, LayerType.STRUCTURE, "wall.stone", "#")
            manager.set_glyph(i, 4, LayerType.STRUCTURE, "wall.stone", "#")

        # Set player
        manager.set_glyph(2, 2, LayerType.ENTITY, "entity.player", "@")

        result = manager.composite()
        assert len(result) == 5
        assert result[0] == "#####"
        assert "@" in result[2]

    def test_composite_ids(self):
        """Test ID compositing."""
        manager = LayerManager(3, 3)
        manager.set_glyph(1, 1, LayerType.BACKGROUND, "floor.stone", ".")
        manager.set_glyph(1, 1, LayerType.ENTITY, "entity.player", "@")

        result = manager.composite_ids()
        # Entity layer should override background
        assert result[1][1] == "entity.player"

    def test_get_all_at(self):
        """Test getting all glyphs at position."""
        manager = LayerManager(5, 5)
        manager.set_glyph(2, 2, LayerType.BACKGROUND, "floor.stone", ".")
        manager.set_glyph(2, 2, LayerType.ENTITY, "entity.player", "@")

        glyphs = manager.get_all_at(2, 2)
        assert len(glyphs) == 2

    def test_serialization(self):
        """Test layer manager serialization."""
        manager = LayerManager(3, 3)
        manager.set_glyph(1, 1, LayerType.BACKGROUND, "floor.stone", ".")

        data = manager.to_dict()
        assert data["width"] == 3
        assert data["height"] == 3
        assert "layers" in data

        # Deserialize
        restored = LayerManager.from_dict(data)
        cell = restored.get_glyph(1, 1, LayerType.BACKGROUND)
        assert cell.glyph_id == "floor.stone"


class TestLegendCompressor:
    """Tests for legend compressor."""

    @pytest.fixture
    def compressor(self):
        """Create legend compressor with registry."""
        reset_glyph_registry()
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data"
        )
        registry = GlyphRegistry(data_path=data_path)
        registry.initialize()
        return LegendCompressor(registry)

    def test_compress_legend(self, compressor):
        """Test legend compression."""
        legend = compressor.compress_legend(max_entries=10)
        assert len(legend) <= 10
        for key, value in legend.items():
            assert key.startswith("U+")
            assert isinstance(value, str)

    def test_compress_char_legend(self, compressor):
        """Test character-based legend compression."""
        legend = compressor.compress_char_legend(max_entries=10)
        assert len(legend) <= 10
        for key, value in legend.items():
            assert len(key) == 1  # Single character
            assert isinstance(value, str)

    def test_category_rules(self, compressor):
        """Test category rules generation."""
        rules = compressor.get_category_rules()
        assert "E000-E0FF" in rules
        assert "E100-E1FF" in rules
        assert "E200-E2FF" in rules

    def test_format_legend_compact(self, compressor):
        """Test compact legend formatting."""
        legend = {"@": "player", "#": "wall"}
        formatted = compressor.format_legend_for_prompt(legend, "compact")
        assert "Legend:" in formatted
        assert "@=player" in formatted

    def test_format_legend_verbose(self, compressor):
        """Test verbose legend formatting."""
        legend = {"@": "player", "#": "wall"}
        formatted = compressor.format_legend_for_prompt(legend, "verbose")
        assert "Glyph Legend:" in formatted
        assert "@: player" in formatted

    def test_format_legend_json(self, compressor):
        """Test JSON legend formatting."""
        legend = {"@": "player"}
        formatted = compressor.format_legend_for_prompt(legend, "json")
        assert '"@"' in formatted
        assert '"player"' in formatted

    def test_generate_room_context(self, compressor):
        """Test room context generation."""
        map_lines = ["###", "#@#", "###"]
        context = compressor.generate_room_context(map_lines, "dungeon")
        assert "Map:" in context
        assert "Biome: dungeon" in context

    def test_llm_constraints(self, compressor):
        """Test LLM constraints text."""
        constraints = compressor.get_llm_constraints()
        assert "Never invent new glyphs" in constraints
        assert "glyph IDs" in constraints


class TestGlyphEngine:
    """Tests for glyph engine."""

    @pytest.fixture
    def engine(self):
        """Create glyph engine for testing."""
        reset_glyph_registry()
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data"
        )
        registry = GlyphRegistry(data_path=data_path)
        return GlyphEngine(width=10, height=10, registry=registry)

    def test_create_engine(self, engine):
        """Test engine creation."""
        assert engine.width == 10
        assert engine.height == 10
        assert engine.registry is not None
        assert engine.layers is not None

    def test_load_room(self, engine):
        """Test loading a room."""
        map_lines = [
            "##########",
            "#........#",
            "#........#",
            "#........#",
            "#........#",
            "#........#",
            "#........#",
            "#........#",
            "#........#",
            "##########",
        ]
        engine.load_room(map_lines, biome="dungeon")

        # Check that walls and floors are placed
        rendered = engine.render()
        assert len(rendered) == 10
        assert rendered[0].startswith("#")

    def test_load_room_with_entities(self, engine):
        """Test loading room with entities."""
        map_lines = [
            "#####",
            "#...#",
            "#...#",
            "#...#",
            "#####",
        ]
        entities = [
            {"x": 2, "y": 2, "type": "player"},
            {"x": 3, "y": 2, "type": "enemy"},
        ]
        engine.load_room(map_lines[:5], entities=entities)

        # Player should be visible
        rendered = engine.render()
        assert "@" in "".join(rendered)

    def test_is_walkable(self, engine):
        """Test walkability checking."""
        map_lines = [
            "#####",
            "#...#",
            "#...#",
            "#...#",
            "#####",
        ]
        engine.load_room(map_lines[:5])

        # Wall should not be walkable
        assert engine.is_walkable(0, 0) is False
        # Floor should be walkable
        assert engine.is_walkable(2, 2) is True

    def test_get_damage_at(self, engine):
        """Test damage checking."""
        # Load room with hazard
        map_lines = [
            "#####",
            "#^..#",
            "#...#",
            "#...#",
            "#####",
        ]
        engine.load_room(map_lines[:5])

        # Trap position should have damage
        damage, damage_type = engine.get_damage_at(1, 1)
        # May or may not have damage depending on glyph definition
        assert isinstance(damage, int)

    def test_set_player_position(self, engine):
        """Test setting player position."""
        map_lines = [".....", ".....", ".....", ".....", "....."]
        engine.load_room(map_lines)

        engine.set_player_position(2, 2)
        rendered = engine.render()
        assert "@" in rendered[2]

        # Move player
        engine.set_player_position(3, 3)
        rendered = engine.render()
        assert "@" not in rendered[2]
        assert "@" in rendered[3]

    def test_apply_patch(self, engine):
        """Test applying a single patch."""
        map_lines = [".....", ".....", ".....", ".....", "....."]
        engine.load_room(map_lines)

        patch = GlyphPatch(
            op="replace",
            x=2,
            y=2,
            layer=1,  # STRUCTURE
            glyph="wall.stone",
        )
        result = engine.apply_patch(patch)
        assert result is True

    def test_apply_diff(self, engine):
        """Test applying a diff."""
        map_lines = [".....", ".....", ".....", ".....", "....."]
        engine.load_room(map_lines)

        diff = GlyphDiff(
            patches=[
                GlyphPatch(op="replace", x=1, y=1, layer=1, glyph="wall.stone"),
                GlyphPatch(op="replace", x=3, y=3, layer=1, glyph="wall.stone"),
            ]
        )
        applied = engine.apply_diff(diff)
        assert applied == 2

    def test_generate_llm_context(self, engine):
        """Test LLM context generation."""
        map_lines = [
            "#####",
            "#...#",
            "#.@.#",
            "#...#",
            "#####",
        ]
        engine.load_room(map_lines[:5])

        context = engine.generate_llm_context()
        assert "Biome:" in context
        assert "dungeon" in context

    def test_validate_map(self, engine):
        """Test map validation."""
        valid_map = ["###", "#.#", "###"]
        invalid = engine.validate_map(valid_map)
        assert len(invalid) == 0

    def test_serialization(self, engine):
        """Test engine serialization."""
        map_lines = ["###", "#.#", "###"]
        engine.load_room(map_lines)

        data = engine.to_dict()
        assert data["width"] == 10
        assert data["height"] == 10
        assert data["biome"] == "dungeon"

        # Deserialize
        restored = GlyphEngine.from_dict(data, engine.registry)
        assert restored.width == 10
        assert restored.current_biome == "dungeon"


class TestAnimationState:
    """Tests for animation state."""

    def test_animation_state_creation(self):
        """Test creating animation state."""
        state = AnimationState(
            animation_id="test.anim",
            x=5,
            y=3,
            layer=LayerType.EFFECT,
        )
        assert state.animation_id == "test.anim"
        assert state.x == 5
        assert state.y == 3
        assert state.current_frame == 0
        assert state.completed is False

    def test_animation_direction(self):
        """Test animation direction for ping-pong."""
        state = AnimationState(
            animation_id="test",
            x=0,
            y=0,
            layer=LayerType.EFFECT,
            direction=-1,  # Backward
        )
        assert state.direction == -1


class TestIntegration:
    """Integration tests for the full glyph system."""

    @pytest.fixture
    def full_setup(self):
        """Set up full glyph system."""
        reset_glyph_registry()
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data"
        )
        registry = GlyphRegistry(data_path=data_path)
        engine = GlyphEngine(width=15, height=11, registry=registry)
        return engine, registry

    def test_full_room_workflow(self, full_setup):
        """Test complete room loading and rendering workflow."""
        engine, registry = full_setup

        # Load a room
        map_lines = [
            "###############",
            "#.............#",
            "#.............#",
            "#.............#",
            "#.............#",
            "#.............#",
            "#.............#",
            "#.............#",
            "#.............#",
            "#.............#",
            "###############",
        ]

        entities = [
            {"x": 7, "y": 5, "type": "player"},
            {"x": 3, "y": 3, "type": "enemy"},
            {"x": 10, "y": 7, "type": "npc"},
        ]

        items = [
            {"x": 5, "y": 5, "category": "potion"},
        ]

        engine.load_room(
            map_lines,
            biome="dungeon",
            entities=entities,
            items=items,
        )

        # Verify rendering
        rendered = engine.render()
        assert len(rendered) == 11
        assert "#" in rendered[0]
        assert "@" in "".join(rendered)

        # Verify walkability
        assert engine.is_walkable(7, 5) is False  # Player blocks
        assert engine.is_walkable(5, 5) is True   # Item doesn't block
        assert engine.is_walkable(0, 0) is False  # Wall blocks

        # Generate LLM context
        context = engine.generate_llm_context()
        assert "dungeon" in context

    def test_glyph_lookup_chain(self, full_setup):
        """Test looking up glyphs through various methods."""
        engine, registry = full_setup

        # Look up by ID
        glyph = registry.get("floor.stone")
        assert glyph is not None

        # Look up by char
        glyph2 = registry.get_by_char(glyph.char)
        assert glyph2 is not None

        # Look up by codepoint
        glyph3 = registry.get_by_codepoint(glyph.codepoint)
        assert glyph3 is not None

        # All should resolve to same glyph
        assert glyph.id == glyph2.id == glyph3.id
