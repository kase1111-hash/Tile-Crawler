"""
Procedural Glyph Foundry - AI Tile Generation Pipeline

This package implements a constrained AI tile generation system where:
- AI creates parametrically constrained micro-tiles
- Tiles obey grid, adjacency, palette, and semantic rules
- Wave Function Collapse compatible edge signatures
- Batch generation via combinatorial parameters

Core principle: AI doesn't create "art" - it creates tiles that obey rules.
"""

from .grammar import (
    TileGrammar,
    EdgeSignature,
    EdgeCode,
    TileStyle,
    TileSpec,
)
from .palettes import (
    Palette,
    PaletteManager,
    get_palette_manager,
)
from .edges import (
    EdgeSystem,
    EdgeCompatibility,
    get_edge_system,
)
from .generator import (
    TileGenerator,
    GenerationConfig,
    GenerationResult,
)
from .validator import (
    TileValidator,
    ValidationResult,
    ValidationError,
)
from .compiler import (
    TileCompiler,
    GlyphOutput,
)
from .font_generator import (
    FontGenerator,
    TileRasterizer,
    generate_tile_font,
    export_tile_sprites,
)

__all__ = [
    # Grammar
    "TileGrammar",
    "EdgeSignature",
    "EdgeCode",
    "TileStyle",
    "TileSpec",
    # Palettes
    "Palette",
    "PaletteManager",
    "get_palette_manager",
    # Edges
    "EdgeSystem",
    "EdgeCompatibility",
    "get_edge_system",
    # Generator
    "TileGenerator",
    "GenerationConfig",
    "GenerationResult",
    # Validator
    "TileValidator",
    "ValidationResult",
    "ValidationError",
    # Compiler
    "TileCompiler",
    "GlyphOutput",
    # Font Generation
    "FontGenerator",
    "TileRasterizer",
    "generate_tile_font",
    "export_tile_sprites",
]
