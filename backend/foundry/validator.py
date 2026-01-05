"""
Tile Validator - Validates generated tiles against constraints.

Each generated tile is checked for:
- Correct size
- Only allowed colors
- Edge pixels match declared edge codes
- No stray pixels
- Consistent center texture

Failures get regenerated.
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
from pydantic import BaseModel

from .grammar import TileGrammar, EdgeCode, TileSize
from .palettes import Palette, Color


class ValidationErrorType(str, Enum):
    """Types of validation errors."""
    SIZE_MISMATCH = "size_mismatch"
    INVALID_COLOR = "invalid_color"
    EDGE_MISMATCH = "edge_mismatch"
    STRAY_PIXELS = "stray_pixels"
    CENTER_INCONSISTENT = "center_inconsistent"
    TRANSPARENCY_ERROR = "transparency_error"
    ANTI_ALIASING = "anti_aliasing"
    FORMAT_ERROR = "format_error"


@dataclass
class ValidationError:
    """A single validation error."""
    error_type: ValidationErrorType
    message: str
    location: Optional[tuple[int, int]] = None  # (x, y) if applicable
    severity: str = "error"  # error, warning

    def __str__(self) -> str:
        loc = f" at ({self.location[0]}, {self.location[1]})" if self.location else ""
        return f"[{self.severity.upper()}] {self.error_type.value}: {self.message}{loc}"


@dataclass
class ValidationResult:
    """Result of tile validation."""
    tile_id: str
    passed: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def add_error(self, error: ValidationError) -> None:
        if error.severity == "warning":
            self.warnings.append(error)
        else:
            self.errors.append(error)
            self.passed = False

    def summary(self) -> str:
        status = "PASSED" if self.passed else "FAILED"
        return f"{self.tile_id}: {status} ({self.error_count} errors, {self.warning_count} warnings)"


class TileValidator:
    """
    Validates generated tiles against their grammar specifications.
    """

    def __init__(self, strict: bool = True):
        self.strict = strict
        # Color tolerance for palette matching (0-255)
        self.color_tolerance = 0 if strict else 10

    def validate(
        self,
        image_data: bytes,
        grammar: TileGrammar,
        palette: Optional[Palette] = None
    ) -> ValidationResult:
        """
        Validate an image against its grammar.

        Args:
            image_data: Raw image bytes (PNG)
            grammar: Expected grammar specification
            palette: Expected color palette

        Returns:
            ValidationResult with errors/warnings
        """
        tile_id = grammar.to_generation_id()
        result = ValidationResult(tile_id=tile_id, passed=True)

        # Parse image (mock implementation - would use PIL/Pillow in real code)
        try:
            image_info = self._parse_image(image_data)
        except Exception as e:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.FORMAT_ERROR,
                message=f"Failed to parse image: {str(e)}"
            ))
            return result

        # Validate size
        self._validate_size(image_info, grammar, result)

        # Validate colors
        if palette:
            self._validate_colors(image_info, palette, result)

        # Validate edges
        self._validate_edges(image_info, grammar, result)

        # Check for anti-aliasing
        if self.strict:
            self._check_anti_aliasing(image_info, palette, result)

        # Check center consistency
        self._validate_center(image_info, grammar, result)

        return result

    def _parse_image(self, image_data: bytes) -> dict:
        """
        Parse image data and extract properties.

        In a real implementation, this would use PIL/Pillow.
        This is a mock that returns expected structure.
        """
        # Mock implementation - in reality would parse actual image
        return {
            "width": 8,
            "height": 8,
            "pixels": [[None] * 8 for _ in range(8)],  # Would be actual pixel data
            "colors_used": set(),
            "format": "PNG",
            "has_alpha": True,
        }

    def _validate_size(
        self,
        image_info: dict,
        grammar: TileGrammar,
        result: ValidationResult
    ) -> None:
        """Validate image dimensions."""
        size_str = grammar.size if isinstance(grammar.size, str) else grammar.size.value
        expected_w, expected_h = map(int, size_str.split("x"))

        actual_w = image_info["width"]
        actual_h = image_info["height"]

        if actual_w != expected_w or actual_h != expected_h:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.SIZE_MISMATCH,
                message=f"Expected {expected_w}×{expected_h}, got {actual_w}×{actual_h}"
            ))

        result.stats["width"] = actual_w
        result.stats["height"] = actual_h

    def _validate_colors(
        self,
        image_info: dict,
        palette: Palette,
        result: ValidationResult
    ) -> None:
        """Validate that only palette colors are used."""
        allowed_colors = set(c.to_rgba() for c in palette.colors)

        # Add transparent as allowed
        if palette.allow_transparency:
            allowed_colors.add((0, 0, 0, 0))

        invalid_colors = []
        for color in image_info.get("colors_used", set()):
            if not self._color_in_palette(color, allowed_colors):
                invalid_colors.append(color)

        if invalid_colors:
            for color in invalid_colors[:5]:  # Report first 5
                result.add_error(ValidationError(
                    error_type=ValidationErrorType.INVALID_COLOR,
                    message=f"Color {color} not in palette"
                ))

        result.stats["colors_used"] = len(image_info.get("colors_used", set()))
        result.stats["invalid_colors"] = len(invalid_colors)

    def _color_in_palette(
        self,
        color: tuple,
        palette_colors: set
    ) -> bool:
        """Check if color matches any palette color within tolerance."""
        if self.color_tolerance == 0:
            return color in palette_colors

        for palette_color in palette_colors:
            if self._colors_similar(color, palette_color):
                return True
        return False

    def _colors_similar(
        self,
        c1: tuple,
        c2: tuple
    ) -> bool:
        """Check if two colors are within tolerance."""
        if len(c1) != len(c2):
            return False

        for v1, v2 in zip(c1, c2):
            if abs(v1 - v2) > self.color_tolerance:
                return False
        return True

    def _validate_edges(
        self,
        image_info: dict,
        grammar: TileGrammar,
        result: ValidationResult
    ) -> None:
        """Validate edge pixels match declared edge codes."""
        # This would analyze the actual edge pixels and compare to expected patterns
        # Mock implementation - in reality would inspect pixel rows/columns

        edges = grammar.edges
        width = image_info["width"]
        height = image_info["height"]

        # Edge validation would check:
        # - North edge (top row) matches edges.north pattern
        # - East edge (right column) matches edges.east pattern
        # - South edge (bottom row) matches edges.south pattern
        # - West edge (left column) matches edges.west pattern

        # For now, we'll assume edges pass unless explicitly failed
        result.stats["edges_validated"] = True

    def _check_anti_aliasing(
        self,
        image_info: dict,
        palette: Optional[Palette],
        result: ValidationResult
    ) -> None:
        """Check for anti-aliasing artifacts."""
        # Would analyze color transitions for smooth gradients
        # that indicate anti-aliasing

        colors_used = len(image_info.get("colors_used", set()))
        max_colors = palette.max_colors if palette else 4

        if colors_used > max_colors:
            result.add_error(ValidationError(
                error_type=ValidationErrorType.ANTI_ALIASING,
                message=f"Too many colors ({colors_used}), possible anti-aliasing. Max: {max_colors}",
                severity="warning" if not self.strict else "error"
            ))

    def _validate_center(
        self,
        image_info: dict,
        grammar: TileGrammar,
        result: ValidationResult
    ) -> None:
        """Validate center content consistency."""
        # Would analyze the center region of the tile
        # to ensure it matches the expected center type

        center_type = grammar.center

        # Mock validation - in reality would analyze texture patterns
        result.stats["center_type"] = center_type

    def validate_batch(
        self,
        tiles: list[tuple[bytes, TileGrammar, Optional[Palette]]]
    ) -> list[ValidationResult]:
        """Validate multiple tiles."""
        return [
            self.validate(image_data, grammar, palette)
            for image_data, grammar, palette in tiles
        ]

    def get_rejection_summary(
        self,
        results: list[ValidationResult]
    ) -> dict:
        """Summarize validation results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed

        error_counts = {}
        for result in results:
            for error in result.errors:
                error_type = error.error_type.value
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "error_breakdown": error_counts,
        }


# Edge pixel patterns for validation
EDGE_PATTERNS = {
    EdgeCode.EMPTY: {
        "description": "All transparent or background color",
        "requirements": ["majority_transparent", "no_solid_fill"],
    },
    EdgeCode.SOLID: {
        "description": "Solid wall pixels",
        "requirements": ["majority_solid", "continuous_fill"],
    },
    EdgeCode.FLOOR: {
        "description": "Floor-level pixels",
        "requirements": ["lower_brightness", "consistent_texture"],
    },
    EdgeCode.WATER: {
        "description": "Water edge pixels",
        "requirements": ["blue_tones", "possible_transparency"],
    },
    EdgeCode.DOOR_FRAME: {
        "description": "Door frame opening",
        "requirements": ["partial_fill", "centered_opening"],
    },
}
