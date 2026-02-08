"""Tests for GASR glyph system -- models and registry only."""

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

    def test_glyph_lookup_chain(self, registry):
        """Test looking up glyphs through various methods."""
        registry.initialize()

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
