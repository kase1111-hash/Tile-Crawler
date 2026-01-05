"""
Tile Grammar - Structured tile definitions for generation.

The grammar defines what a tile IS, not what it looks like.
This is the prompt, not prose.
"""

from enum import IntEnum, Enum
from typing import Optional
from pydantic import BaseModel, Field


class EdgeCode(IntEnum):
    """
    Edge compatibility codes for tile meshing.

    Each tile declares its edge signatures. Tiles can only
    connect when their adjacent edges are compatible.
    """
    EMPTY = 0          # No content, open space
    SOLID = 1          # Solid wall, impassable
    FLOOR = 2          # Floor/ground level
    WATER = 3          # Water edge
    CLIFF = 4          # Cliff/elevation change
    DOOR_FRAME = 5     # Door frame opening
    WINDOW = 6         # Window opening
    FENCE = 7          # Fence/railing
    BRIDGE = 8         # Bridge connection
    LAVA = 9           # Lava edge
    PIT = 10           # Pit/hole edge
    GRASS = 11         # Grass edge
    SAND = 12          # Sand edge
    STONE = 13         # Stone texture edge
    WOOD = 14          # Wood texture edge
    METAL = 15         # Metal texture edge


# Edge compatibility matrix - which edges can connect
EDGE_COMPATIBILITY = {
    EdgeCode.EMPTY: {EdgeCode.EMPTY, EdgeCode.FLOOR, EdgeCode.GRASS, EdgeCode.SAND},
    EdgeCode.SOLID: {EdgeCode.SOLID, EdgeCode.STONE, EdgeCode.WOOD, EdgeCode.METAL},
    EdgeCode.FLOOR: {EdgeCode.FLOOR, EdgeCode.EMPTY, EdgeCode.DOOR_FRAME, EdgeCode.GRASS},
    EdgeCode.WATER: {EdgeCode.WATER, EdgeCode.SAND, EdgeCode.BRIDGE},
    EdgeCode.CLIFF: {EdgeCode.CLIFF, EdgeCode.STONE, EdgeCode.EMPTY},
    EdgeCode.DOOR_FRAME: {EdgeCode.DOOR_FRAME, EdgeCode.FLOOR, EdgeCode.SOLID},
    EdgeCode.WINDOW: {EdgeCode.WINDOW, EdgeCode.SOLID},
    EdgeCode.FENCE: {EdgeCode.FENCE, EdgeCode.FLOOR, EdgeCode.GRASS},
    EdgeCode.BRIDGE: {EdgeCode.BRIDGE, EdgeCode.WATER, EdgeCode.FLOOR},
    EdgeCode.LAVA: {EdgeCode.LAVA, EdgeCode.STONE},
    EdgeCode.PIT: {EdgeCode.PIT, EdgeCode.FLOOR, EdgeCode.STONE},
    EdgeCode.GRASS: {EdgeCode.GRASS, EdgeCode.FLOOR, EdgeCode.EMPTY, EdgeCode.SAND},
    EdgeCode.SAND: {EdgeCode.SAND, EdgeCode.WATER, EdgeCode.GRASS, EdgeCode.EMPTY},
    EdgeCode.STONE: {EdgeCode.STONE, EdgeCode.SOLID, EdgeCode.CLIFF, EdgeCode.LAVA},
    EdgeCode.WOOD: {EdgeCode.WOOD, EdgeCode.SOLID, EdgeCode.FLOOR},
    EdgeCode.METAL: {EdgeCode.METAL, EdgeCode.SOLID},
}


class TileStyle(str, Enum):
    """Visual style constraints for generation."""
    PIXEL = "pixel"              # Hard pixel edges
    COMIC = "comic"              # Outlined comic style
    HIGH_CONTRAST = "high_contrast"  # Strong light/dark
    DITHERED = "dithered"        # Dithering patterns
    FLAT = "flat"                # Flat colors, no shading
    TEXTURED = "textured"        # Subtle texture variation


class TileSize(str, Enum):
    """Standard tile sizes."""
    TINY = "4x4"
    SMALL = "8x8"
    MEDIUM = "16x16"
    LARGE = "24x24"
    XLARGE = "32x32"


class EdgeSignature(BaseModel):
    """Edge signatures for a tile (NESW)."""
    north: EdgeCode = EdgeCode.EMPTY
    east: EdgeCode = EdgeCode.EMPTY
    south: EdgeCode = EdgeCode.EMPTY
    west: EdgeCode = EdgeCode.EMPTY

    def rotated(self, times: int = 1) -> "EdgeSignature":
        """Rotate signature clockwise by 90 degrees * times."""
        n, e, s, w = self.north, self.east, self.south, self.west
        for _ in range(times % 4):
            n, e, s, w = w, n, e, s
        return EdgeSignature(north=n, east=e, south=s, west=w)

    def flipped_horizontal(self) -> "EdgeSignature":
        """Flip signature horizontally."""
        return EdgeSignature(
            north=self.north,
            east=self.west,
            south=self.south,
            west=self.east
        )

    def flipped_vertical(self) -> "EdgeSignature":
        """Flip signature vertically."""
        return EdgeSignature(
            north=self.south,
            east=self.east,
            south=self.north,
            west=self.west
        )

    def compatible_with(self, other: "EdgeSignature", direction: str) -> bool:
        """Check if this tile can connect to another in a direction."""
        if direction == "north":
            my_edge, their_edge = self.north, other.south
        elif direction == "south":
            my_edge, their_edge = self.south, other.north
        elif direction == "east":
            my_edge, their_edge = self.east, other.west
        elif direction == "west":
            my_edge, their_edge = self.west, other.east
        else:
            return False

        return their_edge in EDGE_COMPATIBILITY.get(my_edge, set())

    def to_code(self) -> str:
        """Generate compact edge code string."""
        # Handle both EdgeCode enum and int values
        n = self.north if isinstance(self.north, int) else self.north.value
        e = self.east if isinstance(self.east, int) else self.east.value
        s = self.south if isinstance(self.south, int) else self.south.value
        w = self.west if isinstance(self.west, int) else self.west.value
        return f"{n}{e}{s}{w}"

    @classmethod
    def from_code(cls, code: str) -> "EdgeSignature":
        """Parse compact edge code string."""
        if len(code) != 4:
            raise ValueError("Edge code must be 4 digits")
        return cls(
            north=EdgeCode(int(code[0])),
            east=EdgeCode(int(code[1])),
            south=EdgeCode(int(code[2])),
            west=EdgeCode(int(code[3])),
        )

    class Config:
        use_enum_values = True


class TileGrammar(BaseModel):
    """
    Complete tile grammar definition.

    This is THE specification for a tile - everything needed
    to generate, validate, and classify it.
    """
    category: str = Field(description="Semantic category (wall, floor, entity, etc.)")
    subcategory: Optional[str] = Field(default=None, description="Sub-classification")
    size: TileSize = TileSize.SMALL
    palette: str = Field(description="Palette ID to use")
    edges: EdgeSignature = Field(default_factory=EdgeSignature)
    center: str = Field(default="empty", description="Center content type")
    styles: list[TileStyle] = Field(default_factory=lambda: [TileStyle.PIXEL])

    # Visual modifiers
    damage_state: int = Field(default=0, ge=0, le=3, description="Damage level 0-3")
    lighting_state: int = Field(default=1, ge=0, le=2, description="0=dark, 1=normal, 2=bright")
    moisture_state: int = Field(default=0, ge=0, le=1, description="0=dry, 1=wet")
    age_state: int = Field(default=0, ge=0, le=2, description="0=new, 1=worn, 2=ancient")

    # Metadata
    tags: list[str] = Field(default_factory=list)
    biome_affinity: list[str] = Field(default_factory=list)

    def get_variant_count(self) -> int:
        """Calculate total variants for this grammar."""
        return (
            (self.damage_state + 1) *
            (self.lighting_state + 1) *
            (self.moisture_state + 1) *
            (self.age_state + 1)
        )

    def to_generation_id(self) -> str:
        """Generate unique ID for this grammar configuration."""
        parts = [
            self.category,
            self.subcategory or "base",
            self.center,
            self.edges.to_code(),
            f"d{self.damage_state}",
            f"l{self.lighting_state}",
            f"m{self.moisture_state}",
            f"a{self.age_state}",
        ]
        return ".".join(parts)

    class Config:
        use_enum_values = True


class TileSpec(BaseModel):
    """
    Complete tile specification for batch generation.

    Defines a base tile and all its variant dimensions.
    """
    id: str = Field(description="Base tile ID")
    grammar: TileGrammar

    # Variant dimensions - how many of each state to generate
    damage_variants: int = Field(default=1, ge=1, le=4)
    lighting_variants: int = Field(default=1, ge=1, le=3)
    moisture_variants: int = Field(default=1, ge=1, le=2)
    age_variants: int = Field(default=1, ge=1, le=3)

    # Rotation/flip variants
    generate_rotations: bool = False
    generate_flips: bool = False

    def total_variants(self) -> int:
        """Calculate total tiles to generate."""
        base = (
            self.damage_variants *
            self.lighting_variants *
            self.moisture_variants *
            self.age_variants
        )
        if self.generate_rotations:
            base *= 4
        if self.generate_flips:
            base *= 2  # Horizontal flip (vertical is covered by rotations)
        return base

    def expand_grammars(self) -> list[TileGrammar]:
        """Expand spec into all grammar variants."""
        grammars = []

        for damage in range(self.damage_variants):
            for lighting in range(self.lighting_variants):
                for moisture in range(self.moisture_variants):
                    for age in range(self.age_variants):
                        base_grammar = self.grammar.model_copy()
                        base_grammar.damage_state = damage
                        base_grammar.lighting_state = lighting
                        base_grammar.moisture_state = moisture
                        base_grammar.age_state = age

                        if self.generate_rotations:
                            for rot in range(4):
                                rotated = base_grammar.model_copy()
                                rotated.edges = base_grammar.edges.rotated(rot)
                                grammars.append(rotated)
                        else:
                            grammars.append(base_grammar)

        return grammars


# Standard tile grammars for common tiles
STANDARD_GRAMMARS = {
    "wall.solid": TileGrammar(
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
        styles=[TileStyle.PIXEL, TileStyle.TEXTURED],
    ),
    "wall.corner.ne": TileGrammar(
        category="wall",
        subcategory="corner",
        palette="stone_gray",
        edges=EdgeSignature(
            north=EdgeCode.SOLID,
            east=EdgeCode.SOLID,
            south=EdgeCode.EMPTY,
            west=EdgeCode.EMPTY,
        ),
        center="stone",
        styles=[TileStyle.PIXEL],
    ),
    "floor.stone": TileGrammar(
        category="floor",
        subcategory="stone",
        palette="stone_gray",
        edges=EdgeSignature(
            north=EdgeCode.FLOOR,
            east=EdgeCode.FLOOR,
            south=EdgeCode.FLOOR,
            west=EdgeCode.FLOOR,
        ),
        center="stone_floor",
        styles=[TileStyle.PIXEL, TileStyle.FLAT],
    ),
    "floor.grass": TileGrammar(
        category="floor",
        subcategory="grass",
        palette="nature_green",
        edges=EdgeSignature(
            north=EdgeCode.GRASS,
            east=EdgeCode.GRASS,
            south=EdgeCode.GRASS,
            west=EdgeCode.GRASS,
        ),
        center="grass",
        styles=[TileStyle.PIXEL, TileStyle.TEXTURED],
        biome_affinity=["forest", "ruins"],
    ),
    "water.shallow": TileGrammar(
        category="fluid",
        subcategory="water",
        palette="water_blue",
        edges=EdgeSignature(
            north=EdgeCode.WATER,
            east=EdgeCode.WATER,
            south=EdgeCode.WATER,
            west=EdgeCode.WATER,
        ),
        center="water",
        styles=[TileStyle.PIXEL, TileStyle.DITHERED],
    ),
    "door.wood": TileGrammar(
        category="door",
        subcategory="wood",
        palette="wood_brown",
        edges=EdgeSignature(
            north=EdgeCode.DOOR_FRAME,
            east=EdgeCode.SOLID,
            south=EdgeCode.DOOR_FRAME,
            west=EdgeCode.SOLID,
        ),
        center="door",
        styles=[TileStyle.PIXEL],
    ),
}
