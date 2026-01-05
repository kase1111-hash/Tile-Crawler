"""
Audio Engine for Tile-Crawler

Generates audio intents for TTS-based procedural sound synthesis.
Works with or without LLM - uses onomatopoeia library for fallback.
"""

import json
import os
import random
from typing import Optional
from pydantic import BaseModel


class AudioIntent(BaseModel):
    """Audio intent to be processed by frontend TTS engine."""
    event_type: str  # sfx, ambient, music_motif, ui_feedback, dialogue, environmental
    onomatopoeia: str  # The text to speak
    emotion: str = "neutral"
    intensity: float = 0.5  # 0.0 to 1.0
    pitch_shift: float = 0.0  # -12 to +12 semitones
    speed: float = 1.0  # 0.5 to 2.0
    reverb: float = 0.3  # 0.0 to 1.0
    style: str = "comic_noir"
    spatial: Optional[dict] = None  # {pan: -1 to 1, distance: 0 to 1}
    loop: bool = False
    priority: int = 5  # 1-10, higher = more important


class AudioBatch(BaseModel):
    """Batch of audio intents for a single game event."""
    primary: AudioIntent
    ambient: Optional[AudioIntent] = None
    music: Optional[AudioIntent] = None
    layers: list[AudioIntent] = []


class AudioEngine:
    """
    Generates audio intents for game events.
    Uses onomatopoeia library for procedural sound generation.
    """

    def __init__(self):
        self.audio_schema = self._load_audio_schema()
        self.onomatopoeia = self.audio_schema.get("onomatopoeia_library", {})
        self.processing_presets = self.audio_schema.get("processing_presets", {})
        self.current_biome = "dungeon"
        self.combat_active = False
        self.tension_level = 0.0  # 0.0 to 1.0

    def _load_audio_schema(self) -> dict:
        """Load the audio schema configuration."""
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        schema_path = os.path.join(data_dir, "audio_schema.json")

        if os.path.exists(schema_path):
            try:
                with open(schema_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load audio_schema.json: {e}")
        return {}

    def _pick_onomatopoeia(self, category: str, subcategory: str) -> str:
        """Pick a random onomatopoeia from the library."""
        try:
            options = self.onomatopoeia.get(category, {}).get(subcategory, [])
            if options:
                return random.choice(options)
        except Exception:
            pass
        return "..."

    def _get_biome_preset(self) -> dict:
        """Get audio processing preset for current biome."""
        biome_mapping = {
            "dungeon": "dungeon",
            "cave": "cave",
            "crypt": "dungeon",
            "ruins": "dungeon",
            "temple": "temple",
            "forest": "forest",
            "volcano": "combat",
            "void": "ethereal"
        }
        preset_name = biome_mapping.get(self.current_biome, "dungeon")
        return self.processing_presets.get(preset_name, {})

    def set_biome(self, biome: str):
        """Update the current biome for audio processing."""
        self.current_biome = biome

    def set_combat_state(self, active: bool):
        """Update combat state for audio mixing."""
        self.combat_active = active

    def set_tension(self, level: float):
        """Update tension level (affects music and ambient)."""
        self.tension_level = max(0.0, min(1.0, level))

    # === Combat Audio ===

    def generate_attack_audio(
        self,
        weapon_type: str = "sword",
        hit: bool = True,
        damage: int = 0,
        critical: bool = False
    ) -> AudioBatch:
        """Generate audio for attack action."""
        preset = self._get_biome_preset()

        if critical:
            sfx = self._pick_onomatopoeia("combat", "critical")
            intensity = 1.0
        elif hit:
            if weapon_type in ["sword", "dagger", "axe"]:
                sfx = self._pick_onomatopoeia("combat", "sword_hit")
            elif weapon_type in ["mace", "club", "hammer"]:
                sfx = self._pick_onomatopoeia("combat", "blunt_hit")
            elif weapon_type in ["bow", "crossbow"]:
                sfx = self._pick_onomatopoeia("combat", "arrow")
            elif weapon_type in ["staff", "wand"]:
                sfx = self._pick_onomatopoeia("combat", "magic_hit")
            else:
                sfx = self._pick_onomatopoeia("combat", "blunt_hit")
            intensity = min(1.0, 0.4 + (damage / 20))
        else:
            sfx = self._pick_onomatopoeia("combat", "miss")
            intensity = 0.3

        primary = AudioIntent(
            event_type="sfx",
            onomatopoeia=sfx,
            emotion="danger" if critical else "tense",
            intensity=intensity,
            pitch_shift=2 if critical else 0,
            speed=1.2 if critical else 1.0,
            reverb=preset.get("reverb", 0.3),
            style="comic_noir",
            priority=8 if critical else 6
        )

        # Combat music motif
        music = AudioIntent(
            event_type="music_motif",
            onomatopoeia=self._pick_onomatopoeia("music_motifs", "combat"),
            emotion="tense",
            intensity=0.6,
            speed=1.0,
            reverb=0.4,
            loop=True,
            priority=3
        )

        return AudioBatch(primary=primary, music=music)

    def generate_enemy_death_audio(self, enemy_name: str) -> AudioBatch:
        """Generate audio for enemy death."""
        sfx = self._pick_onomatopoeia("combat", "death")
        victory_motif = self._pick_onomatopoeia("music_motifs", "victory")

        primary = AudioIntent(
            event_type="sfx",
            onomatopoeia=sfx,
            emotion="triumphant",
            intensity=0.8,
            pitch_shift=-2,
            speed=0.9,
            reverb=0.5,
            priority=7
        )

        music = AudioIntent(
            event_type="music_motif",
            onomatopoeia=victory_motif,
            emotion="triumphant",
            intensity=0.7,
            speed=1.0,
            reverb=0.3,
            priority=5
        )

        return AudioBatch(primary=primary, music=music)

    def generate_player_hurt_audio(self, damage: int, current_hp: int, max_hp: int) -> AudioBatch:
        """Generate audio for player taking damage."""
        hp_ratio = current_hp / max_hp if max_hp > 0 else 0

        if hp_ratio < 0.2:
            sfx = "AAAARGH!"
            emotion = "danger"
            intensity = 1.0
        elif hp_ratio < 0.5:
            sfx = "UNGH!"
            emotion = "danger"
            intensity = 0.7
        else:
            sfx = "OOF!"
            emotion = "tense"
            intensity = 0.5

        primary = AudioIntent(
            event_type="sfx",
            onomatopoeia=sfx,
            emotion=emotion,
            intensity=intensity,
            pitch_shift=-1,
            speed=1.0,
            reverb=0.3,
            priority=8
        )

        # Tension music when low HP
        music = None
        if hp_ratio < 0.3:
            music = AudioIntent(
                event_type="music_motif",
                onomatopoeia=self._pick_onomatopoeia("music_motifs", "tension"),
                emotion="danger",
                intensity=0.8,
                speed=1.2,
                loop=True,
                priority=4
            )

        return AudioBatch(primary=primary, music=music)

    def generate_block_audio(self) -> AudioIntent:
        """Generate audio for blocking an attack."""
        return AudioIntent(
            event_type="sfx",
            onomatopoeia=self._pick_onomatopoeia("combat", "block"),
            emotion="tense",
            intensity=0.6,
            pitch_shift=3,
            speed=1.1,
            reverb=0.4,
            priority=6
        )

    # === Movement Audio ===

    def generate_movement_audio(self, terrain: str = "stone") -> AudioIntent:
        """Generate footstep audio based on terrain."""
        terrain_map = {
            "stone": "footsteps_stone",
            "water": "footsteps_water",
            "wood": "footsteps_wood",
            "floor": "footsteps_stone"
        }

        subcategory = terrain_map.get(terrain, "footsteps_stone")
        sfx = self._pick_onomatopoeia("movement", subcategory)
        preset = self._get_biome_preset()

        return AudioIntent(
            event_type="sfx",
            onomatopoeia=sfx,
            emotion="neutral",
            intensity=0.3,
            speed=1.0,
            reverb=preset.get("reverb", 0.3),
            priority=2
        )

    def generate_door_audio(self, opening: bool = True) -> AudioIntent:
        """Generate door opening/closing audio."""
        if opening:
            sfx = self._pick_onomatopoeia("movement", "door_open")
        else:
            sfx = self._pick_onomatopoeia("movement", "door_close")

        preset = self._get_biome_preset()

        return AudioIntent(
            event_type="sfx",
            onomatopoeia=sfx,
            emotion="mysterious",
            intensity=0.6,
            speed=0.9,
            reverb=preset.get("reverb", 0.5),
            priority=5
        )

    def generate_room_enter_audio(self, room_type: str = "normal") -> AudioBatch:
        """Generate audio for entering a new room."""
        preset = self._get_biome_preset()

        # Primary ambient for the room
        ambient_map = {
            "dungeon": "dungeon",
            "cave": "cave_echo",
            "temple": "temple",
            "forest": "forest"
        }

        ambient_type = ambient_map.get(self.current_biome, "dungeon")
        ambient_sfx = self._pick_onomatopoeia("environment", ambient_type)

        ambient = AudioIntent(
            event_type="ambient",
            onomatopoeia=ambient_sfx,
            emotion="mysterious",
            intensity=0.4,
            speed=0.7,
            reverb=preset.get("reverb", 0.6),
            loop=True,
            priority=1
        )

        # Exploration music
        music = AudioIntent(
            event_type="music_motif",
            onomatopoeia=self._pick_onomatopoeia("music_motifs", "exploration"),
            emotion="mysterious",
            intensity=0.3,
            speed=0.8,
            reverb=0.5,
            loop=True,
            priority=2
        )

        # Door sound as primary
        primary = self.generate_door_audio(opening=True)

        return AudioBatch(primary=primary, ambient=ambient, music=music)

    # === Item Audio ===

    def generate_pickup_audio(self, item_type: str = "item") -> AudioIntent:
        """Generate item pickup audio."""
        if item_type in ["gold", "coin", "coins"]:
            sfx = self._pick_onomatopoeia("items", "pickup_coin")
            emotion = "triumphant"
        else:
            sfx = self._pick_onomatopoeia("items", "pickup_item")
            emotion = "neutral"

        return AudioIntent(
            event_type="sfx",
            onomatopoeia=sfx,
            emotion=emotion,
            intensity=0.5,
            pitch_shift=2,
            speed=1.1,
            reverb=0.2,
            priority=5
        )

    def generate_equip_audio(self) -> AudioIntent:
        """Generate equipment change audio."""
        return AudioIntent(
            event_type="sfx",
            onomatopoeia=self._pick_onomatopoeia("items", "equip"),
            emotion="neutral",
            intensity=0.5,
            speed=1.0,
            reverb=0.2,
            priority=4
        )

    def generate_potion_audio(self) -> AudioIntent:
        """Generate potion drinking audio."""
        return AudioIntent(
            event_type="sfx",
            onomatopoeia=self._pick_onomatopoeia("items", "potion_drink"),
            emotion="peaceful",
            intensity=0.5,
            speed=1.0,
            reverb=0.2,
            priority=5
        )

    def generate_chest_open_audio(self) -> AudioBatch:
        """Generate chest opening audio."""
        primary = AudioIntent(
            event_type="sfx",
            onomatopoeia=self._pick_onomatopoeia("items", "chest_open"),
            emotion="mysterious",
            intensity=0.7,
            speed=0.8,
            reverb=0.4,
            priority=6
        )

        # Mystery music sting
        music = AudioIntent(
            event_type="music_motif",
            onomatopoeia=self._pick_onomatopoeia("music_motifs", "mystery"),
            emotion="mysterious",
            intensity=0.5,
            speed=0.9,
            reverb=0.5,
            priority=4
        )

        return AudioBatch(primary=primary, music=music)

    # === UI Audio ===

    def generate_ui_audio(self, action: str) -> AudioIntent:
        """Generate UI feedback audio."""
        action_map = {
            "open": "menu_open",
            "close": "menu_close",
            "select": "select",
            "confirm": "confirm",
            "cancel": "cancel",
            "error": "error",
            "level_up": "level_up"
        }

        subcategory = action_map.get(action, "select")
        sfx = self._pick_onomatopoeia("ui", subcategory)

        intensity = 0.8 if action == "level_up" else 0.4
        priority = 9 if action == "level_up" else 3

        return AudioIntent(
            event_type="ui_feedback",
            onomatopoeia=sfx,
            emotion="triumphant" if action == "level_up" else "neutral",
            intensity=intensity,
            speed=1.0,
            reverb=0.1,
            priority=priority
        )

    # === NPC Audio ===

    def generate_npc_reaction_audio(self, mood: str) -> AudioIntent:
        """Generate NPC vocal reaction audio."""
        mood_map = {
            "friendly": "greeting",
            "hostile": "angry",
            "surprised": "surprised",
            "sad": "sad",
            "happy": "laugh",
            "farewell": "farewell"
        }

        subcategory = mood_map.get(mood, "greeting")
        sfx = self._pick_onomatopoeia("npc", subcategory)

        return AudioIntent(
            event_type="dialogue",
            onomatopoeia=sfx,
            emotion=mood,
            intensity=0.5,
            speed=1.0,
            reverb=0.3,
            priority=5
        )

    # === Special Events ===

    def generate_discovery_audio(self, discovery_type: str = "lore") -> AudioBatch:
        """Generate audio for discoveries (lore, secrets, etc.)."""
        primary = AudioIntent(
            event_type="sfx",
            onomatopoeia="ooooooh...",
            emotion="mysterious",
            intensity=0.6,
            pitch_shift=-3,
            speed=0.7,
            reverb=0.8,
            priority=6
        )

        music = AudioIntent(
            event_type="music_motif",
            onomatopoeia=self._pick_onomatopoeia("music_motifs", "mystery"),
            emotion="mysterious",
            intensity=0.5,
            speed=0.6,
            reverb=0.7,
            priority=4
        )

        return AudioBatch(primary=primary, music=music)

    def generate_boss_intro_audio(self, boss_name: str) -> AudioBatch:
        """Generate dramatic boss introduction audio."""
        primary = AudioIntent(
            event_type="sfx",
            onomatopoeia="DOOM... DOOM... DOOM...",
            emotion="danger",
            intensity=1.0,
            pitch_shift=-6,
            speed=0.6,
            reverb=0.9,
            priority=10
        )

        music = AudioIntent(
            event_type="music_motif",
            onomatopoeia=self._pick_onomatopoeia("music_motifs", "boss"),
            emotion="epic",
            intensity=1.0,
            speed=0.8,
            reverb=0.6,
            loop=True,
            priority=8
        )

        return AudioBatch(primary=primary, music=music)

    def generate_death_audio(self) -> AudioBatch:
        """Generate player death audio."""
        primary = AudioIntent(
            event_type="sfx",
            onomatopoeia="NOOOOO... thud...",
            emotion="melancholy",
            intensity=0.9,
            pitch_shift=-4,
            speed=0.6,
            reverb=0.8,
            priority=10
        )

        music = AudioIntent(
            event_type="music_motif",
            onomatopoeia=self._pick_onomatopoeia("music_motifs", "defeat"),
            emotion="melancholy",
            intensity=0.7,
            speed=0.5,
            reverb=0.7,
            priority=8
        )

        return AudioBatch(primary=primary, music=music)

    def generate_victory_audio(self) -> AudioBatch:
        """Generate victory/quest complete audio."""
        primary = AudioIntent(
            event_type="sfx",
            onomatopoeia="YESSS!",
            emotion="triumphant",
            intensity=0.9,
            pitch_shift=2,
            speed=1.0,
            reverb=0.4,
            priority=9
        )

        music = AudioIntent(
            event_type="music_motif",
            onomatopoeia=self._pick_onomatopoeia("music_motifs", "victory"),
            emotion="triumphant",
            intensity=1.0,
            speed=1.0,
            reverb=0.4,
            priority=8
        )

        return AudioBatch(primary=primary, music=music)


# Global instance
_audio_engine: Optional[AudioEngine] = None


def get_audio_engine() -> AudioEngine:
    """Get the global audio engine instance."""
    global _audio_engine
    if _audio_engine is None:
        _audio_engine = AudioEngine()
    return _audio_engine
