"""
Palette System - Color constraints for tile generation.

Palettes lock colors to ensure visual consistency.
No anti-aliasing, no gradients, just indexed colors.
"""

import json
import os
from typing import Optional
from pydantic import BaseModel, Field


class Color(BaseModel):
    """A single color in RGB format."""
    r: int = Field(ge=0, le=255)
    g: int = Field(ge=0, le=255)
    b: int = Field(ge=0, le=255)
    a: int = Field(default=255, ge=0, le=255)
    name: Optional[str] = None

    def to_hex(self) -> str:
        """Convert to hex string."""
        if self.a == 255:
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}{self.a:02x}"

    def to_rgb(self) -> tuple[int, int, int]:
        """Convert to RGB tuple."""
        return (self.r, self.g, self.b)

    def to_rgba(self) -> tuple[int, int, int, int]:
        """Convert to RGBA tuple."""
        return (self.r, self.g, self.b, self.a)

    @classmethod
    def from_hex(cls, hex_str: str, name: Optional[str] = None) -> "Color":
        """Create from hex string."""
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 6:
            r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
            return cls(r=r, g=g, b=b, name=name)
        elif len(hex_str) == 8:
            r, g, b, a = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), int(hex_str[6:8], 16)
            return cls(r=r, g=g, b=b, a=a, name=name)
        raise ValueError(f"Invalid hex color: {hex_str}")

    def lightened(self, factor: float = 0.2) -> "Color":
        """Return lightened version of color."""
        return Color(
            r=min(255, int(self.r + (255 - self.r) * factor)),
            g=min(255, int(self.g + (255 - self.g) * factor)),
            b=min(255, int(self.b + (255 - self.b) * factor)),
            a=self.a,
            name=f"{self.name}_light" if self.name else None,
        )

    def darkened(self, factor: float = 0.2) -> "Color":
        """Return darkened version of color."""
        return Color(
            r=max(0, int(self.r * (1 - factor))),
            g=max(0, int(self.g * (1 - factor))),
            b=max(0, int(self.b * (1 - factor))),
            a=self.a,
            name=f"{self.name}_dark" if self.name else None,
        )


class Palette(BaseModel):
    """
    A color palette for tile generation.

    Palettes typically have 4-16 colors, indexed.
    """
    id: str
    name: str
    colors: list[Color]
    background_index: int = Field(default=0, description="Index of background/transparent color")
    outline_index: Optional[int] = Field(default=None, description="Index of outline color")
    highlight_index: Optional[int] = Field(default=None, description="Index of highlight color")
    shadow_index: Optional[int] = Field(default=None, description="Index of shadow color")

    # Style constraints
    max_colors: int = Field(default=4, description="Maximum colors to use")
    allow_dithering: bool = True
    allow_transparency: bool = True

    # Metadata
    tags: list[str] = Field(default_factory=list)
    biome_affinity: list[str] = Field(default_factory=list)

    @property
    def color_count(self) -> int:
        return len(self.colors)

    def get_color(self, index: int) -> Optional[Color]:
        """Get color by index."""
        if 0 <= index < len(self.colors):
            return self.colors[index]
        return None

    def get_by_name(self, name: str) -> Optional[Color]:
        """Get color by name."""
        for color in self.colors:
            if color.name == name:
                return color
        return None

    def to_hex_list(self) -> list[str]:
        """Get all colors as hex strings."""
        return [c.to_hex() for c in self.colors]

    def derive_lighting_variants(self) -> dict[str, "Palette"]:
        """Generate dark/normal/bright palette variants."""
        dark_colors = [c.darkened(0.3) for c in self.colors]
        bright_colors = [c.lightened(0.2) for c in self.colors]

        return {
            "dark": Palette(
                id=f"{self.id}_dark",
                name=f"{self.name} (Dark)",
                colors=dark_colors,
                background_index=self.background_index,
                max_colors=self.max_colors,
                tags=self.tags + ["dark"],
            ),
            "normal": self,
            "bright": Palette(
                id=f"{self.id}_bright",
                name=f"{self.name} (Bright)",
                colors=bright_colors,
                background_index=self.background_index,
                max_colors=self.max_colors,
                tags=self.tags + ["bright"],
            ),
        }


class PaletteManager:
    """Manages all available palettes."""

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path
        self._palettes: dict[str, Palette] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Load palettes from data file or create defaults."""
        if self._initialized:
            return

        if self.data_path:
            palette_file = os.path.join(self.data_path, "palettes.json")
            if os.path.exists(palette_file):
                self._load_from_file(palette_file)
                self._initialized = True
                return

        # Create default palettes
        self._create_defaults()
        self._initialized = True

    def _load_from_file(self, path: str) -> None:
        """Load palettes from JSON file."""
        with open(path) as f:
            data = json.load(f)

        for palette_data in data.get("palettes", []):
            colors = [
                Color.from_hex(c["hex"], c.get("name"))
                for c in palette_data.get("colors", [])
            ]
            palette = Palette(
                id=palette_data["id"],
                name=palette_data["name"],
                colors=colors,
                background_index=palette_data.get("background_index", 0),
                outline_index=palette_data.get("outline_index"),
                highlight_index=palette_data.get("highlight_index"),
                shadow_index=palette_data.get("shadow_index"),
                max_colors=palette_data.get("max_colors", 4),
                tags=palette_data.get("tags", []),
                biome_affinity=palette_data.get("biome_affinity", []),
            )
            self._palettes[palette.id] = palette

    def _create_defaults(self) -> None:
        """Create default palettes."""
        defaults = [
            # Stone gray (dungeon/cave)
            Palette(
                id="stone_gray",
                name="Stone Gray",
                colors=[
                    Color.from_hex("#1a1a2e", "darkest"),
                    Color.from_hex("#4a4a5e", "dark"),
                    Color.from_hex("#8a8a9e", "mid"),
                    Color.from_hex("#cacade", "light"),
                ],
                background_index=0,
                outline_index=0,
                highlight_index=3,
                shadow_index=1,
                tags=["stone", "neutral"],
                biome_affinity=["dungeon", "cave", "crypt"],
            ),
            # Stone gray 4-color
            Palette(
                id="stone_gray_4",
                name="Stone Gray (4 color)",
                colors=[
                    Color.from_hex("#1a1a2e", "black"),
                    Color.from_hex("#5a5a6e", "dark_gray"),
                    Color.from_hex("#9a9aae", "light_gray"),
                    Color.from_hex("#dadaee", "white"),
                ],
                max_colors=4,
                tags=["stone", "minimal"],
            ),
            # Wood brown
            Palette(
                id="wood_brown",
                name="Wood Brown",
                colors=[
                    Color.from_hex("#2d1b0e", "darkest"),
                    Color.from_hex("#5c3a1d", "dark"),
                    Color.from_hex("#8b5a2b", "mid"),
                    Color.from_hex("#d4a574", "light"),
                ],
                tags=["wood", "warm"],
            ),
            # Nature green
            Palette(
                id="nature_green",
                name="Nature Green",
                colors=[
                    Color.from_hex("#1a2e1a", "darkest"),
                    Color.from_hex("#2d5a2d", "dark"),
                    Color.from_hex("#4a8a4a", "mid"),
                    Color.from_hex("#8aca8a", "light"),
                ],
                tags=["nature", "organic"],
                biome_affinity=["forest"],
            ),
            # Water blue
            Palette(
                id="water_blue",
                name="Water Blue",
                colors=[
                    Color.from_hex("#0a1a2e", "darkest"),
                    Color.from_hex("#1a4a7e", "dark"),
                    Color.from_hex("#3a7abe", "mid"),
                    Color.from_hex("#7abaee", "light"),
                ],
                tags=["water", "fluid"],
            ),
            # Lava orange
            Palette(
                id="lava_orange",
                name="Lava Orange",
                colors=[
                    Color.from_hex("#2e0a0a", "darkest"),
                    Color.from_hex("#8a1a1a", "dark"),
                    Color.from_hex("#da4a1a", "mid"),
                    Color.from_hex("#faba4a", "light"),
                ],
                tags=["lava", "hot"],
                biome_affinity=["volcano"],
            ),
            # Bone white (crypt)
            Palette(
                id="bone_white",
                name="Bone White",
                colors=[
                    Color.from_hex("#2e2a1a", "darkest"),
                    Color.from_hex("#6e5a4a", "dark"),
                    Color.from_hex("#beaa8a", "mid"),
                    Color.from_hex("#eee8da", "light"),
                ],
                tags=["bone", "macabre"],
                biome_affinity=["crypt"],
            ),
            # Void purple
            Palette(
                id="void_purple",
                name="Void Purple",
                colors=[
                    Color.from_hex("#0a0a1e", "darkest"),
                    Color.from_hex("#2a1a4e", "dark"),
                    Color.from_hex("#5a3a8e", "mid"),
                    Color.from_hex("#aa7ace", "light"),
                ],
                tags=["void", "magic"],
                biome_affinity=["void"],
            ),
            # Sand yellow
            Palette(
                id="sand_yellow",
                name="Sand Yellow",
                colors=[
                    Color.from_hex("#3e2a1a", "darkest"),
                    Color.from_hex("#8e6a3a", "dark"),
                    Color.from_hex("#ceaa6a", "mid"),
                    Color.from_hex("#eee8ba", "light"),
                ],
                tags=["sand", "desert"],
            ),
            # Metal gray
            Palette(
                id="metal_gray",
                name="Metal Gray",
                colors=[
                    Color.from_hex("#1a1a1a", "darkest"),
                    Color.from_hex("#4a4a5a", "dark"),
                    Color.from_hex("#8a8a9a", "mid"),
                    Color.from_hex("#dadaea", "light"),
                ],
                tags=["metal", "industrial"],
            ),
            # Blood red
            Palette(
                id="blood_red",
                name="Blood Red",
                colors=[
                    Color.from_hex("#1a0a0a", "darkest"),
                    Color.from_hex("#4a1a1a", "dark"),
                    Color.from_hex("#8a2a2a", "mid"),
                    Color.from_hex("#ca5a5a", "light"),
                ],
                tags=["blood", "macabre"],
            ),
            # Ice blue
            Palette(
                id="ice_blue",
                name="Ice Blue",
                colors=[
                    Color.from_hex("#1a2a3e", "darkest"),
                    Color.from_hex("#4a6a8e", "dark"),
                    Color.from_hex("#8abaee", "mid"),
                    Color.from_hex("#daeeff", "light"),
                ],
                tags=["ice", "cold"],
            ),
        ]

        for palette in defaults:
            self._palettes[palette.id] = palette

    def get(self, palette_id: str) -> Optional[Palette]:
        """Get palette by ID."""
        self.initialize()
        return self._palettes.get(palette_id)

    def get_by_tag(self, tag: str) -> list[Palette]:
        """Get all palettes with a tag."""
        self.initialize()
        return [p for p in self._palettes.values() if tag in p.tags]

    def get_by_biome(self, biome: str) -> list[Palette]:
        """Get palettes with affinity for a biome."""
        self.initialize()
        return [p for p in self._palettes.values() if biome in p.biome_affinity]

    def all_palettes(self) -> list[Palette]:
        """Get all palettes."""
        self.initialize()
        return list(self._palettes.values())

    def register(self, palette: Palette) -> None:
        """Register a new palette."""
        self.initialize()
        self._palettes[palette.id] = palette


# Singleton
_palette_manager: Optional[PaletteManager] = None


def get_palette_manager(data_path: Optional[str] = None) -> PaletteManager:
    """Get singleton palette manager."""
    global _palette_manager
    if _palette_manager is None:
        _palette_manager = PaletteManager(data_path)
    return _palette_manager


def reset_palette_manager() -> None:
    """Reset singleton (for testing)."""
    global _palette_manager
    _palette_manager = None
