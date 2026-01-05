"""
Tile Compiler - Converts generated tiles to glyphs and registry entries.

Pipeline:
1. Tile PNG → Font glyph (codepoint assignment)
2. Grammar → Registry entry (auto-generated metadata)
3. Export TTF/OTF font file
4. Generate glyphs.json entries
"""

import json
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

from .grammar import TileGrammar, TileSpec, EdgeCode, TileStyle
from .palettes import Palette


# Import glyph models
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from glyphs.models import (
    Glyph,
    GlyphPhysics,
    GlyphVisual,
    GlyphAudio,
    GlyphNarrative,
    GlyphLLM,
    GlyphCategory,
    GlyphLayer,
    CODEPOINT_BANDS as GLYPH_CODEPOINT_BANDS,
)


@dataclass
class GlyphOutput:
    """Output from compiling a tile to a glyph."""
    glyph: Glyph
    codepoint: str
    tile_id: str
    image_path: Optional[str] = None
    font_index: Optional[int] = None


@dataclass
class CompilationBatch:
    """A batch of compiled glyphs."""
    outputs: list[GlyphOutput] = field(default_factory=list)
    registry_json: Optional[str] = None
    font_path: Optional[str] = None
    errors: list[str] = field(default_factory=list)


class CodepointAllocator:
    """Allocates Unicode codepoints from PUA ranges."""

    def __init__(self):
        # Track next available codepoint per category
        self._counters: dict[GlyphCategory, int] = {}
        self._allocated: dict[str, str] = {}  # tile_id -> codepoint

        # Initialize counters from band starts
        for category, (start, _) in GLYPH_CODEPOINT_BANDS.items():
            self._counters[category] = start

    def allocate(self, tile_id: str, category: GlyphCategory) -> str:
        """Allocate a codepoint for a tile."""
        # Check if already allocated
        if tile_id in self._allocated:
            return self._allocated[tile_id]

        # Get next codepoint
        start, end = GLYPH_CODEPOINT_BANDS[category]
        codepoint = self._counters[category]

        if codepoint > end:
            raise ValueError(f"Codepoint range exhausted for {category}")

        self._counters[category] = codepoint + 1
        codepoint_str = f"U+{codepoint:04X}"
        self._allocated[tile_id] = codepoint_str

        return codepoint_str

    def get_allocated(self, tile_id: str) -> Optional[str]:
        """Get allocated codepoint for a tile."""
        return self._allocated.get(tile_id)

    def get_stats(self) -> dict:
        """Get allocation statistics."""
        stats = {}
        for category, (start, end) in GLYPH_CODEPOINT_BANDS.items():
            current = self._counters[category]
            stats[category.value] = {
                "allocated": current - start,
                "remaining": end - current + 1,
                "total": end - start + 1,
            }
        return stats


class TileCompiler:
    """
    Compiles tiles to glyphs and generates registry entries.

    Converts tile grammars to full glyph definitions with:
    - Codepoint assignment
    - Physics properties
    - Visual properties
    - Audio cues
    - Narrative text
    - LLM metadata
    """

    def __init__(self):
        self.allocator = CodepointAllocator()
        self._compiled: dict[str, GlyphOutput] = {}

    def compile_tile(
        self,
        grammar: TileGrammar,
        image_path: Optional[str] = None,
        fallback_char: Optional[str] = None,
    ) -> GlyphOutput:
        """
        Compile a tile grammar to a glyph.

        Args:
            grammar: Tile grammar specification
            image_path: Path to tile image (optional)
            fallback_char: Character for legacy rendering

        Returns:
            GlyphOutput with compiled glyph
        """
        tile_id = grammar.to_generation_id()

        # Map grammar category to glyph category
        glyph_category = self._map_category(grammar.category)

        # Allocate codepoint
        codepoint = self.allocator.allocate(tile_id, glyph_category)

        # Determine fallback character
        char = fallback_char or self._default_char(grammar)

        # Build glyph
        glyph = Glyph(
            id=self._generate_glyph_id(grammar),
            codepoint=codepoint,
            char=char,
            name=self._generate_name(grammar),
            category=glyph_category,
            tags=self._generate_tags(grammar),
            variant=grammar.subcategory,
            physics=self._generate_physics(grammar),
            visual=self._generate_visual(grammar),
            audio=self._generate_audio(grammar),
            narrative=self._generate_narrative(grammar),
            llm=self._generate_llm(grammar),
        )

        output = GlyphOutput(
            glyph=glyph,
            codepoint=codepoint,
            tile_id=tile_id,
            image_path=image_path,
        )

        self._compiled[tile_id] = output
        return output

    def _map_category(self, category: str) -> GlyphCategory:
        """Map grammar category to glyph category."""
        mapping = {
            "wall": GlyphCategory.WALL,
            "floor": GlyphCategory.GROUND,
            "ground": GlyphCategory.GROUND,
            "door": GlyphCategory.DOOR,
            "window": GlyphCategory.DOOR,
            "fluid": GlyphCategory.FLUID,
            "water": GlyphCategory.FLUID,
            "lava": GlyphCategory.FLUID,
            "prop": GlyphCategory.PROP,
            "object": GlyphCategory.PROP,
            "item": GlyphCategory.ITEM,
            "entity": GlyphCategory.ENTITY,
            "creature": GlyphCategory.ENTITY,
            "effect": GlyphCategory.EFFECT,
            "particle": GlyphCategory.EFFECT,
            "ui": GlyphCategory.UI,
            "overlay": GlyphCategory.OVERLAY,
            "empty": GlyphCategory.EMPTY,
        }
        return mapping.get(category.lower(), GlyphCategory.PROP)

    def _default_char(self, grammar: TileGrammar) -> str:
        """Get default fallback character for grammar."""
        category_chars = {
            "wall": "#",
            "floor": ".",
            "ground": ".",
            "door": "+",
            "fluid": "~",
            "water": "≈",
            "lava": "▓",
            "prop": "■",
            "item": "!",
            "entity": "&",
            "effect": "*",
            "empty": " ",
        }
        return category_chars.get(grammar.category, "?")

    def _generate_glyph_id(self, grammar: TileGrammar) -> str:
        """Generate glyph ID from grammar."""
        parts = [grammar.category]

        if grammar.subcategory:
            parts.append(grammar.subcategory)

        # Add edge signature for walls/corners
        if grammar.category == "wall":
            edges = grammar.edges
            # Handle both EdgeCode and int types
            n = edges.north if isinstance(edges.north, int) else edges.north.value
            e = edges.east if isinstance(edges.east, int) else edges.east.value
            s = edges.south if isinstance(edges.south, int) else edges.south.value
            w = edges.west if isinstance(edges.west, int) else edges.west.value

            if n == 1 and e == 1 and s == 0 and w == 0:
                parts.append("corner.ne")
            elif n == 0 and e == 1 and s == 1 and w == 0:
                parts.append("corner.se")
            elif n == 0 and e == 0 and s == 1 and w == 1:
                parts.append("corner.sw")
            elif n == 1 and e == 0 and s == 0 and w == 1:
                parts.append("corner.nw")

        # Add state modifiers
        if grammar.damage_state > 0:
            parts.append(["pristine", "scratched", "cracked", "broken"][grammar.damage_state])

        if grammar.moisture_state > 0:
            parts.append("wet")

        if grammar.age_state > 0:
            parts.append(["new", "worn", "ancient"][grammar.age_state])

        return ".".join(parts)

    def _generate_name(self, grammar: TileGrammar) -> str:
        """Generate human-readable name."""
        parts = []

        # State adjectives
        if grammar.damage_state > 0:
            parts.append(["", "Scratched", "Cracked", "Broken"][grammar.damage_state])

        if grammar.moisture_state > 0:
            parts.append("Wet")

        if grammar.age_state > 0:
            parts.append(["", "Worn", "Ancient"][grammar.age_state])

        # Category name
        category_name = grammar.category.replace("_", " ").title()
        parts.append(category_name)

        if grammar.subcategory:
            parts.append(f"({grammar.subcategory})")

        return " ".join(filter(None, parts))

    def _generate_tags(self, grammar: TileGrammar) -> list[str]:
        """Generate tags from grammar."""
        tags = list(grammar.tags)

        # Add category tag
        tags.append(grammar.category)

        # Add physics-derived tags
        edges = grammar.edges
        # Handle both EdgeCode and int types
        n = edges.north if isinstance(edges.north, int) else edges.north.value
        e = edges.east if isinstance(edges.east, int) else edges.east.value
        s = edges.south if isinstance(edges.south, int) else edges.south.value
        w = edges.west if isinstance(edges.west, int) else edges.west.value

        all_solid = all(x == 1 for x in [n, e, s, w])  # EdgeCode.SOLID = 1
        all_empty = all(x == 0 for x in [n, e, s, w])  # EdgeCode.EMPTY = 0

        if all_solid:
            tags.append("solid")
            tags.append("opaque")
        elif all_empty:
            tags.append("passable")
            tags.append("transparent")

        # State tags
        if grammar.damage_state > 0:
            tags.append("damaged")
        if grammar.moisture_state > 0:
            tags.append("wet")
        if grammar.age_state > 0:
            tags.append("aged")

        # Style tags
        for style in grammar.styles:
            style_str = style if isinstance(style, str) else style.value
            tags.append(style_str)

        return list(set(tags))  # Deduplicate

    def _generate_physics(self, grammar: TileGrammar) -> GlyphPhysics:
        """Generate physics properties from grammar."""
        edges = grammar.edges
        # Handle both EdgeCode and int types
        n = edges.north if isinstance(edges.north, int) else edges.north.value
        e = edges.east if isinstance(edges.east, int) else edges.east.value
        s = edges.south if isinstance(edges.south, int) else edges.south.value
        w = edges.west if isinstance(edges.west, int) else edges.west.value

        all_solid = all(x == 1 for x in [n, e, s, w])
        has_solid = any(x == 1 for x in [n, e, s, w])

        # Determine walkability
        walkable = not all_solid
        blocks_movement = all_solid
        blocks_light = all_solid

        # Category overrides
        if grammar.category in ["fluid", "water"]:
            walkable = True
            blocks_movement = False

        if grammar.category in ["lava"]:
            walkable = False
            blocks_movement = True

        # Movement penalty
        movement_penalty = 0.0
        if grammar.category == "fluid":
            movement_penalty = 0.3
        if grammar.moisture_state > 0:
            movement_penalty += 0.1

        # Damage
        damage = 0
        damage_type = None
        if grammar.category == "lava":
            damage = 50
            damage_type = "fire"

        return GlyphPhysics(
            walkable=walkable,
            blocks_movement=blocks_movement,
            blocks_light=blocks_light,
            movement_penalty=movement_penalty,
            damage_on_enter=damage,
            damage_type=damage_type,
        )

    def _generate_visual(self, grammar: TileGrammar) -> GlyphVisual:
        """Generate visual properties from grammar."""
        # Determine layer
        layer = GlyphLayer.BACKGROUND
        if grammar.category in ["wall", "door", "prop"]:
            layer = GlyphLayer.STRUCTURE
        elif grammar.category in ["entity", "item"]:
            layer = GlyphLayer.ENTITY
        elif grammar.category in ["effect", "particle"]:
            layer = GlyphLayer.EFFECT
        elif grammar.category == "overlay":
            layer = GlyphLayer.LIGHTING

        # Glow for light sources
        glow = grammar.center in ["fire", "torch", "crystal", "lava", "magic"]
        glow_radius = 2 if glow else 0

        return GlyphVisual(
            layer=layer,
            connectivity="auto" if grammar.category == "wall" else "none",
            palette=grammar.palette,
            glow=glow,
            glow_radius=glow_radius,
        )

    def _generate_audio(self, grammar: TileGrammar) -> GlyphAudio:
        """Generate audio cues from grammar."""
        # Step sounds based on category/material
        step_sounds = {
            "floor": "movement.step.stone",
            "ground": "movement.step.dirt",
            "grass": "movement.step.grass",
            "wood": "movement.step.wood",
            "water": "movement.splash.light",
            "fluid": "movement.splash.light",
        }

        on_step = step_sounds.get(grammar.category)
        if grammar.moisture_state > 0:
            on_step = "movement.step.wet"

        # Ambient sounds
        ambient = None
        if grammar.category in ["water", "fluid"]:
            ambient = "ambient.water"
        elif grammar.category == "lava":
            ambient = "ambient.lava.bubble"

        return GlyphAudio(
            on_step=on_step,
            ambient=ambient,
        )

    def _generate_narrative(self, grammar: TileGrammar) -> GlyphNarrative:
        """Generate narrative text from grammar."""
        # Build description
        desc_parts = []

        if grammar.age_state > 0:
            desc_parts.append(["", "Worn", "Ancient"][grammar.age_state])

        if grammar.damage_state > 0:
            desc_parts.append(["", "scratched", "cracked", "broken"][grammar.damage_state])

        if grammar.moisture_state > 0:
            desc_parts.append("damp")

        category_desc = {
            "wall": "stone wall",
            "floor": "stone floor",
            "ground": "ground",
            "door": "door",
            "fluid": "water",
            "prop": "object",
        }

        desc_parts.append(category_desc.get(grammar.category, grammar.category))

        description = " ".join(filter(None, desc_parts)).capitalize() + "."

        # Tone
        tone = "neutral"
        if grammar.category in ["lava"]:
            tone = "dangerous"
        if grammar.age_state > 1:
            tone = "ancient"
        if grammar.damage_state > 1:
            tone = "decay"

        return GlyphNarrative(
            description=description,
            tone=tone,
            keywords=[grammar.category, grammar.subcategory] if grammar.subcategory else [grammar.category],
        )

    def _generate_llm(self, grammar: TileGrammar) -> GlyphLLM:
        """Generate LLM metadata from grammar."""
        # Summary
        summary_parts = []
        if grammar.damage_state > 0:
            summary_parts.append(["", "scratched", "cracked", "broken"][grammar.damage_state])
        if grammar.moisture_state > 0:
            summary_parts.append("wet")
        summary_parts.append(grammar.category)
        if grammar.subcategory:
            summary_parts.append(grammar.subcategory)

        summary = " ".join(summary_parts)

        # Threat level
        threat = 0.0
        if grammar.category in ["lava"]:
            threat = 1.0
        elif grammar.category in ["fluid"]:
            threat = 0.2
        elif grammar.damage_state > 1:
            threat = 0.1

        # Interest level
        interest = 0.1
        if grammar.category in ["door", "prop"]:
            interest = 0.5
        if grammar.subcategory in ["chest", "altar", "crystal"]:
            interest = 0.8

        return GlyphLLM(
            summary=summary,
            threat=threat,
            interest=interest,
            contexts=grammar.biome_affinity,
        )

    def compile_batch(
        self,
        specs: list[TileSpec],
        output_dir: Optional[str] = None,
    ) -> CompilationBatch:
        """
        Compile multiple tile specs to glyphs.

        Args:
            specs: List of tile specifications
            output_dir: Optional output directory

        Returns:
            CompilationBatch with all outputs
        """
        batch = CompilationBatch()

        for spec in specs:
            grammars = spec.expand_grammars()
            for grammar in grammars:
                try:
                    output = self.compile_tile(grammar)
                    batch.outputs.append(output)
                except Exception as e:
                    batch.errors.append(f"Failed to compile {grammar.to_generation_id()}: {str(e)}")

        # Generate registry JSON
        batch.registry_json = self.export_registry_json()

        return batch

    def export_registry_json(self) -> str:
        """Export compiled glyphs as registry JSON."""
        glyphs_data = []

        for output in self._compiled.values():
            glyph = output.glyph
            glyphs_data.append(glyph.model_dump())

        registry = {
            "version": "1.0.0",
            "description": "Auto-generated glyph registry from tile compiler",
            "glyphs": glyphs_data,
        }

        return json.dumps(registry, indent=2)

    def get_allocation_stats(self) -> dict:
        """Get codepoint allocation statistics."""
        return self.allocator.get_stats()

    def get_compiled_count(self) -> int:
        """Get number of compiled glyphs."""
        return len(self._compiled)
