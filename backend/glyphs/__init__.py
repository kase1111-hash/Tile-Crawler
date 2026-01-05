"""
Glyph Addressing & Semantic Registry (GASR) System

This package implements a font-driven, tile-based rendering system where
every character cell is a graphical tile with semantic meaning.

Key concepts:
- Font = Tileset ROM
- Text Grid = VRAM
- Glyph = Tile + State + Meaning
- LLM-native (symbolic, diffable, deterministic)
"""

from .models import (
    Glyph,
    GlyphPhysics,
    GlyphVisual,
    GlyphAudio,
    GlyphNarrative,
    GlyphLLM,
    Animation,
    GlyphLayer,
    GlyphCategory,
)
from .registry import (
    GlyphRegistry,
    get_glyph_registry,
    reset_glyph_registry,
)
from .layers import LayerManager, LayerType
from .legends import LegendCompressor
from .engine import GlyphEngine, AnimationState

__all__ = [
    # Models
    "Glyph",
    "GlyphPhysics",
    "GlyphVisual",
    "GlyphAudio",
    "GlyphNarrative",
    "GlyphLLM",
    "Animation",
    "GlyphLayer",
    "GlyphCategory",
    # Registry
    "GlyphRegistry",
    "get_glyph_registry",
    "reset_glyph_registry",
    # Layers
    "LayerManager",
    "LayerType",
    # Legends
    "LegendCompressor",
    # Engine
    "GlyphEngine",
    "AnimationState",
]
