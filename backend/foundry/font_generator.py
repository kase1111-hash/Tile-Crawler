"""
Font Generator - Creates TTF fonts from glyph tile definitions.

Pipeline:
1. Read glyph definitions from glyphs.json
2. Rasterize each glyph to a bitmap using procedural patterns
3. Convert bitmaps to font outlines using fonttools
4. Export TTF file for web use
"""

import json
import os
from io import BytesIO
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from PIL import Image, ImageDraw

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont

from .palettes import Color, Palette, get_palette_manager


# Tile patterns for procedural generation
TILE_PATTERNS = {
    # Ground patterns (8x8 pixel templates)
    "floor.stone": [
        "########",
        "#......#",
        "#......#",
        "#..##..#",
        "#..##..#",
        "#......#",
        "#......#",
        "########",
    ],
    "floor.stone.cracked": [
        "##/##/##",
        "#......#",
        "#./....#",
        "#..##..#",
        "#./##/.#",
        "#......#",
        "#.././.#",
        "########",
    ],
    "floor.dirt": [
        "........",
        "..::....",
        ".....:..",
        "...:....",
        "........",
        ".:......",
        "....:::.",
        "........",
    ],
    "floor.grass": [
        "........",
        '..".."..',
        '..."....',
        '........',
        '..".."."',
        '........',
        '."......',
        '........',
    ],
    "floor.wood": [
        "========",
        "========",
        "--------",
        "========",
        "========",
        "--------",
        "========",
        "========",
    ],
    # Wall patterns
    "wall.solid": [
        "########",
        "########",
        "########",
        "########",
        "########",
        "########",
        "########",
        "########",
    ],
    "wall.brick": [
        "##|##|##",
        "##|##|##",
        "--------",
        "|##|##|#",
        "|##|##|#",
        "--------",
        "##|##|##",
        "##|##|##",
    ],
    "wall.stone": [
        "#@##@###",
        "########",
        "###@#@##",
        "##@#####",
        "#####@##",
        "@#######",
        "###@##@#",
        "########",
    ],
    # Fluid patterns
    "fluid.water": [
        "~~~~~~~~",
        "~~~~~~~≈",
        "~~~~~~≈~",
        "~~~~~≈~~",
        "~~~~≈~~~",
        "~~~≈~~~~",
        "~~≈~~~~~",
        "~≈~~~~~~",
    ],
    "fluid.lava": [
        "▓▒▓▓▒▓▓▓",
        "▓▓▒▓▓▓▒▓",
        "▒▓▓▓▒▓▓▓",
        "▓▓▒▓▓▒▓▓",
        "▓▒▓▓▓▓▒▓",
        "▓▓▓▒▓▓▓▓",
        "▒▓▓▓▓▒▓▒",
        "▓▓▒▓▓▓▓▓",
    ],
    # Prop patterns
    "prop.door.closed": [
        "##+=+###",
        "##|.|###",
        "##|.|###",
        "##|o|###",
        "##|.|###",
        "##|.|###",
        "##|_|###",
        "########",
    ],
    "prop.door.open": [
        "##/ \\###",
        "## . ###",
        "## . ###",
        "## . ###",
        "## . ###",
        "## . ###",
        "## . ###",
        "########",
    ],
    "prop.stairs.down": [
        "........",
        ".>>>>>>.",
        ".>>>>>. ",
        ".>>>>. .",
        ".>>>. ..",
        ".>>. ...",
        ".>. ....",
        "........",
    ],
    "prop.stairs.up": [
        "........",
        ".<<<<<<.",
        " .<<<<< ",
        ". .<<<<.",
        ".. .<<<.",
        "... .<<.",
        ".... .<.",
        "........",
    ],
    "prop.chest": [
        "........",
        ".######.",
        ".#■■■■#.",
        ".#----#.",
        ".#■■■■#.",
        ".#■■■■#.",
        ".######.",
        "........",
    ],
    # Entity patterns
    "entity.player": [
        "...@@...",
        "..@@@@..",
        "..@@@@..",
        "...@@...",
        "..@@@@..",
        ".@@@@@@.",
        "..@..@..",
        "..@..@..",
    ],
    "entity.enemy": [
        "..&&&...",
        ".&&&&&..",
        ".&o.o&..",
        ".&&&&&..",
        "..&&&...",
        ".&&&&&..",
        ".&.&.&..",
        ".&...&..",
    ],
    "entity.npc": [
        "...@@...",
        "..@@@@..",
        "..o..o..",
        "...@@...",
        "..@@@@..",
        ".@@@@@@.",
        "..@..@..",
        "..@..@..",
    ],
    # Item patterns
    "item.potion": [
        "........",
        "...##...",
        "..#..#..",
        "..####..",
        ".##..##.",
        ".#....#.",
        ".##..##.",
        "..####..",
    ],
    "item.gold": [
        "........",
        "..####..",
        ".#$$$$#.",
        ".#$$$$#.",
        ".#$$$$#.",
        ".#$$$$#.",
        "..####..",
        "........",
    ],
    "item.key": [
        "........",
        "..ooo...",
        "..o.o...",
        "..ooo...",
        "...o....",
        "...oo...",
        "...o....",
        "...o....",
    ],
    # Effect patterns
    "effect.torch": [
        "....*...",
        "..****..",
        "..****...",
        "...**..",
        "...|...",
        "...|...",
        "...|...",
        "...|...",
    ],
    "effect.fire": [
        "...^....",
        "..^^^...",
        ".^^^^^..",
        ".^^^^^..",
        "..^^^...",
        "...^....",
        "........",
        "........",
    ],
    # Empty
    "empty.void": [
        "        ",
        "        ",
        "        ",
        "        ",
        "        ",
        "        ",
        "        ",
        "        ",
    ],
}


@dataclass
class TileRasterConfig:
    """Configuration for tile rasterization."""
    tile_size: int = 8  # Base tile size in pixels
    scale: int = 1      # Scale factor for output
    palette_id: str = "stone_gray_4"


@dataclass
class RasterizedTile:
    """A rasterized tile ready for font embedding."""
    glyph_id: str
    codepoint: int
    char: str
    image: Image.Image
    width: int
    height: int


class TileRasterizer:
    """
    Rasterizes glyph definitions to bitmap images.

    Uses procedural patterns + palette colors to generate pixel art tiles.
    """

    def __init__(self, config: Optional[TileRasterConfig] = None):
        self.config = config or TileRasterConfig()
        self.palette_manager = get_palette_manager()
        self._cache: dict[str, RasterizedTile] = {}

    def get_pattern(self, glyph_id: str) -> list[str]:
        """Get or generate pattern for a glyph."""
        # Try exact match first
        if glyph_id in TILE_PATTERNS:
            return TILE_PATTERNS[glyph_id]

        # Try category match
        category = glyph_id.split(".")[0] if "." in glyph_id else glyph_id
        for pattern_id, pattern in TILE_PATTERNS.items():
            if pattern_id.startswith(category):
                return pattern

        # Generate from character
        return self._generate_char_pattern(glyph_id)

    def _generate_char_pattern(self, glyph_id: str) -> list[str]:
        """Generate a simple pattern from a single character."""
        # Get fallback char from glyph_id
        char_map = {
            "empty": " ",
            "floor": ".",
            "ground": ".",
            "wall": "#",
            "door": "+",
            "fluid": "~",
            "water": "≈",
            "lava": "▓",
            "prop": "■",
            "item": "!",
            "entity": "@",
            "effect": "*",
        }

        category = glyph_id.split(".")[0] if "." in glyph_id else glyph_id
        char = char_map.get(category, "?")

        # Create centered character pattern
        return [
            "        ",
            "        ",
            f"   {char}    ",
            f"   {char}    ",
            f"   {char}    ",
            "        ",
            "        ",
            "        ",
        ]

    def get_palette_for_glyph(self, glyph_id: str, glyph_data: dict) -> Palette:
        """Determine appropriate palette for a glyph."""
        # Check if palette specified in visual
        visual = glyph_data.get("visual", {})
        if "palette" in visual:
            palette = self.palette_manager.get(visual["palette"])
            if palette:
                return palette

        # Match by category/tags
        category = glyph_data.get("category", "")
        tags = glyph_data.get("tags", [])

        palette_map = {
            "ground": "stone_gray_4",
            "wall": "stone_gray",
            "fluid": "water_blue",
            "door": "wood_brown",
            "prop": "wood_brown",
            "item": "metal_gray",
            "entity": "blood_red",
            "effect": "lava_orange",
        }

        # Check tags for biome hints
        if "water" in tags:
            return self.palette_manager.get("water_blue")
        if "lava" in tags:
            return self.palette_manager.get("lava_orange")
        if "nature" in tags or "grass" in tags:
            return self.palette_manager.get("nature_green")
        if "wood" in tags:
            return self.palette_manager.get("wood_brown")
        if "bone" in tags or "crypt" in tags:
            return self.palette_manager.get("bone_white")
        if "void" in tags or "magic" in tags:
            return self.palette_manager.get("void_purple")

        palette_id = palette_map.get(category, "stone_gray_4")
        return self.palette_manager.get(palette_id)

    def rasterize(self, glyph_id: str, glyph_data: dict) -> RasterizedTile:
        """Rasterize a single glyph to a bitmap."""
        # Check cache
        if glyph_id in self._cache:
            return self._cache[glyph_id]

        # Get pattern and palette
        pattern = self.get_pattern(glyph_id)
        palette = self.get_palette_for_glyph(glyph_id, glyph_data)

        # Calculate dimensions
        size = self.config.tile_size * self.config.scale

        # Create image
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Map pattern characters to colors
        color_map = self._build_color_map(palette, glyph_data)

        # Draw each pixel
        pixel_size = self.config.scale
        for y, row in enumerate(pattern):
            for x, char in enumerate(row):
                if x >= self.config.tile_size or y >= self.config.tile_size:
                    continue

                color = color_map.get(char, (0, 0, 0, 0))
                if color[3] > 0:  # Not transparent
                    px = x * pixel_size
                    py = y * pixel_size
                    draw.rectangle(
                        [px, py, px + pixel_size - 1, py + pixel_size - 1],
                        fill=color
                    )

        # Parse codepoint
        codepoint_str = glyph_data.get("codepoint", "U+E000")
        codepoint = int(codepoint_str.replace("U+", ""), 16)

        result = RasterizedTile(
            glyph_id=glyph_id,
            codepoint=codepoint,
            char=glyph_data.get("char", "?"),
            image=img,
            width=size,
            height=size,
        )

        self._cache[glyph_id] = result
        return result

    def _build_color_map(self, palette: Palette, glyph_data: dict) -> dict[str, tuple]:
        """Build character-to-color mapping."""
        colors = palette.colors if palette else [
            Color.from_hex("#1a1a2e"),
            Color.from_hex("#5a5a6e"),
            Color.from_hex("#9a9aae"),
            Color.from_hex("#dadaee"),
        ]

        # Ensure we have at least 4 colors
        while len(colors) < 4:
            colors.append(colors[-1])

        # Map pattern characters to palette indices
        return {
            " ": (0, 0, 0, 0),           # Transparent
            ".": colors[1].to_rgba(),     # Light floor
            ",": colors[1].to_rgba(),     # Cracked
            ":": colors[2].to_rgba(),     # Dots
            "#": colors[0].to_rgba(),     # Dark wall
            "@": colors[3].to_rgba(),     # Highlight (player)
            "&": colors[2].to_rgba(),     # Entity
            "~": colors[2].to_rgba(),     # Water
            "≈": colors[3].to_rgba(),     # Water highlight
            "▓": colors[0].to_rgba(),     # Dark solid
            "▒": colors[3].to_rgba(),     # Lava glow
            "+": colors[0].to_rgba(),     # Door frame
            "-": colors[0].to_rgba(),     # Horizontal line
            "|": colors[0].to_rgba(),     # Vertical line
            "=": colors[1].to_rgba(),     # Wood plank
            "/": colors[0].to_rgba(),     # Crack
            "\\": colors[0].to_rgba(),    # Crack
            ">": colors[2].to_rgba(),     # Stairs down
            "<": colors[2].to_rgba(),     # Stairs up
            "^": colors[3].to_rgba(),     # Fire
            "*": colors[3].to_rgba(),     # Sparkle
            "o": colors[3].to_rgba(),     # Detail
            "$": colors[3].to_rgba(),     # Gold
            "■": colors[1].to_rgba(),     # Chest body
            "_": colors[1].to_rgba(),     # Bottom
            "!": colors[3].to_rgba(),     # Item
            "?": colors[2].to_rgba(),     # Unknown
        }

    def rasterize_all(self, glyphs: list[dict]) -> list[RasterizedTile]:
        """Rasterize all glyphs."""
        results = []
        for glyph in glyphs:
            glyph_id = glyph.get("id", "unknown")
            try:
                tile = self.rasterize(glyph_id, glyph)
                results.append(tile)
            except Exception as e:
                print(f"Warning: Failed to rasterize {glyph_id}: {e}")
        return results


class FontGenerator:
    """
    Generates TTF fonts from rasterized tiles.

    Creates a web-ready font file with custom glyphs in the Private Use Area.
    """

    def __init__(
        self,
        font_name: str = "TileCrawler",
        em_size: int = 1000,
        tile_size: int = 8,
    ):
        self.font_name = font_name
        self.em_size = em_size  # Font units per em
        self.tile_size = tile_size
        self.scale = em_size // tile_size  # Pixels to font units

        self.rasterizer = TileRasterizer(
            TileRasterConfig(tile_size=tile_size)
        )

    def generate(
        self,
        glyphs_data: list[dict],
        output_path: str,
    ) -> str:
        """
        Generate a TTF font from glyph definitions.

        Args:
            glyphs_data: List of glyph definitions from glyphs.json
            output_path: Path to write TTF file

        Returns:
            Path to generated font file
        """
        # Rasterize all glyphs
        tiles = self.rasterizer.rasterize_all(glyphs_data)

        if not tiles:
            raise ValueError("No tiles to generate font from")

        # Build font
        font = self._build_font(tiles)

        # Write output
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        font.save(str(output_path))

        return str(output_path)

    def _build_font(self, tiles: list[RasterizedTile]) -> TTFont:
        """Build TTF font from rasterized tiles."""
        # Collect all codepoints
        cmap = {}
        glyph_order = [".notdef"]
        char_strings = {}

        # Create .notdef glyph (required)
        notdef_pen = T2CharStringPen(self.em_size, None)
        notdef_pen.moveTo((0, 0))
        notdef_pen.lineTo((self.em_size, 0))
        notdef_pen.lineTo((self.em_size, self.em_size))
        notdef_pen.lineTo((0, self.em_size))
        notdef_pen.closePath()
        char_strings[".notdef"] = notdef_pen.getCharString()

        # Process each tile
        for tile in tiles:
            glyph_name = f"uni{tile.codepoint:04X}"

            # Add to character map
            cmap[tile.codepoint] = glyph_name
            glyph_order.append(glyph_name)

            # Convert bitmap to outline
            char_string = self._bitmap_to_charstring(tile.image)
            char_strings[glyph_name] = char_string

        # Also add ASCII fallback characters
        for tile in tiles:
            if tile.char and ord(tile.char) < 0xE000:
                ascii_code = ord(tile.char)
                if ascii_code not in cmap:
                    cmap[ascii_code] = f"uni{tile.codepoint:04X}"

        # Build font using FontBuilder
        fb = FontBuilder(self.em_size, isTTF=False)  # CFF outlines
        fb.setupGlyphOrder(glyph_order)
        fb.setupCharacterMap(cmap)

        # Font naming
        fb.setupNameTable({
            "familyName": self.font_name,
            "styleName": "Regular",
        })

        # Setup CFF with proper arguments for fonttools
        # setupCFF(psName, fontInfo, charStringsDict, privateDict)
        fb.setupCFF(
            self.font_name,  # psName
            {"FullName": self.font_name},  # fontInfo
            char_strings,  # charStringsDict
            {},  # privateDict
        )

        # Metrics
        metrics = {}
        for name in glyph_order:
            metrics[name] = (self.em_size, 0)  # width, lsb
        fb.setupHorizontalMetrics(metrics)

        # OS/2 and other tables
        fb.setupHorizontalHeader(ascent=self.em_size, descent=0)
        fb.setupOS2()
        fb.setupPost()
        fb.setupHead(unitsPerEm=self.em_size)

        return fb.font

    def _bitmap_to_charstring(self, img: Image.Image) -> object:
        """Convert bitmap to CFF CharString (outline)."""
        pen = T2CharStringPen(self.em_size, None)

        # Get pixel data
        pixels = img.load()
        width, height = img.size

        # Track which pixels we've drawn (for combining rectangles)
        drawn = [[False] * width for _ in range(height)]

        # Draw each opaque pixel as a rectangle
        # (In a more sophisticated version, we'd combine adjacent pixels)
        for y in range(height):
            for x in range(width):
                if drawn[y][x]:
                    continue

                pixel = pixels[x, y]
                if len(pixel) >= 4 and pixel[3] > 127:  # Opaque
                    # Find rectangle extent (simple greedy)
                    end_x = x
                    while end_x + 1 < width and not drawn[y][end_x + 1]:
                        next_pixel = pixels[end_x + 1, y]
                        if len(next_pixel) >= 4 and next_pixel[3] > 127:
                            end_x += 1
                        else:
                            break

                    # Mark as drawn
                    for dx in range(x, end_x + 1):
                        drawn[y][dx] = True

                    # Convert to font coordinates (flip Y, scale)
                    x1 = x * self.scale
                    y1 = (height - y - 1) * self.scale
                    x2 = (end_x + 1) * self.scale
                    y2 = (height - y) * self.scale

                    # Draw rectangle
                    pen.moveTo((x1, y1))
                    pen.lineTo((x2, y1))
                    pen.lineTo((x2, y2))
                    pen.lineTo((x1, y2))
                    pen.closePath()

        return pen.getCharString()


def generate_tile_font(
    glyphs_json_path: str,
    output_path: str,
    font_name: str = "TileCrawler",
) -> str:
    """
    Main entry point for font generation.

    Args:
        glyphs_json_path: Path to glyphs.json
        output_path: Path to write TTF file
        font_name: Name for the generated font

    Returns:
        Path to generated font file
    """
    # Load glyph definitions
    with open(glyphs_json_path, "r") as f:
        data = json.load(f)

    glyphs = data.get("glyphs", [])

    if not glyphs:
        raise ValueError(f"No glyphs found in {glyphs_json_path}")

    # Generate font
    generator = FontGenerator(font_name=font_name)
    return generator.generate(glyphs, output_path)


def export_tile_sprites(
    glyphs_json_path: str,
    output_dir: str,
    scale: int = 1,
) -> list[str]:
    """
    Export individual tile sprites as PNG files.

    Args:
        glyphs_json_path: Path to glyphs.json
        output_dir: Directory to write PNG files
        scale: Scale factor (1 = 8x8, 2 = 16x16, etc.)

    Returns:
        List of generated file paths
    """
    # Load glyph definitions
    with open(glyphs_json_path, "r") as f:
        data = json.load(f)

    glyphs = data.get("glyphs", [])

    # Rasterize
    rasterizer = TileRasterizer(
        TileRasterConfig(tile_size=8, scale=scale)
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for glyph in glyphs:
        glyph_id = glyph.get("id", "unknown")
        tile = rasterizer.rasterize(glyph_id, glyph)

        # Write PNG
        filename = f"{glyph_id.replace('.', '_')}.png"
        path = output_dir / filename
        tile.image.save(str(path))
        paths.append(str(path))

    return paths


if __name__ == "__main__":
    import sys

    # Default paths
    base_dir = Path(__file__).parent.parent.parent
    glyphs_path = base_dir / "data" / "glyphs.json"
    output_path = base_dir / "frontend" / "public" / "fonts" / "TileCrawler.otf"

    if len(sys.argv) > 1:
        output_path = Path(sys.argv[1])

    print(f"Generating font from {glyphs_path}")
    print(f"Output: {output_path}")

    result = generate_tile_font(str(glyphs_path), str(output_path))
    print(f"Generated: {result}")
