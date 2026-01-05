"""
Layer Manager for multi-layer glyph rendering.

Implements SNES-style layer system where each layer is its own text grid.
Layers are composited bottom-to-top for final display.
"""

from enum import IntEnum
from typing import Optional
from dataclasses import dataclass, field


class LayerType(IntEnum):
    """Rendering layers (SNES-style)."""
    BACKGROUND = 0    # Background terrain (floors, ground)
    STRUCTURE = 1     # Structures (walls, doors, props)
    ENTITY = 2        # Entities (player, enemies, NPCs, items)
    EFFECT = 3        # Effects / particles
    LIGHTING = 4      # Lighting overlays
    UI = 5            # UI elements (highlights, selection)


@dataclass
class Cell:
    """A single cell in a layer grid."""
    glyph_id: str = "empty.void"
    char: str = " "
    metadata: dict = field(default_factory=dict)


@dataclass
class Layer:
    """A single rendering layer (text grid)."""
    type: LayerType
    width: int
    height: int
    cells: list[list[Cell]] = field(default_factory=list)
    visible: bool = True
    opacity: float = 1.0

    def __post_init__(self):
        if not self.cells:
            self.cells = [
                [Cell() for _ in range(self.width)]
                for _ in range(self.height)
            ]

    def get(self, x: int, y: int) -> Optional[Cell]:
        """Get cell at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x]
        return None

    def set(self, x: int, y: int, glyph_id: str, char: str, metadata: Optional[dict] = None) -> bool:
        """Set cell at position. Returns True if successful."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.cells[y][x] = Cell(
                glyph_id=glyph_id,
                char=char,
                metadata=metadata or {}
            )
            return True
        return False

    def clear(self, glyph_id: str = "empty.void", char: str = " ") -> None:
        """Clear the entire layer."""
        for y in range(self.height):
            for x in range(self.width):
                self.cells[y][x] = Cell(glyph_id=glyph_id, char=char)

    def to_strings(self) -> list[str]:
        """Convert layer to list of strings for rendering."""
        return ["".join(cell.char for cell in row) for row in self.cells]

    def to_id_grid(self) -> list[list[str]]:
        """Convert layer to grid of glyph IDs."""
        return [[cell.glyph_id for cell in row] for row in self.cells]


class LayerManager:
    """
    Manages multiple rendering layers and composites them.

    Each layer is a text grid that can be manipulated independently.
    Layers are composited bottom-to-top for final display.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.layers: dict[LayerType, Layer] = {}

        # Create all layers
        for layer_type in LayerType:
            self.layers[layer_type] = Layer(
                type=layer_type,
                width=width,
                height=height
            )

    def get_layer(self, layer_type: LayerType) -> Layer:
        """Get a specific layer."""
        return self.layers[layer_type]

    def set_glyph(
        self,
        x: int,
        y: int,
        layer: LayerType,
        glyph_id: str,
        char: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """Set a glyph at position on specified layer."""
        return self.layers[layer].set(x, y, glyph_id, char, metadata)

    def get_glyph(self, x: int, y: int, layer: LayerType) -> Optional[Cell]:
        """Get glyph at position on specified layer."""
        return self.layers[layer].get(x, y)

    def clear_layer(self, layer_type: LayerType) -> None:
        """Clear a specific layer."""
        self.layers[layer_type].clear()

    def clear_all(self) -> None:
        """Clear all layers."""
        for layer in self.layers.values():
            layer.clear()

    def composite(self, include_empty: bool = False) -> list[str]:
        """
        Composite all visible layers into final display.

        Layers are composited bottom-to-top. Non-empty cells
        on higher layers override lower layers.

        Args:
            include_empty: If True, empty cells are included in output

        Returns:
            List of strings representing the composited display
        """
        result = [[" " for _ in range(self.width)] for _ in range(self.height)]

        # Composite layers from bottom to top
        for layer_type in sorted(LayerType):
            layer = self.layers[layer_type]
            if not layer.visible:
                continue

            for y in range(self.height):
                for x in range(self.width):
                    cell = layer.cells[y][x]
                    # Skip empty cells unless on background layer
                    if cell.char != " " or layer_type == LayerType.BACKGROUND:
                        if cell.char != " " or include_empty:
                            result[y][x] = cell.char

        return ["".join(row) for row in result]

    def composite_ids(self) -> list[list[str]]:
        """
        Composite all visible layers into glyph ID grid.

        Returns:
            2D grid of glyph IDs (topmost non-empty glyph at each position)
        """
        result = [["empty.void" for _ in range(self.width)] for _ in range(self.height)]

        for layer_type in sorted(LayerType):
            layer = self.layers[layer_type]
            if not layer.visible:
                continue

            for y in range(self.height):
                for x in range(self.width):
                    cell = layer.cells[y][x]
                    if cell.glyph_id != "empty.void":
                        result[y][x] = cell.glyph_id

        return result

    def get_all_at(self, x: int, y: int) -> list[tuple[LayerType, Cell]]:
        """
        Get all non-empty cells at a position across all layers.

        Returns:
            List of (layer_type, cell) tuples from bottom to top
        """
        result = []
        for layer_type in sorted(LayerType):
            cell = self.layers[layer_type].get(x, y)
            if cell and cell.glyph_id != "empty.void":
                result.append((layer_type, cell))
        return result

    def load_map(
        self,
        map_lines: list[str],
        layer: LayerType,
        glyph_resolver: callable
    ) -> None:
        """
        Load a character map into a layer.

        Args:
            map_lines: List of strings representing the map
            layer: Target layer
            glyph_resolver: Function(char) -> (glyph_id, char) or None
        """
        target = self.layers[layer]

        for y, line in enumerate(map_lines):
            if y >= self.height:
                break
            for x, char in enumerate(line):
                if x >= self.width:
                    break
                result = glyph_resolver(char)
                if result:
                    glyph_id, display_char = result
                    target.set(x, y, glyph_id, display_char)
                else:
                    target.set(x, y, f"unknown.{char}", char)

    def apply_overlay(
        self,
        overlay_map: list[list[Optional[str]]],
        layer: LayerType = LayerType.LIGHTING,
        glyph_resolver: Optional[callable] = None
    ) -> None:
        """
        Apply an overlay map to a layer.

        Args:
            overlay_map: 2D grid of glyph IDs (None = no overlay)
            layer: Target layer
            glyph_resolver: Optional function to resolve glyph ID to char
        """
        target = self.layers[layer]

        for y, row in enumerate(overlay_map):
            if y >= self.height:
                break
            for x, glyph_id in enumerate(row):
                if x >= self.width:
                    break
                if glyph_id is not None:
                    char = "?"
                    if glyph_resolver:
                        result = glyph_resolver(glyph_id)
                        if result:
                            char = result[1]
                    target.set(x, y, glyph_id, char)

    def to_dict(self) -> dict:
        """Serialize layer manager state to dictionary."""
        return {
            "width": self.width,
            "height": self.height,
            "layers": {
                layer_type.name: {
                    "visible": layer.visible,
                    "opacity": layer.opacity,
                    "cells": [
                        [
                            {"glyph_id": cell.glyph_id, "char": cell.char}
                            for cell in row
                        ]
                        for row in layer.cells
                    ]
                }
                for layer_type, layer in self.layers.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LayerManager":
        """Deserialize layer manager from dictionary."""
        manager = cls(data["width"], data["height"])

        for layer_name, layer_data in data.get("layers", {}).items():
            layer_type = LayerType[layer_name]
            layer = manager.layers[layer_type]
            layer.visible = layer_data.get("visible", True)
            layer.opacity = layer_data.get("opacity", 1.0)

            for y, row in enumerate(layer_data.get("cells", [])):
                for x, cell_data in enumerate(row):
                    layer.set(
                        x, y,
                        cell_data.get("glyph_id", "empty.void"),
                        cell_data.get("char", " ")
                    )

        return manager
