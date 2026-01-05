"""
Glyph models for the GASR system.

Defines the data structures for glyphs, their properties,
and related metadata.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GlyphCategory(str, Enum):
    """Glyph category aligned with codepoint bands."""
    EMPTY = "empty"           # E000-E0FF: Empty / Null / Air
    GROUND = "ground"         # E100-E1FF: Ground / Floor
    WALL = "wall"             # E200-E2FF: Walls / Structures
    DOOR = "door"             # E300-E3FF: Doors / Windows
    FLUID = "fluid"           # E400-E4FF: Fluids
    PROP = "prop"             # E500-E5FF: Props / Objects
    ITEM = "item"             # E600-E6FF: Items
    ENTITY = "entity"         # E700-E7FF: Entities / Creatures
    EFFECT = "effect"         # E800-E8FF: Effects / Particles
    UI = "ui"                 # E900-E9FF: UI / Chrome
    OVERLAY = "overlay"       # EA00-EAFF: Lighting / Overlays
    ANIMATION = "animation"   # EB00-EBFF: Animation Frames


# Codepoint band ranges for each category
CODEPOINT_BANDS = {
    GlyphCategory.EMPTY: (0xE000, 0xE0FF),
    GlyphCategory.GROUND: (0xE100, 0xE1FF),
    GlyphCategory.WALL: (0xE200, 0xE2FF),
    GlyphCategory.DOOR: (0xE300, 0xE3FF),
    GlyphCategory.FLUID: (0xE400, 0xE4FF),
    GlyphCategory.PROP: (0xE500, 0xE5FF),
    GlyphCategory.ITEM: (0xE600, 0xE6FF),
    GlyphCategory.ENTITY: (0xE700, 0xE7FF),
    GlyphCategory.EFFECT: (0xE800, 0xE8FF),
    GlyphCategory.UI: (0xE900, 0xE9FF),
    GlyphCategory.OVERLAY: (0xEA00, 0xEAFF),
    GlyphCategory.ANIMATION: (0xEB00, 0xEBFF),
}


class GlyphLayer(int, Enum):
    """Rendering layers (SNES-style)."""
    BACKGROUND = 0    # Background terrain
    STRUCTURE = 1     # Structures (walls, doors)
    ENTITY = 2        # Entities (player, enemies, NPCs)
    EFFECT = 3        # Effects / particles
    LIGHTING = 4      # Lighting overlays
    UI = 5            # UI elements


class GlyphPhysics(BaseModel):
    """Physical properties of a glyph."""
    walkable: bool = True
    blocks_movement: bool = False
    blocks_light: bool = False
    blocks_projectiles: bool = False
    climbable: bool = False
    swimmable: bool = False
    movement_penalty: float = Field(default=0.0, ge=0.0, le=1.0)
    damage_on_enter: int = 0
    damage_type: Optional[str] = None


class GlyphVisual(BaseModel):
    """Visual properties of a glyph."""
    layer: GlyphLayer = GlyphLayer.BACKGROUND
    connectivity: str = Field(default="none", description="none, auto, or manual")
    palette: Optional[str] = None
    glow: bool = False
    glow_radius: int = 0
    glow_color: Optional[str] = None
    animated: bool = False
    animation_id: Optional[str] = None
    z_index: int = 0


class GlyphAudio(BaseModel):
    """Audio properties tied to glyph interactions."""
    on_step: Optional[str] = None
    on_enter: Optional[str] = None
    on_exit: Optional[str] = None
    on_interact: Optional[str] = None
    on_impact: Optional[str] = None
    ambient: Optional[str] = None
    ambient_volume: float = Field(default=1.0, ge=0.0, le=1.0)


class GlyphNarrative(BaseModel):
    """Narrative/descriptive properties for storytelling."""
    description: str = ""
    examine_text: Optional[str] = None
    tone: str = "neutral"
    keywords: list[str] = Field(default_factory=list)
    lore_category: Optional[str] = None


class GlyphLLM(BaseModel):
    """LLM-specific metadata for AI reasoning."""
    summary: str = ""
    threat: float = Field(default=0.0, ge=0.0, le=1.0)
    interest: float = Field(default=0.0, ge=0.0, le=1.0)
    utility: float = Field(default=0.0, ge=0.0, le=1.0)
    rarity: float = Field(default=0.5, ge=0.0, le=1.0)
    synonyms: list[str] = Field(default_factory=list)
    contexts: list[str] = Field(default_factory=list)


class Glyph(BaseModel):
    """
    Complete glyph definition.

    Each glyph has a stable ID independent of codepoint.
    Codepoints may change during development; IDs must not.
    """
    id: str = Field(description="Stable glyph identifier (e.g., 'wall.stone.corner.ne')")
    codepoint: str = Field(description="Unicode codepoint (e.g., 'U+E213')")
    char: str = Field(description="Fallback display character for legacy rendering")
    name: str = Field(description="Human-readable name")
    category: GlyphCategory
    tags: list[str] = Field(default_factory=list)
    variant: Optional[str] = None

    # Component properties
    physics: GlyphPhysics = Field(default_factory=GlyphPhysics)
    visual: GlyphVisual = Field(default_factory=GlyphVisual)
    audio: GlyphAudio = Field(default_factory=GlyphAudio)
    narrative: GlyphNarrative = Field(default_factory=GlyphNarrative)
    llm: GlyphLLM = Field(default_factory=GlyphLLM)

    # Biome-specific overrides
    biome_variants: dict[str, dict] = Field(default_factory=dict)

    @property
    def codepoint_int(self) -> int:
        """Get codepoint as integer."""
        return int(self.codepoint.replace("U+", ""), 16)

    @property
    def unicode_char(self) -> str:
        """Get the Unicode character for this glyph."""
        return chr(self.codepoint_int)

    def get_for_biome(self, biome: str) -> "Glyph":
        """Get biome-specific variant of this glyph."""
        if biome not in self.biome_variants:
            return self

        # Create copy with biome overrides
        data = self.model_dump()
        overrides = self.biome_variants[biome]

        # Deep merge overrides
        for key, value in overrides.items():
            if key in data and isinstance(data[key], dict) and isinstance(value, dict):
                data[key].update(value)
            else:
                data[key] = value

        return Glyph(**data)

    class Config:
        use_enum_values = True


class Animation(BaseModel):
    """Animation definition for animated glyphs."""
    id: str = Field(description="Animation identifier")
    frames: list[str] = Field(description="List of codepoints for frames")
    rate_ms: int = Field(default=100, description="Frame duration in milliseconds")
    loop: bool = True
    ping_pong: bool = False
    on_complete: Optional[str] = None  # Event to trigger on completion

    @property
    def frame_chars(self) -> list[str]:
        """Get Unicode characters for all frames."""
        return [chr(int(cp.replace("U+", ""), 16)) for cp in self.frames]


class OverlayType(str, Enum):
    """Types of overlay glyphs."""
    LIGHT = "light"           # EA00-EA3F: Light levels
    DAMAGE = "damage"         # EA40-EA7F: Damage states
    STATUS = "status"         # EA80-EABF: Status effects
    HIGHLIGHT = "highlight"   # EAC0-EAFF: Selection/highlight


OVERLAY_BANDS = {
    OverlayType.LIGHT: (0xEA00, 0xEA3F),
    OverlayType.DAMAGE: (0xEA40, 0xEA7F),
    OverlayType.STATUS: (0xEA80, 0xEABF),
    OverlayType.HIGHLIGHT: (0xEAC0, 0xEAFF),
}


class GlyphPatch(BaseModel):
    """LLM world patch format for modifying glyphs."""
    op: str = Field(description="Operation: replace, add, remove")
    x: int
    y: int
    layer: GlyphLayer = GlyphLayer.BACKGROUND
    glyph: str = Field(description="Glyph ID to place")

    class Config:
        use_enum_values = True


class GlyphDiff(BaseModel):
    """Batch of glyph patches for efficient updates."""
    patches: list[GlyphPatch]
    timestamp: Optional[str] = None
    source: str = "system"  # system, player, llm
