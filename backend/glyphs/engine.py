"""
Glyph Engine - Integration layer for GASR system.

Provides high-level interface for:
- Room rendering with multiple layers
- Glyph validation and conversion
- Animation management
- LLM context generation
"""

import time
from typing import Optional
from dataclasses import dataclass, field

from .models import (
    Glyph,
    GlyphCategory,
    GlyphPatch,
    GlyphDiff,
    GlyphLayer as LayerEnum,
    Animation,
)
from .registry import GlyphRegistry, get_glyph_registry
from .layers import LayerManager, LayerType
from .legends import LegendCompressor


@dataclass
class AnimationState:
    """Tracks the state of a running animation."""
    animation_id: str
    x: int
    y: int
    layer: LayerType
    current_frame: int = 0
    last_update: float = 0.0
    direction: int = 1  # 1 = forward, -1 = backward (for ping_pong)
    completed: bool = False


class GlyphEngine:
    """
    Main engine for glyph-based rendering and game integration.

    Manages:
    - Multi-layer room rendering
    - Entity/effect placement
    - Animation playback
    - LLM context generation
    """

    def __init__(
        self,
        width: int = 15,
        height: int = 11,
        registry: Optional[GlyphRegistry] = None
    ):
        self.width = width
        self.height = height
        self.registry = registry or get_glyph_registry()
        self.registry.initialize()

        self.layers = LayerManager(width, height)
        self.legend_compressor = LegendCompressor(self.registry)

        # Animation tracking
        self.animations: dict[str, AnimationState] = {}  # key = f"{x},{y},{layer}"

        # Current biome for contextual rendering
        self.current_biome: str = "dungeon"

    def load_room(
        self,
        map_lines: list[str],
        biome: str = "dungeon",
        entities: Optional[list[dict]] = None,
        items: Optional[list[dict]] = None,
        effects: Optional[list[dict]] = None,
    ) -> None:
        """
        Load a room into the layer system.

        Args:
            map_lines: Base map as character strings
            biome: Current biome for glyph variants
            entities: List of entity dicts with {x, y, glyph_id} or {x, y, type}
            items: List of item dicts with {x, y, glyph_id} or {x, y, id}
            effects: List of effect dicts with {x, y, glyph_id}
        """
        self.current_biome = biome
        self.layers.clear_all()
        self.animations.clear()

        # Load base map into background and structure layers
        for y, line in enumerate(map_lines):
            if y >= self.height:
                break
            for x, char in enumerate(line):
                if x >= self.width:
                    break

                glyph = self.registry.get_by_char(char)
                if glyph:
                    # Get biome-specific variant
                    variant = glyph.get_for_biome(biome)
                    layer = self._get_layer_for_glyph(variant)
                    self.layers.set_glyph(
                        x, y, layer,
                        variant.id, variant.char,
                        {"glyph": variant}
                    )

                    # Start animation if applicable
                    if variant.visual.animated and variant.visual.animation_id:
                        self._start_animation(x, y, layer, variant.visual.animation_id)
                else:
                    # Unknown character - place on background
                    self.layers.set_glyph(
                        x, y, LayerType.BACKGROUND,
                        f"unknown.{char}", char
                    )

        # Place entities
        if entities:
            for entity in entities:
                self._place_entity(entity)

        # Place items
        if items:
            for item in items:
                self._place_item(item)

        # Place effects
        if effects:
            for effect in effects:
                self._place_effect(effect)

    def _get_layer_for_glyph(self, glyph: Glyph) -> LayerType:
        """Determine which layer a glyph should render on."""
        layer_value = glyph.visual.layer
        if isinstance(layer_value, int):
            return LayerType(layer_value)
        return LayerType.BACKGROUND

    def _place_entity(self, entity: dict) -> None:
        """Place an entity on the entity layer."""
        x, y = entity.get("x", 0), entity.get("y", 0)

        # Try to resolve glyph
        glyph_id = entity.get("glyph_id")
        if not glyph_id:
            # Infer from entity type
            entity_type = entity.get("type", "enemy")
            if entity_type == "player":
                glyph_id = "entity.player"
            elif entity_type == "boss":
                glyph_id = "entity.enemy.boss"
            elif entity_type == "npc":
                glyph_id = "entity.npc.friendly"
            elif entity_type == "merchant":
                glyph_id = "entity.npc.merchant"
            else:
                glyph_id = "entity.enemy.basic"

        glyph = self.registry.get(glyph_id)
        if glyph:
            self.layers.set_glyph(
                x, y, LayerType.ENTITY,
                glyph.id, glyph.char,
                {"entity": entity, "glyph": glyph}
            )

    def _place_item(self, item: dict) -> None:
        """Place an item on the entity layer."""
        x, y = item.get("x", 0), item.get("y", 0)

        glyph_id = item.get("glyph_id")
        if not glyph_id:
            # Infer from item category or id
            item_id = item.get("id", "coin")
            category = item.get("category", "misc")

            glyph_mapping = {
                "weapon": "item.weapon",
                "armor": "item.armor",
                "potion": "item.potion",
                "consumable": "item.potion",
                "key": "item.key",
                "scroll": "item.scroll",
                "gem": "item.gem",
                "food": "item.food",
            }
            glyph_id = glyph_mapping.get(category, "item.coin")

        glyph = self.registry.get(glyph_id)
        if glyph:
            self.layers.set_glyph(
                x, y, LayerType.ENTITY,
                glyph.id, glyph.char,
                {"item": item, "glyph": glyph}
            )

    def _place_effect(self, effect: dict) -> None:
        """Place an effect on the effect layer."""
        x, y = effect.get("x", 0), effect.get("y", 0)
        glyph_id = effect.get("glyph_id", "effect.magic.sparkle")

        glyph = self.registry.get(glyph_id)
        if glyph:
            self.layers.set_glyph(
                x, y, LayerType.EFFECT,
                glyph.id, glyph.char,
                {"effect": effect, "glyph": glyph}
            )

            if glyph.visual.animated and glyph.visual.animation_id:
                self._start_animation(x, y, LayerType.EFFECT, glyph.visual.animation_id)

    def _start_animation(self, x: int, y: int, layer: LayerType, animation_id: str) -> None:
        """Start an animation at a position."""
        animation = self.registry.get_animation(animation_id)
        if not animation:
            return

        key = f"{x},{y},{layer.value}"
        self.animations[key] = AnimationState(
            animation_id=animation_id,
            x=x,
            y=y,
            layer=layer,
            last_update=time.time()
        )

    def update_animations(self) -> list[tuple[int, int, LayerType, str]]:
        """
        Update all running animations.

        Returns:
            List of (x, y, layer, new_char) for cells that changed
        """
        current_time = time.time()
        changes = []

        for key, state in list(self.animations.items()):
            if state.completed:
                continue

            animation = self.registry.get_animation(state.animation_id)
            if not animation:
                continue

            elapsed = (current_time - state.last_update) * 1000  # to ms
            if elapsed >= animation.rate_ms:
                # Advance frame
                if animation.ping_pong:
                    state.current_frame += state.direction
                    if state.current_frame >= len(animation.frames) - 1:
                        state.direction = -1
                    elif state.current_frame <= 0:
                        state.direction = 1
                else:
                    state.current_frame = (state.current_frame + 1) % len(animation.frames)

                # Check if animation completed (for non-looping)
                if not animation.loop and state.current_frame == len(animation.frames) - 1:
                    state.completed = True

                # Update cell
                frame_codepoint = animation.frames[state.current_frame]
                frame_glyph = self.registry.get_by_codepoint(frame_codepoint)
                if frame_glyph:
                    self.layers.set_glyph(
                        state.x, state.y, state.layer,
                        frame_glyph.id, frame_glyph.char
                    )
                    changes.append((state.x, state.y, state.layer, frame_glyph.char))

                state.last_update = current_time

        return changes

    def apply_patch(self, patch: GlyphPatch) -> bool:
        """
        Apply a single glyph patch.

        Returns:
            True if patch was applied successfully
        """
        glyph = self.registry.get(patch.glyph)
        if not glyph:
            return False

        layer = LayerType(patch.layer) if isinstance(patch.layer, int) else patch.layer

        if patch.op == "replace" or patch.op == "add":
            return self.layers.set_glyph(
                patch.x, patch.y, layer,
                glyph.id, glyph.char,
                {"glyph": glyph}
            )
        elif patch.op == "remove":
            return self.layers.set_glyph(
                patch.x, patch.y, layer,
                "empty.void", " "
            )
        return False

    def apply_diff(self, diff: GlyphDiff) -> int:
        """
        Apply a batch of patches.

        Returns:
            Number of successfully applied patches
        """
        applied = 0
        for patch in diff.patches:
            if self.apply_patch(patch):
                applied += 1
        return applied

    def render(self) -> list[str]:
        """
        Render all layers into final display.

        Returns:
            List of strings representing the composited room
        """
        return self.layers.composite()

    def render_with_ids(self) -> list[list[str]]:
        """
        Render all layers as glyph IDs.

        Returns:
            2D grid of glyph IDs
        """
        return self.layers.composite_ids()

    def get_at(self, x: int, y: int) -> list[Glyph]:
        """
        Get all glyphs at a position across all layers.

        Returns:
            List of Glyph objects from bottom to top
        """
        glyphs = []
        for layer_type, cell in self.layers.get_all_at(x, y):
            glyph = self.registry.get(cell.glyph_id)
            if glyph:
                glyphs.append(glyph)
        return glyphs

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is walkable."""
        glyphs = self.get_at(x, y)
        for glyph in glyphs:
            if glyph.physics.blocks_movement:
                return False
        return True

    def get_damage_at(self, x: int, y: int) -> tuple[int, Optional[str]]:
        """
        Get total damage at position.

        Returns:
            Tuple of (total_damage, damage_type)
        """
        total_damage = 0
        damage_type = None

        for glyph in self.get_at(x, y):
            if glyph.physics.damage_on_enter > 0:
                total_damage += glyph.physics.damage_on_enter
                damage_type = glyph.physics.damage_type

        return total_damage, damage_type

    def set_player_position(self, x: int, y: int) -> None:
        """Update player position on entity layer."""
        # Clear old player position
        entity_layer = self.layers.get_layer(LayerType.ENTITY)
        for row in entity_layer.cells:
            for cell in row:
                if cell.glyph_id == "entity.player":
                    cell.glyph_id = "empty.void"
                    cell.char = " "

        # Set new position
        player_glyph = self.registry.get("entity.player")
        if player_glyph:
            self.layers.set_glyph(
                x, y, LayerType.ENTITY,
                player_glyph.id, player_glyph.char
            )

    def generate_llm_context(
        self,
        include_legend: bool = True,
        include_threats: bool = True,
        include_interests: bool = True
    ) -> str:
        """
        Generate context string for LLM prompts.

        Args:
            include_legend: Include glyph legend
            include_threats: Include threat indicators
            include_interests: Include interest indicators

        Returns:
            Formatted context string
        """
        parts = []

        if include_legend:
            legend = self.legend_compressor.compress_char_legend()
            parts.append(self.legend_compressor.format_legend_for_prompt(legend, "compact"))

        # Add map
        parts.append("Current Room:")
        parts.extend(self.render())

        parts.append(f"Biome: {self.current_biome}")

        if include_threats:
            threats = self._find_threats()
            if threats:
                parts.append("Threats: " + ", ".join(threats))

        if include_interests:
            interests = self._find_interests()
            if interests:
                parts.append("Points of Interest: " + ", ".join(interests))

        return "\n".join(parts)

    def _find_threats(self) -> list[str]:
        """Find high-threat glyphs in current room."""
        threats = []
        for y in range(self.height):
            for x in range(self.width):
                for glyph in self.get_at(x, y):
                    if glyph.llm.threat >= 0.5:
                        threats.append(f"{glyph.llm.summary}@({x},{y})")
        return threats

    def _find_interests(self) -> list[str]:
        """Find interesting glyphs in current room."""
        interests = []
        for y in range(self.height):
            for x in range(self.width):
                for glyph in self.get_at(x, y):
                    if glyph.llm.interest >= 0.5:
                        interests.append(f"{glyph.llm.summary}@({x},{y})")
        return interests

    def validate_map(self, map_lines: list[str]) -> list[tuple[int, int, str]]:
        """
        Validate that all characters in a map are registered glyphs.

        Returns:
            List of (x, y, char) for invalid characters
        """
        return self.registry.validate_map(map_lines)

    def get_glyph_info(self, glyph_id: str) -> Optional[dict]:
        """Get full glyph information as dictionary."""
        glyph = self.registry.get(glyph_id)
        if glyph:
            return glyph.model_dump()
        return None

    def to_dict(self) -> dict:
        """Serialize engine state."""
        return {
            "width": self.width,
            "height": self.height,
            "biome": self.current_biome,
            "layers": self.layers.to_dict(),
            "animations": {
                key: {
                    "animation_id": state.animation_id,
                    "x": state.x,
                    "y": state.y,
                    "layer": state.layer.value,
                    "current_frame": state.current_frame,
                }
                for key, state in self.animations.items()
                if not state.completed
            }
        }

    @classmethod
    def from_dict(cls, data: dict, registry: Optional[GlyphRegistry] = None) -> "GlyphEngine":
        """Deserialize engine state."""
        engine = cls(
            width=data["width"],
            height=data["height"],
            registry=registry
        )
        engine.current_biome = data.get("biome", "dungeon")
        engine.layers = LayerManager.from_dict(data["layers"])

        for key, anim_data in data.get("animations", {}).items():
            engine.animations[key] = AnimationState(
                animation_id=anim_data["animation_id"],
                x=anim_data["x"],
                y=anim_data["y"],
                layer=LayerType(anim_data["layer"]),
                current_frame=anim_data.get("current_frame", 0),
                last_update=time.time()
            )

        return engine
