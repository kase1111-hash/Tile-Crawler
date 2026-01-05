"""
Glyph Registry - Single source of truth for all glyph definitions.

The registry:
- Loads glyph definitions from JSON
- Provides fast lookup by ID, codepoint, or character
- Validates glyphs against schema
- Supports biome-specific variants
"""

import json
import os
from typing import Optional
from pathlib import Path

from .models import (
    Glyph,
    GlyphCategory,
    Animation,
    CODEPOINT_BANDS,
)


class GlyphRegistry:
    """
    Central registry for all glyph definitions.

    Provides:
    - Lookup by ID, codepoint, or fallback character
    - Category filtering
    - Tag-based queries
    - Biome variant resolution
    - Animation registry
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or self._default_data_path()
        self._glyphs: dict[str, Glyph] = {}
        self._by_codepoint: dict[str, Glyph] = {}
        self._by_char: dict[str, Glyph] = {}
        self._by_category: dict[GlyphCategory, list[Glyph]] = {
            cat: [] for cat in GlyphCategory
        }
        self._animations: dict[str, Animation] = {}
        self._initialized = False

    def _default_data_path(self) -> str:
        """Get default path to glyph data files."""
        backend_dir = Path(__file__).parent.parent
        return str(backend_dir.parent / "data")

    def initialize(self) -> None:
        """Load all glyph definitions."""
        if self._initialized:
            return

        self._load_glyphs()
        self._load_animations()
        self._initialized = True

    def _load_glyphs(self) -> None:
        """Load glyph definitions from JSON."""
        glyph_file = os.path.join(self.data_path, "glyphs.json")

        if not os.path.exists(glyph_file):
            # Fall back to generating from tiles.json
            self._generate_from_tiles()
            return

        with open(glyph_file) as f:
            data = json.load(f)

        for glyph_data in data.get("glyphs", []):
            glyph = Glyph(**glyph_data)
            self._register_glyph(glyph)

    def _generate_from_tiles(self) -> None:
        """Generate glyphs from existing tiles.json for backwards compatibility."""
        tiles_file = os.path.join(self.data_path, "tiles.json")

        if not os.path.exists(tiles_file):
            self._create_default_glyphs()
            return

        with open(tiles_file) as f:
            tiles_data = json.load(f)

        # Codepoint counter per category
        counters = {cat: band[0] for cat, band in CODEPOINT_BANDS.items()}

        for tile_id, tile in tiles_data.get("tiles", {}).items():
            # Map tile category to glyph category
            category = self._map_tile_category(tile.get("category", "terrain"))

            # Assign codepoint
            codepoint = counters[category]
            counters[category] += 1

            glyph = Glyph(
                id=tile_id,
                codepoint=f"U+{codepoint:04X}",
                char=tile.get("char", "?"),
                name=tile.get("name", tile_id),
                category=category,
                tags=self._extract_tags(tile),
                physics={
                    "walkable": tile.get("passable", True),
                    "blocks_movement": not tile.get("passable", True),
                    "blocks_light": tile.get("opaque", False),
                    "damage_on_enter": tile.get("hazard_damage", 0) if tile.get("hazard") else 0,
                    "movement_penalty": tile.get("movement_penalty", 0.0),
                },
                visual={
                    "layer": self._category_to_layer(category),
                    "glow": tile.get("light_source", False),
                    "glow_radius": tile.get("light_radius", 0),
                },
                narrative={
                    "description": tile.get("description", ""),
                },
                llm={
                    "summary": tile.get("description", tile.get("name", "")),
                    "threat": 0.5 if tile.get("hazard") else 0.0,
                    "interest": 0.5 if tile.get("interactive") else 0.2,
                },
            )
            self._register_glyph(glyph)

    def _map_tile_category(self, category: str) -> GlyphCategory:
        """Map existing tile categories to glyph categories."""
        mapping = {
            "structure": GlyphCategory.WALL,
            "terrain": GlyphCategory.GROUND,
            "entity": GlyphCategory.ENTITY,
            "interactive": GlyphCategory.PROP,
            "hazard": GlyphCategory.EFFECT,
            "transition": GlyphCategory.DOOR,
        }
        return mapping.get(category, GlyphCategory.GROUND)

    def _category_to_layer(self, category: GlyphCategory) -> int:
        """Map category to default rendering layer."""
        from .models import GlyphLayer
        mapping = {
            GlyphCategory.EMPTY: GlyphLayer.BACKGROUND,
            GlyphCategory.GROUND: GlyphLayer.BACKGROUND,
            GlyphCategory.WALL: GlyphLayer.STRUCTURE,
            GlyphCategory.DOOR: GlyphLayer.STRUCTURE,
            GlyphCategory.FLUID: GlyphLayer.BACKGROUND,
            GlyphCategory.PROP: GlyphLayer.STRUCTURE,
            GlyphCategory.ITEM: GlyphLayer.ENTITY,
            GlyphCategory.ENTITY: GlyphLayer.ENTITY,
            GlyphCategory.EFFECT: GlyphLayer.EFFECT,
            GlyphCategory.UI: GlyphLayer.UI,
            GlyphCategory.OVERLAY: GlyphLayer.LIGHTING,
            GlyphCategory.ANIMATION: GlyphLayer.EFFECT,
        }
        return mapping.get(category, GlyphLayer.BACKGROUND)

    def _extract_tags(self, tile: dict) -> list[str]:
        """Extract tags from tile properties."""
        tags = []
        if tile.get("passable"):
            tags.append("walkable")
        if tile.get("opaque"):
            tags.append("opaque")
        if tile.get("interactive"):
            tags.append("interactive")
        if tile.get("hazard"):
            tags.append("hazard")
        if tile.get("light_source"):
            tags.append("light_source")
        return tags

    def _create_default_glyphs(self) -> None:
        """Create minimal default glyphs if no data files exist."""
        defaults = [
            Glyph(
                id="empty.void",
                codepoint="U+E000",
                char=" ",
                name="Void",
                category=GlyphCategory.EMPTY,
                physics={"walkable": True},
                llm={"summary": "empty space"},
            ),
            Glyph(
                id="floor.stone",
                codepoint="U+E100",
                char=".",
                name="Stone Floor",
                category=GlyphCategory.GROUND,
                tags=["walkable"],
                physics={"walkable": True},
                llm={"summary": "stone floor"},
            ),
            Glyph(
                id="wall.stone",
                codepoint="U+E200",
                char="#",
                name="Stone Wall",
                category=GlyphCategory.WALL,
                tags=["solid", "opaque"],
                physics={"walkable": False, "blocks_movement": True, "blocks_light": True},
                llm={"summary": "solid stone wall"},
            ),
            Glyph(
                id="entity.player",
                codepoint="U+E700",
                char="@",
                name="Player",
                category=GlyphCategory.ENTITY,
                visual={"layer": 2},
                llm={"summary": "the player character"},
            ),
            Glyph(
                id="entity.enemy",
                codepoint="U+E701",
                char="&",
                name="Enemy",
                category=GlyphCategory.ENTITY,
                visual={"layer": 2},
                llm={"summary": "hostile creature", "threat": 0.7},
            ),
        ]

        for glyph in defaults:
            self._register_glyph(glyph)

    def _register_glyph(self, glyph: Glyph) -> None:
        """Register a glyph in all indices."""
        self._glyphs[glyph.id] = glyph
        self._by_codepoint[glyph.codepoint] = glyph
        self._by_char[glyph.char] = glyph
        self._by_category[glyph.category].append(glyph)

    def _load_animations(self) -> None:
        """Load animation definitions."""
        anim_file = os.path.join(self.data_path, "animations.json")

        if not os.path.exists(anim_file):
            return

        with open(anim_file) as f:
            data = json.load(f)

        for anim_data in data.get("animations", []):
            animation = Animation(**anim_data)
            self._animations[animation.id] = animation

    # Query methods

    def get(self, glyph_id: str) -> Optional[Glyph]:
        """Get glyph by ID."""
        self.initialize()
        return self._glyphs.get(glyph_id)

    def get_by_codepoint(self, codepoint: str) -> Optional[Glyph]:
        """Get glyph by codepoint (e.g., 'U+E100')."""
        self.initialize()
        return self._by_codepoint.get(codepoint)

    def get_by_char(self, char: str) -> Optional[Glyph]:
        """Get glyph by fallback character."""
        self.initialize()
        return self._by_char.get(char)

    def get_by_category(self, category: GlyphCategory) -> list[Glyph]:
        """Get all glyphs in a category."""
        self.initialize()
        return self._by_category.get(category, [])

    def get_by_tags(self, tags: list[str], match_all: bool = True) -> list[Glyph]:
        """Get glyphs matching tags."""
        self.initialize()
        results = []
        for glyph in self._glyphs.values():
            if match_all:
                if all(tag in glyph.tags for tag in tags):
                    results.append(glyph)
            else:
                if any(tag in glyph.tags for tag in tags):
                    results.append(glyph)
        return results

    def get_walkable(self) -> list[Glyph]:
        """Get all walkable glyphs."""
        return self.get_by_tags(["walkable"])

    def get_animation(self, animation_id: str) -> Optional[Animation]:
        """Get animation by ID."""
        self.initialize()
        return self._animations.get(animation_id)

    def all_glyphs(self) -> list[Glyph]:
        """Get all registered glyphs."""
        self.initialize()
        return list(self._glyphs.values())

    def all_ids(self) -> list[str]:
        """Get all glyph IDs."""
        self.initialize()
        return list(self._glyphs.keys())

    # Validation methods

    def validate_char(self, char: str) -> bool:
        """Check if a character is a valid glyph."""
        self.initialize()
        return char in self._by_char

    def validate_map(self, map_lines: list[str]) -> list[tuple[int, int, str]]:
        """
        Validate a map, returning list of invalid positions.

        Returns:
            List of (x, y, char) tuples for invalid characters
        """
        self.initialize()
        invalid = []
        for y, line in enumerate(map_lines):
            for x, char in enumerate(line):
                if char not in self._by_char:
                    invalid.append((x, y, char))
        return invalid

    # Conversion methods

    def char_to_id(self, char: str) -> Optional[str]:
        """Convert fallback character to glyph ID."""
        glyph = self.get_by_char(char)
        return glyph.id if glyph else None

    def id_to_char(self, glyph_id: str) -> Optional[str]:
        """Convert glyph ID to fallback character."""
        glyph = self.get(glyph_id)
        return glyph.char if glyph else None

    def map_to_ids(self, map_lines: list[str]) -> list[list[str]]:
        """Convert character map to glyph ID map."""
        self.initialize()
        result = []
        for line in map_lines:
            row = []
            for char in line:
                glyph = self.get_by_char(char)
                row.append(glyph.id if glyph else "unknown")
            result.append(row)
        return result

    def ids_to_map(self, id_map: list[list[str]]) -> list[str]:
        """Convert glyph ID map to character map."""
        self.initialize()
        result = []
        for row in id_map:
            line = ""
            for glyph_id in row:
                glyph = self.get(glyph_id)
                line += glyph.char if glyph else "?"
            result.append(line)
        return result


# Singleton management
_glyph_registry: Optional[GlyphRegistry] = None


def get_glyph_registry(data_path: Optional[str] = None) -> GlyphRegistry:
    """Get the singleton glyph registry instance."""
    global _glyph_registry
    if _glyph_registry is None:
        _glyph_registry = GlyphRegistry(data_path)
    return _glyph_registry


def reset_glyph_registry() -> None:
    """Reset the glyph registry singleton (for testing)."""
    global _glyph_registry
    _glyph_registry = None
