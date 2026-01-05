"""
Legend Compression utilities for efficient LLM context.

Provides compressed glyph legends and context-efficient
representations for LLM prompts.
"""

from typing import Optional

from .models import Glyph, GlyphCategory
from .registry import GlyphRegistry


class LegendCompressor:
    """
    Compresses glyph information for efficient LLM context.

    Instead of full registry, provides:
    - Compact codepoint -> summary mappings
    - Category rules
    - Context-specific subsets
    """

    def __init__(self, registry: GlyphRegistry):
        self.registry = registry

    def compress_legend(
        self,
        glyphs: Optional[list[str]] = None,
        include_categories: Optional[list[GlyphCategory]] = None,
        max_entries: int = 100
    ) -> dict[str, str]:
        """
        Create compressed legend mapping codepoints to summaries.

        Args:
            glyphs: Specific glyph IDs to include (None = all)
            include_categories: Categories to include (None = all)
            max_entries: Maximum entries to return

        Returns:
            Dict mapping codepoints to LLM summaries
        """
        self.registry.initialize()
        legend = {}

        if glyphs:
            # Specific glyphs requested
            for glyph_id in glyphs:
                glyph = self.registry.get(glyph_id)
                if glyph:
                    legend[glyph.codepoint] = glyph.llm.summary or glyph.name
        else:
            # Get by categories or all
            source_glyphs = []
            if include_categories:
                for cat in include_categories:
                    source_glyphs.extend(self.registry.get_by_category(cat))
            else:
                source_glyphs = self.registry.all_glyphs()

            for glyph in source_glyphs[:max_entries]:
                legend[glyph.codepoint] = glyph.llm.summary or glyph.name

        return legend

    def compress_char_legend(
        self,
        glyphs: Optional[list[str]] = None,
        include_categories: Optional[list[GlyphCategory]] = None,
        max_entries: int = 100
    ) -> dict[str, str]:
        """
        Create compressed legend mapping characters to summaries.

        For legacy/fallback rendering compatibility.
        """
        self.registry.initialize()
        legend = {}

        if glyphs:
            for glyph_id in glyphs:
                glyph = self.registry.get(glyph_id)
                if glyph:
                    legend[glyph.char] = glyph.llm.summary or glyph.name
        else:
            source_glyphs = []
            if include_categories:
                for cat in include_categories:
                    source_glyphs.extend(self.registry.get_by_category(cat))
            else:
                source_glyphs = self.registry.all_glyphs()

            for glyph in source_glyphs[:max_entries]:
                legend[glyph.char] = glyph.llm.summary or glyph.name

        return legend

    def get_category_rules(self) -> str:
        """
        Generate category rules text for LLM context.

        Returns:
            Human-readable category rules
        """
        rules = """Glyph Category Rules:
- E000-E0FF: Empty/void spaces - always passable
- E100-E1FF: Ground/floors - typically passable terrain
- E200-E2FF: Walls/structures - block movement and light
- E300-E3FF: Doors/windows - may be passable when open
- E400-E4FF: Fluids - may slow movement or cause damage
- E500-E5FF: Props/objects - static interactive objects
- E600-E6FF: Items - collectible objects
- E700-E7FF: Entities - creatures, NPCs, player
- E800-E8FF: Effects - particles, spells, environmental
- E900-E9FF: UI elements - highlights, selection
- EA00-EAFF: Overlays - lighting, damage states
- EB00-EBFF: Animation frames - animated glyph sequences"""
        return rules

    def get_biome_legend(self, biome: str, max_entries: int = 50) -> dict[str, str]:
        """
        Get legend optimized for a specific biome.

        Args:
            biome: Biome name
            max_entries: Maximum entries

        Returns:
            Dict mapping characters to summaries
        """
        self.registry.initialize()
        legend = {}

        for glyph in self.registry.all_glyphs()[:max_entries]:
            # Get biome-specific variant if available
            variant = glyph.get_for_biome(biome)
            legend[variant.char] = variant.llm.summary or variant.name

        return legend

    def format_legend_for_prompt(
        self,
        legend: dict[str, str],
        format_type: str = "compact"
    ) -> str:
        """
        Format legend dictionary for LLM prompt inclusion.

        Args:
            legend: Legend dictionary
            format_type: "compact", "verbose", or "json"

        Returns:
            Formatted string for prompt
        """
        if format_type == "json":
            import json
            return json.dumps(legend, indent=2)

        if format_type == "verbose":
            lines = ["Glyph Legend:"]
            for key, value in legend.items():
                lines.append(f"  {key}: {value}")
            return "\n".join(lines)

        # Compact format
        items = [f"{k}={v}" for k, v in legend.items()]
        return "Legend: " + ", ".join(items)

    def get_threat_glyphs(self, min_threat: float = 0.5) -> list[str]:
        """Get glyph IDs with threat level above threshold."""
        self.registry.initialize()
        return [
            g.id for g in self.registry.all_glyphs()
            if g.llm.threat >= min_threat
        ]

    def get_interesting_glyphs(self, min_interest: float = 0.5) -> list[str]:
        """Get glyph IDs with interest level above threshold."""
        self.registry.initialize()
        return [
            g.id for g in self.registry.all_glyphs()
            if g.llm.interest >= min_interest
        ]

    def generate_room_context(
        self,
        map_lines: list[str],
        biome: str,
        include_legend: bool = True
    ) -> str:
        """
        Generate complete room context for LLM.

        Args:
            map_lines: Room map as character strings
            biome: Current biome
            include_legend: Include glyph legend

        Returns:
            Formatted context string
        """
        self.registry.initialize()

        # Collect unique characters in map
        unique_chars = set()
        for line in map_lines:
            unique_chars.update(line)

        # Build legend for just the used characters
        legend = {}
        for char in unique_chars:
            glyph = self.registry.get_by_char(char)
            if glyph:
                variant = glyph.get_for_biome(biome)
                legend[char] = variant.llm.summary or variant.name

        context_parts = []

        if include_legend:
            context_parts.append(self.format_legend_for_prompt(legend, "compact"))

        # Add map
        context_parts.append("Map:")
        context_parts.extend(map_lines)

        # Add biome info
        context_parts.append(f"Biome: {biome}")

        return "\n".join(context_parts)

    def create_patch_format_example(self) -> str:
        """Generate example of LLM patch format."""
        return """{
  "patches": [
    {"op": "replace", "x": 5, "y": 3, "layer": 1, "glyph": "door.wood.open"},
    {"op": "add", "x": 7, "y": 4, "layer": 2, "glyph": "entity.npc.merchant"},
    {"op": "remove", "x": 2, "y": 6, "layer": 3, "glyph": "effect.fire"}
  ]
}"""

    def get_llm_constraints(self) -> str:
        """Get LLM constraints text for prompts."""
        return """LLM Glyph Constraints:
- Never invent new glyphs - only use registered glyph IDs
- Emit glyph IDs or codepoints, not arbitrary characters
- Reason in symbols, not pixels
- Use patch format for world modifications
- Respect glyph physics (walkable, blocks_movement, etc.)
- Consider glyph threat/interest levels for placement"""
