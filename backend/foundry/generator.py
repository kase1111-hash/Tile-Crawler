"""
Tile Generator - Constrained AI tile generation.

Generates parametrically constrained micro-tiles using AI.
The prompt IS the tile grammar, not prose.
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel, Field

from .grammar import TileGrammar, TileSpec, TileStyle, TileSize, EdgeCode
from .palettes import Palette, PaletteManager, get_palette_manager


class GenerationStatus(str, Enum):
    """Status of a generation request."""
    PENDING = "pending"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETE = "complete"
    FAILED = "failed"
    REJECTED = "rejected"  # Failed validation


@dataclass
class GenerationConfig:
    """Configuration for tile generation."""
    # Resolution
    target_size: TileSize = TileSize.SMALL
    scale_factor: int = 1  # For upscaling

    # Quality
    max_retries: int = 3
    validation_strict: bool = True

    # Style enforcement
    force_pixel_grid: bool = True
    force_palette: bool = True
    allow_anti_aliasing: bool = False
    allow_gradients: bool = False

    # Output
    output_format: str = "png"
    include_metadata: bool = True


class GenerationResult(BaseModel):
    """Result of a tile generation."""
    tile_id: str
    grammar: TileGrammar
    status: GenerationStatus
    image_data: Optional[bytes] = None
    image_path: Optional[str] = None
    validation_errors: list[str] = Field(default_factory=list)
    retries: int = 0
    generation_prompt: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class TileGenerator:
    """
    Generates tiles from grammar specifications.

    Uses constrained prompts to ensure consistent output.
    """

    def __init__(
        self,
        config: Optional[GenerationConfig] = None,
        palette_manager: Optional[PaletteManager] = None,
    ):
        self.config = config or GenerationConfig()
        self.palettes = palette_manager or get_palette_manager()
        self._pending: list[GenerationResult] = []
        self._completed: list[GenerationResult] = []

    def build_prompt(self, grammar: TileGrammar) -> str:
        """
        Build generation prompt from grammar.

        The grammar IS the prompt - we translate it to
        natural language constraints.
        """
        # Get palette
        palette = self.palettes.get(grammar.palette)
        palette_desc = self._describe_palette(palette) if palette else "grayscale 4-color"

        # Parse size
        size = grammar.size if isinstance(grammar.size, str) else grammar.size.value
        width, height = size.split("x")

        # Build edge descriptions
        edge_desc = self._describe_edges(grammar.edges)

        # Build style constraints
        style_desc = self._describe_styles(grammar.styles)

        # Build state modifiers
        state_desc = self._describe_states(grammar)

        # Construct prompt
        prompt_parts = [
            f"Generate a {width}×{height} pixel tile.",
            f"Category: {grammar.category} ({grammar.subcategory or 'base'}).",
            f"Center content: {grammar.center}.",
            f"Palette: {palette_desc}.",
            f"Edge requirements: {edge_desc}.",
            f"Style: {style_desc}.",
        ]

        if state_desc:
            prompt_parts.append(f"State modifiers: {state_desc}.")

        # Add strict constraints
        prompt_parts.extend([
            "CONSTRAINTS:",
            "- Exact pixel resolution, no anti-aliasing",
            "- Only use specified palette colors",
            "- No gradients or smooth shading",
            "- No perspective - flat orthographic view",
            "- Edge pixels must match declared edge codes",
            "- Center texture must be consistent",
        ])

        if grammar.tags:
            prompt_parts.append(f"Tags for reference: {', '.join(grammar.tags)}")

        return "\n".join(prompt_parts)

    def _describe_palette(self, palette: Palette) -> str:
        """Describe palette for prompt."""
        color_hex = ", ".join(palette.to_hex_list()[:4])
        return f"{palette.name} ({palette.color_count} colors: {color_hex})"

    def _describe_edges(self, edges) -> str:
        """Describe edge requirements."""
        descriptions = {
            EdgeCode.EMPTY: "open/empty",
            EdgeCode.SOLID: "solid wall",
            EdgeCode.FLOOR: "floor level",
            EdgeCode.WATER: "water edge",
            EdgeCode.CLIFF: "cliff/drop",
            EdgeCode.DOOR_FRAME: "door frame",
            EdgeCode.GRASS: "grass edge",
            EdgeCode.SAND: "sand edge",
            EdgeCode.STONE: "stone texture",
            EdgeCode.WOOD: "wood texture",
        }

        parts = []
        for direction, code in [
            ("North", edges.north),
            ("East", edges.east),
            ("South", edges.south),
            ("West", edges.west),
        ]:
            # Handle both EdgeCode and int
            if isinstance(code, int):
                code = EdgeCode(code)
            desc = descriptions.get(code, str(code))
            parts.append(f"{direction}={desc}")

        return ", ".join(parts)

    def _describe_styles(self, styles: list) -> str:
        """Describe style requirements."""
        style_map = {
            TileStyle.PIXEL: "hard pixel edges",
            TileStyle.COMIC: "outlined comic style",
            TileStyle.HIGH_CONTRAST: "high contrast light/dark",
            TileStyle.DITHERED: "dithered shading",
            TileStyle.FLAT: "flat solid colors",
            TileStyle.TEXTURED: "subtle texture variation",
            "pixel": "hard pixel edges",
            "comic": "outlined comic style",
            "high_contrast": "high contrast light/dark",
            "dithered": "dithered shading",
            "flat": "flat solid colors",
            "textured": "subtle texture variation",
        }

        descriptions = [style_map.get(s, str(s)) for s in styles]
        return ", ".join(descriptions)

    def _describe_states(self, grammar: TileGrammar) -> str:
        """Describe state modifiers."""
        parts = []

        if grammar.damage_state > 0:
            damage_desc = ["pristine", "scratched", "cracked", "broken"][grammar.damage_state]
            parts.append(f"damage={damage_desc}")

        if grammar.lighting_state != 1:
            light_desc = ["shadowed", "normal", "highlighted"][grammar.lighting_state]
            parts.append(f"lighting={light_desc}")

        if grammar.moisture_state > 0:
            parts.append("wet/damp")

        if grammar.age_state > 0:
            age_desc = ["new", "worn", "ancient"][grammar.age_state]
            parts.append(f"age={age_desc}")

        return ", ".join(parts) if parts else ""

    def generate_tile(
        self,
        grammar: TileGrammar,
        dry_run: bool = False
    ) -> GenerationResult:
        """
        Generate a single tile from grammar.

        Args:
            grammar: Tile grammar specification
            dry_run: If True, only generate prompt without actual generation

        Returns:
            GenerationResult with status and data
        """
        tile_id = grammar.to_generation_id()
        prompt = self.build_prompt(grammar)

        result = GenerationResult(
            tile_id=tile_id,
            grammar=grammar,
            status=GenerationStatus.PENDING,
            generation_prompt=prompt,
        )

        if dry_run:
            result.status = GenerationStatus.COMPLETE
            return result

        # In a real implementation, this would call an image generation API
        # For now, we mark it as pending for external processing
        result.status = GenerationStatus.PENDING
        self._pending.append(result)

        return result

    def generate_batch(
        self,
        spec: TileSpec,
        dry_run: bool = False
    ) -> list[GenerationResult]:
        """
        Generate all variants from a tile spec.

        Args:
            spec: Tile specification with variant dimensions
            dry_run: If True, only generate prompts

        Returns:
            List of GenerationResults
        """
        results = []
        grammars = spec.expand_grammars()

        for grammar in grammars:
            result = self.generate_tile(grammar, dry_run=dry_run)
            results.append(result)

        return results

    def calculate_batch_size(self, specs: list[TileSpec]) -> int:
        """Calculate total tiles that would be generated."""
        return sum(spec.total_variants() for spec in specs)

    def generate_combinatorial(
        self,
        bases: list[str],
        edge_variants: int = 4,
        damage_states: int = 4,
        lighting_states: int = 3,
        moisture_states: int = 2,
        dry_run: bool = True
    ) -> dict[str, int]:
        """
        Calculate combinatorial generation statistics.

        This shows how batch generation scales.
        """
        total = len(bases) * edge_variants * damage_states * lighting_states * moisture_states

        return {
            "base_tiles": len(bases),
            "edge_variants": edge_variants,
            "damage_states": damage_states,
            "lighting_states": lighting_states,
            "moisture_states": moisture_states,
            "total_tiles": total,
            "formula": f"{len(bases)} × {edge_variants} × {damage_states} × {lighting_states} × {moisture_states}",
        }

    def get_pending(self) -> list[GenerationResult]:
        """Get pending generation requests."""
        return self._pending

    def get_completed(self) -> list[GenerationResult]:
        """Get completed generations."""
        return self._completed

    def mark_complete(
        self,
        tile_id: str,
        image_data: Optional[bytes] = None,
        image_path: Optional[str] = None,
        validation_errors: Optional[list[str]] = None
    ) -> Optional[GenerationResult]:
        """
        Mark a pending generation as complete.

        Called after external image generation.
        """
        for result in self._pending:
            if result.tile_id == tile_id:
                self._pending.remove(result)

                if validation_errors:
                    result.validation_errors = validation_errors
                    result.status = GenerationStatus.REJECTED
                else:
                    result.image_data = image_data
                    result.image_path = image_path
                    result.status = GenerationStatus.COMPLETE

                self._completed.append(result)
                return result

        return None


# Prompt templates for common tile types
PROMPT_TEMPLATES = {
    "wall_solid": """
Generate an 8×8 pixel tile for a solid wall.
Use only these 4 colors: {palette}
All edges are solid (connect to other walls).
Style: pixel art, high contrast, no anti-aliasing.
Texture: stone blocks with subtle variation.
""",

    "floor_basic": """
Generate an 8×8 pixel tile for a floor.
Use only these 4 colors: {palette}
All edges are floor-level (connect to other floors).
Style: pixel art, flat with subtle texture.
Pattern: stone tiles or flagstones.
""",

    "wall_corner": """
Generate an 8×8 pixel tile for a wall corner ({corner_type}).
Use only these 4 colors: {palette}
Solid edges: {solid_edges}
Open edges: {open_edges}
Style: pixel art, shows depth at corner.
""",

    "door_frame": """
Generate an 8×8 pixel tile for a door frame.
Use only these 4 colors: {palette}
Top/bottom: door frame (opening)
Left/right: solid wall connection
Style: pixel art, wooden frame visible.
""",

    "water_tile": """
Generate an 8×8 pixel tile for water.
Use only these 4 colors: {palette}
All edges: water (connect to other water).
Style: pixel art with dithering for animation frames.
Pattern: rippled surface.
""",

    "transition_floor_grass": """
Generate an 8×8 pixel tile for floor-to-grass transition.
Use colors from both palettes: {palette1}, {palette2}
North/East: grass edge
South/West: floor edge
Style: pixel art, smooth transition.
""",
}
