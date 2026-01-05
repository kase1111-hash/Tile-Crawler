"""Tests for Procedural Glyph Foundry system."""

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foundry.grammar import (
    TileGrammar,
    TileSpec,
    EdgeSignature,
    EdgeCode,
    TileStyle,
    TileSize,
    EDGE_COMPATIBILITY,
    STANDARD_GRAMMARS,
)
from foundry.palettes import (
    Palette,
    Color,
    PaletteManager,
    get_palette_manager,
    reset_palette_manager,
)
from foundry.edges import (
    EdgeSystem,
    EdgeCompatibility,
    Direction,
    get_edge_system,
    reset_edge_system,
)
from foundry.generator import (
    TileGenerator,
    GenerationConfig,
    GenerationResult,
    GenerationStatus,
)
from foundry.validator import (
    TileValidator,
    ValidationResult,
    ValidationError,
    ValidationErrorType,
)
from foundry.compiler import (
    TileCompiler,
    GlyphOutput,
    CodepointAllocator,
)


class TestEdgeSignature:
    """Tests for edge signatures."""

    def test_create_signature(self):
        """Test creating an edge signature."""
        sig = EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.SOLID,
            south=EdgeCode.EMPTY,
            west=EdgeCode.EMPTY,
        )
        assert sig.north == EdgeCode.SOLID
        assert sig.south == EdgeCode.EMPTY

    def test_signature_to_code(self):
        """Test converting signature to code string."""
        sig = EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.EMPTY,
            south=EdgeCode.FLOOR,
            west=EdgeCode.WATER,
        )
        code = sig.to_code()
        assert code == "1023"

    def test_signature_from_code(self):
        """Test parsing signature from code string."""
        sig = EdgeSignature.from_code("1100")
        assert sig.north == EdgeCode.SOLID
        assert sig.east == EdgeCode.SOLID
        assert sig.south == EdgeCode.EMPTY
        assert sig.west == EdgeCode.EMPTY

    def test_signature_rotation(self):
        """Test rotating signature."""
        sig = EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.EMPTY,
            south=EdgeCode.FLOOR,
            west=EdgeCode.WATER,
        )
        rotated = sig.rotated(1)  # 90 degrees clockwise
        assert rotated.north == EdgeCode.WATER
        assert rotated.east == EdgeCode.SOLID
        assert rotated.south == EdgeCode.EMPTY
        assert rotated.west == EdgeCode.FLOOR

    def test_signature_flip_horizontal(self):
        """Test horizontal flip."""
        sig = EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.EMPTY,
            south=EdgeCode.FLOOR,
            west=EdgeCode.WATER,
        )
        flipped = sig.flipped_horizontal()
        assert flipped.east == EdgeCode.WATER
        assert flipped.west == EdgeCode.EMPTY

    def test_signature_compatibility(self):
        """Test edge compatibility checking."""
        wall = EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.SOLID,
            south=EdgeCode.SOLID,
            west=EdgeCode.SOLID,
        )
        corner = EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.SOLID,
            south=EdgeCode.EMPTY,
            west=EdgeCode.EMPTY,
        )
        # Wall's south should connect with corner's north
        assert wall.compatible_with(corner, "south")


class TestTileGrammar:
    """Tests for tile grammar."""

    def test_create_grammar(self):
        """Test creating a tile grammar."""
        grammar = TileGrammar(
            category="wall",
            subcategory="solid",
            palette="stone_gray",
            edges=EdgeSignature(
                north=EdgeCode.SOLID,
                east=EdgeCode.SOLID,
                south=EdgeCode.SOLID,
                west=EdgeCode.SOLID,
            ),
            center="stone",
        )
        assert grammar.category == "wall"
        assert grammar.palette == "stone_gray"

    def test_grammar_generation_id(self):
        """Test generating tile ID from grammar."""
        grammar = TileGrammar(
            category="floor",
            subcategory="stone",
            palette="stone_gray",
            center="tiles",
        )
        tile_id = grammar.to_generation_id()
        assert "floor" in tile_id
        assert "stone" in tile_id

    def test_grammar_variant_count(self):
        """Test variant counting."""
        grammar = TileGrammar(
            category="wall",
            palette="stone_gray",
            damage_state=2,
            lighting_state=1,
        )
        # (damage+1) * (lighting+1) * (moisture+1) * (age+1)
        # (2+1) * (1+1) * (0+1) * (0+1) = 6
        assert grammar.get_variant_count() == 6

    def test_standard_grammars(self):
        """Test standard grammar definitions exist."""
        assert "wall.solid" in STANDARD_GRAMMARS
        assert "floor.stone" in STANDARD_GRAMMARS
        assert "water.shallow" in STANDARD_GRAMMARS


class TestTileSpec:
    """Tests for tile specifications."""

    def test_create_spec(self):
        """Test creating a tile spec."""
        grammar = TileGrammar(
            category="wall",
            palette="stone_gray",
        )
        spec = TileSpec(
            id="test_wall",
            grammar=grammar,
            damage_variants=4,
            lighting_variants=3,
        )
        assert spec.damage_variants == 4
        assert spec.lighting_variants == 3

    def test_spec_total_variants(self):
        """Test calculating total variants."""
        grammar = TileGrammar(category="wall", palette="stone_gray")
        spec = TileSpec(
            id="test",
            grammar=grammar,
            damage_variants=4,
            lighting_variants=3,
            moisture_variants=2,
        )
        # 4 * 3 * 2 * 1 = 24
        assert spec.total_variants() == 24

    def test_spec_with_rotations(self):
        """Test spec with rotation variants."""
        grammar = TileGrammar(category="wall", palette="stone_gray")
        spec = TileSpec(
            id="test",
            grammar=grammar,
            generate_rotations=True,
        )
        # 1 * 1 * 1 * 1 * 4 (rotations) = 4
        assert spec.total_variants() == 4

    def test_expand_grammars(self):
        """Test expanding spec to grammars."""
        grammar = TileGrammar(category="wall", palette="stone_gray")
        spec = TileSpec(
            id="test",
            grammar=grammar,
            damage_variants=2,
        )
        grammars = spec.expand_grammars()
        assert len(grammars) == 2


class TestColor:
    """Tests for color handling."""

    def test_color_from_hex(self):
        """Test creating color from hex."""
        color = Color.from_hex("#ff0000", "red")
        assert color.r == 255
        assert color.g == 0
        assert color.b == 0
        assert color.name == "red"

    def test_color_to_hex(self):
        """Test converting color to hex."""
        color = Color(r=255, g=128, b=0)
        assert color.to_hex() == "#ff8000"

    def test_color_lightened(self):
        """Test lightening a color."""
        color = Color(r=100, g=100, b=100)
        light = color.lightened(0.5)
        assert light.r > color.r
        assert light.g > color.g

    def test_color_darkened(self):
        """Test darkening a color."""
        color = Color(r=200, g=200, b=200)
        dark = color.darkened(0.5)
        assert dark.r < color.r
        assert dark.g < color.g


class TestPalette:
    """Tests for palettes."""

    def test_create_palette(self):
        """Test creating a palette."""
        colors = [
            Color.from_hex("#000000", "black"),
            Color.from_hex("#555555", "dark"),
            Color.from_hex("#aaaaaa", "light"),
            Color.from_hex("#ffffff", "white"),
        ]
        palette = Palette(
            id="test_gray",
            name="Test Gray",
            colors=colors,
        )
        assert palette.color_count == 4
        assert palette.get_color(0).name == "black"

    def test_palette_to_hex_list(self):
        """Test getting hex color list."""
        colors = [
            Color.from_hex("#111111"),
            Color.from_hex("#222222"),
        ]
        palette = Palette(id="test", name="Test", colors=colors)
        hex_list = palette.to_hex_list()
        assert "#111111" in hex_list

    def test_palette_lighting_variants(self):
        """Test generating lighting variants."""
        colors = [Color.from_hex("#808080")]
        palette = Palette(id="test", name="Test", colors=colors)
        variants = palette.derive_lighting_variants()
        assert "dark" in variants
        assert "normal" in variants
        assert "bright" in variants


class TestPaletteManager:
    """Tests for palette manager."""

    @pytest.fixture
    def manager(self):
        reset_palette_manager()
        return get_palette_manager()

    def test_default_palettes(self, manager):
        """Test default palettes are created."""
        manager.initialize()
        assert manager.get("stone_gray") is not None
        assert manager.get("wood_brown") is not None

    def test_get_by_tag(self, manager):
        """Test getting palettes by tag."""
        manager.initialize()
        stone_palettes = manager.get_by_tag("stone")
        assert len(stone_palettes) > 0

    def test_singleton(self):
        """Test singleton behavior."""
        reset_palette_manager()
        m1 = get_palette_manager()
        m2 = get_palette_manager()
        assert m1 is m2


class TestEdgeSystem:
    """Tests for edge compatibility system."""

    @pytest.fixture
    def edge_system(self):
        reset_edge_system()
        system = get_edge_system()
        # Register some test tiles
        system.register_tile("wall.solid", EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.SOLID,
            south=EdgeCode.SOLID,
            west=EdgeCode.SOLID,
        ))
        system.register_tile("floor.basic", EdgeSignature(
            north=EdgeCode.FLOOR,
            east=EdgeCode.FLOOR,
            south=EdgeCode.FLOOR,
            west=EdgeCode.FLOOR,
        ))
        system.register_tile("wall.corner.ne", EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.SOLID,
            south=EdgeCode.EMPTY,
            west=EdgeCode.EMPTY,
        ))
        return system

    def test_register_tile(self, edge_system):
        """Test registering tiles."""
        tile = edge_system.get_tile("wall.solid")
        assert tile is not None
        assert tile.tile_id == "wall.solid"

    def test_can_place_valid(self, edge_system):
        """Test valid tile placement."""
        # Floor next to floor
        can_place = edge_system.can_place("floor.basic", {
            Direction.NORTH: "floor.basic",
        })
        assert can_place is True

    def test_get_compatible(self, edge_system):
        """Test getting compatible tiles."""
        compatible = edge_system.get_compatible_for_direction(
            "wall.solid", Direction.SOUTH
        )
        assert "wall.solid" in compatible

    def test_adjacency_rules(self, edge_system):
        """Test generating adjacency rules."""
        rules = edge_system.generate_adjacency_rules()
        assert "wall.solid" in rules
        assert "north" in rules["wall.solid"]


class TestTileGenerator:
    """Tests for tile generator."""

    @pytest.fixture
    def generator(self):
        return TileGenerator()

    def test_build_prompt(self, generator):
        """Test building generation prompt."""
        grammar = TileGrammar(
            category="wall",
            subcategory="solid",
            palette="stone_gray",
            center="stone",
        )
        prompt = generator.build_prompt(grammar)
        assert "wall" in prompt.lower()
        assert "stone" in prompt.lower()
        assert "pixel" in prompt.lower()

    def test_generate_dry_run(self, generator):
        """Test dry run generation."""
        grammar = TileGrammar(
            category="floor",
            palette="stone_gray",
        )
        result = generator.generate_tile(grammar, dry_run=True)
        assert result.status == GenerationStatus.COMPLETE
        assert result.generation_prompt is not None

    def test_generate_batch(self, generator):
        """Test batch generation."""
        grammar = TileGrammar(category="wall", palette="stone_gray")
        spec = TileSpec(
            id="test",
            grammar=grammar,
            damage_variants=2,
        )
        results = generator.generate_batch(spec, dry_run=True)
        assert len(results) == 2

    def test_combinatorial_stats(self, generator):
        """Test combinatorial generation stats."""
        stats = generator.generate_combinatorial(
            bases=["wall", "floor", "water"],
            edge_variants=4,
            damage_states=2,
            lighting_states=2,
            moisture_states=2,
        )
        # 3 * 4 * 2 * 2 * 2 = 96
        assert stats["total_tiles"] == 96


class TestTileValidator:
    """Tests for tile validator."""

    @pytest.fixture
    def validator(self):
        return TileValidator(strict=True)

    def test_validation_result(self):
        """Test validation result structure."""
        result = ValidationResult(tile_id="test", passed=True)
        assert result.passed is True
        assert result.error_count == 0

    def test_add_error(self):
        """Test adding validation error."""
        result = ValidationResult(tile_id="test", passed=True)
        result.add_error(ValidationError(
            error_type=ValidationErrorType.SIZE_MISMATCH,
            message="Wrong size",
        ))
        assert result.passed is False
        assert result.error_count == 1

    def test_rejection_summary(self, validator):
        """Test generating rejection summary."""
        results = [
            ValidationResult(tile_id="t1", passed=True),
            ValidationResult(tile_id="t2", passed=False),
        ]
        summary = validator.get_rejection_summary(results)
        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1


class TestCodepointAllocator:
    """Tests for codepoint allocation."""

    def test_allocate(self):
        """Test allocating codepoints."""
        from glyphs.models import GlyphCategory
        allocator = CodepointAllocator()
        cp1 = allocator.allocate("tile1", GlyphCategory.WALL)
        cp2 = allocator.allocate("tile2", GlyphCategory.WALL)
        assert cp1 != cp2
        assert cp1.startswith("U+E2")  # Wall range

    def test_allocate_same_tile(self):
        """Test allocating same tile returns same codepoint."""
        from glyphs.models import GlyphCategory
        allocator = CodepointAllocator()
        cp1 = allocator.allocate("tile1", GlyphCategory.GROUND)
        cp2 = allocator.allocate("tile1", GlyphCategory.GROUND)
        assert cp1 == cp2

    def test_allocation_stats(self):
        """Test getting allocation stats."""
        allocator = CodepointAllocator()
        stats = allocator.get_stats()
        assert "wall" in stats
        assert "allocated" in stats["wall"]


class TestTileCompiler:
    """Tests for tile compiler."""

    @pytest.fixture
    def compiler(self):
        return TileCompiler()

    def test_compile_tile(self, compiler):
        """Test compiling a tile."""
        grammar = TileGrammar(
            category="wall",
            subcategory="solid",
            palette="stone_gray",
        )
        output = compiler.compile_tile(grammar)
        assert output.glyph is not None
        assert output.codepoint.startswith("U+E2")  # Wall range

    def test_compile_generates_physics(self, compiler):
        """Test that compilation generates physics."""
        grammar = TileGrammar(
            category="wall",
            palette="stone_gray",
            edges=EdgeSignature(
                north=EdgeCode.SOLID,
                east=EdgeCode.SOLID,
                south=EdgeCode.SOLID,
                west=EdgeCode.SOLID,
            ),
        )
        output = compiler.compile_tile(grammar)
        assert output.glyph.physics.blocks_movement is True
        assert output.glyph.physics.walkable is False

    def test_compile_generates_tags(self, compiler):
        """Test that compilation generates tags."""
        grammar = TileGrammar(
            category="floor",
            palette="stone_gray",
            moisture_state=1,
        )
        output = compiler.compile_tile(grammar)
        assert "wet" in output.glyph.tags
        assert "floor" in output.glyph.tags

    def test_compile_batch(self, compiler):
        """Test batch compilation."""
        grammar = TileGrammar(category="wall", palette="stone_gray")
        specs = [
            TileSpec(id="wall1", grammar=grammar, damage_variants=2),
        ]
        batch = compiler.compile_batch(specs)
        assert len(batch.outputs) == 2
        assert batch.registry_json is not None

    def test_export_registry_json(self, compiler):
        """Test exporting registry JSON."""
        grammar = TileGrammar(category="floor", palette="stone_gray")
        compiler.compile_tile(grammar)
        json_str = compiler.export_registry_json()
        assert "glyphs" in json_str
        assert "version" in json_str


class TestIntegration:
    """Integration tests for the full foundry pipeline."""

    def test_full_pipeline(self):
        """Test complete tile generation pipeline."""
        # 1. Define grammar
        grammar = TileGrammar(
            category="wall",
            subcategory="stone",
            palette="stone_gray",
            edges=EdgeSignature(
                north=EdgeCode.SOLID,
                east=EdgeCode.SOLID,
                south=EdgeCode.SOLID,
                west=EdgeCode.SOLID,
            ),
            center="stone_blocks",
            styles=[TileStyle.PIXEL, TileStyle.HIGH_CONTRAST],
        )

        # 2. Create spec with variants
        spec = TileSpec(
            id="wall.stone.solid",
            grammar=grammar,
            damage_variants=4,
            lighting_variants=3,
            moisture_variants=2,
        )

        # 3. Calculate total tiles
        total = spec.total_variants()
        assert total == 24  # 4 * 3 * 2 * 1

        # 4. Generate prompts
        generator = TileGenerator()
        results = generator.generate_batch(spec, dry_run=True)
        assert len(results) == 24

        # 5. Compile to glyphs
        compiler = TileCompiler()
        batch = compiler.compile_batch([spec])
        assert len(batch.outputs) == 24

        # 6. Verify registry JSON
        import json
        registry = json.loads(batch.registry_json)
        assert len(registry["glyphs"]) == 24

    def test_combinatorial_scale(self):
        """Test that combinatorial generation scales as expected."""
        # 20 bases × 8 edge variants × 4 damage × 3 lighting × 2 moisture
        # = 3,840 tiles

        generator = TileGenerator()
        stats = generator.generate_combinatorial(
            bases=["wall", "floor", "water", "lava", "grass"] * 4,  # 20 bases
            edge_variants=8,
            damage_states=4,
            lighting_states=3,
            moisture_states=2,
        )

        assert stats["total_tiles"] == 3840
        assert "formula" in stats
