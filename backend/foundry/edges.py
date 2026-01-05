"""
Edge Compatibility System - Wave Function Collapse compatible tiling.

Ensures perfect tile meshing through edge signature matching.
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from .grammar import EdgeCode, EdgeSignature, EDGE_COMPATIBILITY


class Direction(str, Enum):
    """Cardinal directions."""
    NORTH = "north"
    EAST = "east"
    SOUTH = "south"
    WEST = "west"


# Direction opposites
OPPOSITE_DIRECTION = {
    Direction.NORTH: Direction.SOUTH,
    Direction.SOUTH: Direction.NORTH,
    Direction.EAST: Direction.WEST,
    Direction.WEST: Direction.EAST,
}


@dataclass
class TileSocket:
    """A tile's connection socket for a specific direction."""
    direction: Direction
    edge_code: EdgeCode
    compatible_codes: set[EdgeCode] = field(default_factory=set)

    def __post_init__(self):
        if not self.compatible_codes:
            self.compatible_codes = EDGE_COMPATIBILITY.get(self.edge_code, {self.edge_code})


@dataclass
class EdgeCompatibility:
    """Tracks edge compatibility for a tile type."""
    tile_id: str
    signature: EdgeSignature
    sockets: dict[Direction, TileSocket] = field(default_factory=dict)

    def __post_init__(self):
        if not self.sockets:
            self.sockets = {
                Direction.NORTH: TileSocket(Direction.NORTH, self.signature.north),
                Direction.EAST: TileSocket(Direction.EAST, self.signature.east),
                Direction.SOUTH: TileSocket(Direction.SOUTH, self.signature.south),
                Direction.WEST: TileSocket(Direction.WEST, self.signature.west),
            }

    def can_connect(self, other: "EdgeCompatibility", direction: Direction) -> bool:
        """Check if this tile can connect to another in the given direction."""
        my_socket = self.sockets[direction]
        opposite = OPPOSITE_DIRECTION[direction]
        their_socket = other.sockets[opposite]

        return their_socket.edge_code in my_socket.compatible_codes


class EdgeSystem:
    """
    Manages edge compatibility for tile placement.

    Supports Wave Function Collapse style constraint propagation.
    """

    def __init__(self):
        self._tiles: dict[str, EdgeCompatibility] = {}
        self._by_signature: dict[str, list[str]] = {}  # signature code -> tile IDs

    def register_tile(self, tile_id: str, signature: EdgeSignature) -> EdgeCompatibility:
        """Register a tile with its edge signature."""
        compat = EdgeCompatibility(tile_id=tile_id, signature=signature)
        self._tiles[tile_id] = compat

        # Index by signature
        sig_code = signature.to_code()
        if sig_code not in self._by_signature:
            self._by_signature[sig_code] = []
        self._by_signature[sig_code].append(tile_id)

        return compat

    def get_tile(self, tile_id: str) -> Optional[EdgeCompatibility]:
        """Get edge compatibility for a tile."""
        return self._tiles.get(tile_id)

    def get_by_signature(self, signature: EdgeSignature) -> list[str]:
        """Get all tiles with a given signature."""
        return self._by_signature.get(signature.to_code(), [])

    def can_place(
        self,
        tile_id: str,
        neighbors: dict[Direction, str]
    ) -> bool:
        """
        Check if a tile can be placed given its neighbors.

        Args:
            tile_id: ID of tile to place
            neighbors: Dict of direction -> neighbor tile ID

        Returns:
            True if placement is valid
        """
        tile = self._tiles.get(tile_id)
        if not tile:
            return True  # Unknown tile, allow

        for direction, neighbor_id in neighbors.items():
            neighbor = self._tiles.get(neighbor_id)
            if neighbor and not tile.can_connect(neighbor, direction):
                return False

        return True

    def get_valid_placements(
        self,
        neighbors: dict[Direction, str]
    ) -> list[str]:
        """
        Get all tiles that can be validly placed given neighbors.

        Args:
            neighbors: Dict of direction -> neighbor tile ID

        Returns:
            List of valid tile IDs
        """
        valid = []

        for tile_id, tile in self._tiles.items():
            if self.can_place(tile_id, neighbors):
                valid.append(tile_id)

        return valid

    def get_compatible_for_direction(
        self,
        tile_id: str,
        direction: Direction
    ) -> list[str]:
        """
        Get all tiles that can connect to given tile in direction.

        Args:
            tile_id: Source tile ID
            direction: Direction to check

        Returns:
            List of compatible tile IDs
        """
        tile = self._tiles.get(tile_id)
        if not tile:
            return list(self._tiles.keys())

        my_socket = tile.sockets[direction]
        compatible = []

        for other_id, other in self._tiles.items():
            opposite = OPPOSITE_DIRECTION[direction]
            their_code = other.sockets[opposite].edge_code
            if their_code in my_socket.compatible_codes:
                compatible.append(other_id)

        return compatible

    def generate_adjacency_rules(self) -> dict[str, dict[str, list[str]]]:
        """
        Generate complete adjacency rules for WFC.

        Returns:
            Dict of tile_id -> {direction -> [compatible_tile_ids]}
        """
        rules = {}

        for tile_id in self._tiles:
            rules[tile_id] = {}
            for direction in Direction:
                rules[tile_id][direction.value] = self.get_compatible_for_direction(
                    tile_id, direction
                )

        return rules

    def validate_map(
        self,
        tile_grid: list[list[str]]
    ) -> list[tuple[int, int, str, str]]:
        """
        Validate a tile map for edge compatibility.

        Args:
            tile_grid: 2D grid of tile IDs

        Returns:
            List of (x, y, direction, error_message) for violations
        """
        violations = []
        height = len(tile_grid)
        if height == 0:
            return violations

        width = len(tile_grid[0])

        for y in range(height):
            for x in range(width):
                tile_id = tile_grid[y][x]
                tile = self._tiles.get(tile_id)
                if not tile:
                    continue

                # Check north
                if y > 0:
                    north_id = tile_grid[y - 1][x]
                    north = self._tiles.get(north_id)
                    if north and not tile.can_connect(north, Direction.NORTH):
                        violations.append((
                            x, y, "north",
                            f"{tile_id} incompatible with {north_id}"
                        ))

                # Check west
                if x > 0:
                    west_id = tile_grid[y][x - 1]
                    west = self._tiles.get(west_id)
                    if west and not tile.can_connect(west, Direction.WEST):
                        violations.append((
                            x, y, "west",
                            f"{tile_id} incompatible with {west_id}"
                        ))

        return violations

    def suggest_fix(
        self,
        tile_grid: list[list[str]],
        x: int,
        y: int
    ) -> list[str]:
        """
        Suggest valid tiles for a position that has violations.

        Args:
            tile_grid: Current tile grid
            x, y: Position to fix

        Returns:
            List of valid tile IDs for that position
        """
        height = len(tile_grid)
        width = len(tile_grid[0]) if height > 0 else 0

        neighbors = {}

        if y > 0:
            neighbors[Direction.NORTH] = tile_grid[y - 1][x]
        if y < height - 1:
            neighbors[Direction.SOUTH] = tile_grid[y + 1][x]
        if x > 0:
            neighbors[Direction.WEST] = tile_grid[y][x - 1]
        if x < width - 1:
            neighbors[Direction.EAST] = tile_grid[y][x + 1]

        return self.get_valid_placements(neighbors)


# Singleton
_edge_system: Optional[EdgeSystem] = None


def get_edge_system() -> EdgeSystem:
    """Get singleton edge system."""
    global _edge_system
    if _edge_system is None:
        _edge_system = EdgeSystem()
    return _edge_system


def reset_edge_system() -> None:
    """Reset singleton (for testing)."""
    global _edge_system
    _edge_system = None
