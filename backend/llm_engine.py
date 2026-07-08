"""
LLM Engine for Tile-Crawler

Handles OpenAI API integration, prompt management, and response parsing
for dynamic content generation.
"""

import json
import os
import logging
from typing import Optional
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from metrics import timed_llm_call
from llm_cache import get_llm_cache, CachedRoom

logger = logging.getLogger(__name__)

load_dotenv()


class RoomGenerationResponse(BaseModel):
    """Expected response structure from room generation."""
    map: list[str]
    description: str
    enemies: list[dict] = []
    items: list[dict] = []
    npcs: list[str] = []
    features: list[str] = []


class DialogueResponse(BaseModel):
    """Expected response structure from NPC dialogue."""
    speech: str
    mood: str = "neutral"
    hints: list[str] = []
    trade_available: bool = False


class CombatNarrationResponse(BaseModel):
    """Expected response structure from combat narration."""
    narration: str
    dramatic_moment: bool = False


class LLMEngine:
    """
    Manages LLM interactions for dynamic content generation.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "ollama")
        self.model = os.getenv("LLM_MODEL", "llama3.2")
        self.base_url = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")

        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        else:
            self.client = None

        # Temperature per context: combat is low (0.5) so damage narration
        # stays coherent; descriptions are high (0.9) for variety since
        # players see dozens of room descriptions per session.
        self.temperatures = {
            "exploration": float(os.getenv("LLM_TEMPERATURE", "0.8")),
            "combat": 0.5,
            "dialogue": 0.8,
            "description": 0.9
        }

        # Load game data for context
        self.game_data = self._load_game_data()

        # System prompt for the dungeon master
        self.system_prompt = """You are the Dungeon Master for Tile-Crawler, an AI-powered roguelike dungeon crawler.

Your role is to:
1. Generate atmospheric, consistent dungeon content
2. Maintain narrative continuity with previous events
3. Create engaging descriptions that fit the dark fantasy tone
4. Output valid JSON matching the requested schema

Guidelines:
- Keep descriptions concise but evocative (2-4 sentences)
- Maintain consistency with the established world and tone
- Reference previous events when relevant
- Create interesting but fair challenges
- Use the tile characters provided for map generation

Tile Characters:
▓ = Wall, ░ = Floor, @ = Player, $ = Item, ☺ = NPC
≈ = Water, ▲ = Mountain, ♣ = Tree, + = Door (closed)
/ = Door (open), > = Stairs down, < = Stairs up
■ = Chest, □ = Open chest, ^ = Trap, ╬ = Altar
& = Enemy, Ω = Boss

Always respond with valid JSON matching the requested format."""

    def _load_game_data(self) -> dict:
        """Load game data files for context."""
        data = {}
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

        files_to_load = ["tiles.json", "npcs.json", "enemies.json", "biomes.json", "items.json"]

        for filename in files_to_load:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        key = filename.replace(".json", "")
                        data[key] = json.load(f)
                except Exception as e:
                    logger.warning("Could not load %s: %s", filename, e)

        # Load biome prompt templates
        prompts_path = os.path.join(os.path.dirname(__file__), "prompts", "biomes.json")
        if os.path.exists(prompts_path):
            try:
                with open(prompts_path, 'r', encoding='utf-8') as f:
                    data["biome_prompts"] = json.load(f)
            except Exception as e:
                logger.warning("Could not load biome prompts: %s", e)

        return data

    def is_available(self) -> bool:
        """Check if the LLM engine is available."""
        return self.client is not None

    @timed_llm_call("generate_room")
    async def generate_room(
        self,
        x: int,
        y: int,
        z: int,
        biome: str,
        exits: dict[str, bool],
        narrative_context: dict,
        inventory_summary: str
    ) -> Optional[RoomGenerationResponse]:
        """
        Generate a new room using the LLM.
        """
        if not self.is_available():
            return self._generate_fallback_room(x, y, z, biome, exits)

        # Check cache — try all enemy/npc variants so we don't exclusively
        # return rooms with enemies (the original code hardcoded True/False)
        cache = get_llm_cache()
        cached = None
        for try_enemies in (True, False):
            for try_npcs in (True, False):
                cached = cache.get(biome, z, has_enemies=try_enemies, has_npcs=try_npcs)
                if cached:
                    break
            if cached:
                break
        if cached:
            logger.info(f"Cache hit for {biome} room at depth {z}")
            return RoomGenerationResponse(
                map=cached.map,
                description=cached.description,
                enemies=cached.enemies,
                items=cached.items,
                npcs=cached.npcs,
                features=cached.features
            )

        # Get biome-specific prompt data
        biome_prompts = self.game_data.get("biome_prompts", {})
        bp = biome_prompts.get(biome, biome_prompts.get("dungeon", {}))

        atmosphere = bp.get("atmosphere", "dark and foreboding")
        tiles = bp.get("tile_vocabulary", {})
        tile_notes = tiles.get("notes", "")
        enemy_archetypes = bp.get("enemy_archetypes", [])
        item_themes = bp.get("item_themes", [])
        arch_vocab = bp.get("architectural_vocabulary", [])
        example_desc = bp.get("example_description", "")

        exits_str = ", ".join([d for d, available in exits.items() if available])

        # Build a biome-aware prompt with few-shot example
        prompt = f"""Generate a {biome} room for the dungeon crawler.

**Location:** ({x}, {y}, floor {z})
**Biome:** {biome}
**Atmosphere:** {atmosphere}
**Architectural elements:** {', '.join(arch_vocab[:4])}
**Available exits:** {exits_str}

**Tile constraints for this biome:**
▓ = Wall, ░ = Floor, @ = Player, & = Enemy, $ = Item, ☺ = NPC
{tiles.get('accent_1', '+')} = {biome}-specific accent, {tiles.get('accent_2', '·')} = secondary accent
> = Stairs down, < = Stairs up
{tile_notes}

**Story context:**
{narrative_context.get('story_summary', 'A brave adventurer explores the depths.')}

**Recent events:**
{chr(10).join(narrative_context.get('recent_events', ['- Just entered the dungeon']))}

**Player inventory:** {inventory_summary}

**Example response for a {biome} room:**
```json
{{"map": ["▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓", "▓░░░░░░░░░░░░░▓", "▓░░░░░░░░░░░░░▓", "▓░░░░░░░░░░░░░▓", "▓░░░░░@░░░░░░░▓", "▓░░░░░░░░░░░░░▓", "▓░░░░░░░░░░░░░▓", "▓░░░░░░░░░░░░░▓", "▓░░░░░░░░░░░░░▓", "▓░░░░░░░░░░░░░▓", "▓▓▓▓▓▓▓ ▓▓▓▓▓▓▓"], "description": "{example_desc}", "enemies": [], "items": [], "npcs": [], "features": ["torch_sconce"]}}
```

**Generate a JSON response with:**
- "map": 11-row array of 15-char strings using the tile characters above
- "description": Atmospheric 2-3 sentence {biome} description
- "enemies": 0-2 enemy objects with "id", "name", "hp", "attack" (use: {', '.join(enemy_archetypes[:3])})
- "items": 0-2 item objects with "id", "name" (themes: {', '.join(item_themes[:3])})
- "npcs": Array of NPC IDs (rare, ~10% chance)
- "features": Notable features matching {biome} atmosphere

**Rules:**
- Place @ near the entrance, & for enemies, $ for items
- Mark exits with spaces in walls at row/column midpoints
- Each map row must be exactly 15 characters
- Match the {biome} atmosphere and architectural style"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperatures["exploration"],
                max_tokens=800,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content

            # Parse JSON with error handling
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"LLM returned invalid JSON: {e}")
                return self._generate_fallback_room(x, y, z, biome, exits)

            # Validate response structure with Pydantic
            try:
                result = RoomGenerationResponse.model_validate(data)
                # Store in cache for future reuse
                cache.put(biome, z, CachedRoom(
                    biome=biome,
                    depth_range=str(z),
                    map=result.map,
                    description=result.description,
                    enemies=result.enemies,
                    items=result.items,
                    npcs=result.npcs,
                    features=result.features
                ))
                return result
            except ValidationError as e:
                logger.warning(f"LLM response failed schema validation: {e}")
                return self._generate_fallback_room(x, y, z, biome, exits)

        except Exception as e:
            logger.error(f"LLM room generation failed: {e}")
            return self._generate_fallback_room(x, y, z, biome, exits)

    def _generate_fallback_room(
        self,
        x: int,
        y: int,
        z: int,
        biome: str,
        exits: dict[str, bool]
    ) -> RoomGenerationResponse:
        """Generate a varied room without LLM using templates and data files."""
        import random

        templates = self._load_room_templates()
        template = self._pick_template(templates, x, y, z, biome, exits)

        # Build the map from template or generate procedurally
        room_map = self._build_fallback_map(template, exits, biome)

        # Pick a description
        description = self._pick_description(template, biome)

        # Spawn enemies based on biome and depth
        enemies = self._spawn_fallback_enemies(biome, z)

        # Spawn items
        items = self._spawn_fallback_items(biome, z)

        # Determine features
        features = self._pick_features(template, biome)

        # Place entities on the map
        room_map = self._place_entities_on_map(room_map, enemies, items)

        return RoomGenerationResponse(
            map=room_map,
            description=description,
            enemies=enemies,
            items=items,
            npcs=[],
            features=features
        )

    def _load_room_templates(self) -> dict:
        """Load room templates from data file (cached on game_data)."""
        if "room_templates" not in self.game_data:
            data_path = os.path.join(os.path.dirname(__file__), "..", "data", "room_templates.json")
            if os.path.exists(data_path):
                try:
                    with open(data_path, 'r', encoding='utf-8') as f:
                        self.game_data["room_templates"] = json.load(f)
                except Exception:
                    self.game_data["room_templates"] = {}
            else:
                self.game_data["room_templates"] = {}
        return self.game_data["room_templates"]

    def _pick_template(self, templates: dict, x: int, y: int, z: int, biome: str, exits: dict) -> Optional[dict]:
        """Pick a room template appropriate for the context."""
        import random

        all_templates = templates.get("templates", {})
        if not all_templates:
            return None

        rules = templates.get("procedural_rules", {})
        exit_count = sum(1 for v in exits.values() if v)

        # Filter candidates by context
        candidates = []
        for tid, tmpl in all_templates.items():
            # Skip boss rooms unless deep enough
            if tmpl.get("boss_room") and z < rules.get("boss_room_depth_minimum", 5):
                continue
            # Safe rooms only every N rooms (use coordinate hash as proxy)
            if tmpl.get("safe_room") and tid == "safe_room":
                freq = rules.get("safe_room_frequency", 8)
                if (abs(x) + abs(y) + z) % freq != 0:
                    continue
            # Prefer templates whose exit count roughly matches
            tmpl_exits = sum(1 for v in tmpl.get("exits", {}).values() if v)
            if abs(tmpl_exits - exit_count) <= 2:
                candidates.append(tmpl)

        if not candidates:
            # Fall back to basic templates
            for tid in ["basic_corridor", "crossroads", "entrance_chamber"]:
                if tid in all_templates:
                    candidates.append(all_templates[tid])

        return random.choice(candidates) if candidates else None

    def _build_fallback_map(self, template: Optional[dict], exits: dict, biome: str) -> list[str]:
        """Build a room map from a template, adapting exits."""
        import random

        if template and "map" in template:
            base_map = [list(row) for row in template["map"]]
        else:
            # Generate a procedural room
            base_map = self._generate_procedural_map(biome)

        rows = len(base_map)
        cols = len(base_map[0]) if rows > 0 else 15

        # Ensure exits match the requested ones
        mid_col = cols // 2
        mid_row = rows // 2

        # North exit
        if exits.get("north") and rows > 0:
            base_map[0][mid_col] = " "
        elif not exits.get("north") and rows > 0 and base_map[0][mid_col] == " ":
            base_map[0][mid_col] = "▓"

        # South exit
        if exits.get("south") and rows > 0:
            base_map[rows - 1][mid_col] = " "
        elif not exits.get("south") and rows > 0 and base_map[rows - 1][mid_col] == " ":
            base_map[rows - 1][mid_col] = "▓"

        # East exit
        if exits.get("east"):
            base_map[mid_row][cols - 1] = " "
        elif base_map[mid_row][cols - 1] == " ":
            base_map[mid_row][cols - 1] = "▓"

        # West exit
        if exits.get("west"):
            base_map[mid_row][0] = " "
        elif base_map[mid_row][0] == " ":
            base_map[mid_row][0] = "▓"

        # Down stairs
        if exits.get("down"):
            # Place > on a floor tile near center
            for dy in range(3):
                ry = mid_row + dy
                if 0 < ry < rows - 1 and base_map[ry][mid_col] == "░":
                    base_map[ry][mid_col] = ">"
                    break

        # Up stairs
        if exits.get("up"):
            for dy in range(3):
                ry = mid_row - dy
                if 0 < ry < rows - 1 and base_map[ry][mid_col] == "░":
                    base_map[ry][mid_col] = "<"
                    break

        # Apply biome-specific tile variants
        base_map = self._apply_biome_tiles(base_map, biome)

        return ["".join(row) for row in base_map]

    def _generate_procedural_map(self, biome: str) -> list[list[str]]:
        """Generate a simple procedural room map."""
        import random

        # Vary room size
        width = random.choice([11, 13, 15])
        height = random.choice([9, 11])

        room = []
        for y in range(height):
            row = []
            for x in range(width):
                if y == 0 or y == height - 1 or x == 0 or x == width - 1:
                    row.append("▓")
                else:
                    row.append("░")
            room.append(row)

        # Add 1-3 random features (pillars, water, debris)
        features_chars = {
            "dungeon": ["▓", "╬"],
            "cave": ["▓", "≈"],
            "crypt": ["╬", "▓"],
            "ruins": ["▓", "░"],
            "temple": ["╬", "╬"],
            "volcano": ["≈", "▓"],
            "void": ["░", "░"],
        }
        feature_set = features_chars.get(biome, ["▓"])

        num_features = random.randint(1, 3)
        for _ in range(num_features):
            fx = random.randint(2, width - 3)
            fy = random.randint(2, height - 3)
            room[fy][fx] = random.choice(feature_set)

        return room

    def _apply_biome_tiles(self, room_map: list[list[str]], biome: str) -> list[list[str]]:
        """Apply biome-specific tile substitutions for variety."""
        import random

        biome_floor = {
            "cave": ("░", "·"),
            "volcano": ("░", "~"),
        }

        if biome in biome_floor:
            base, variant = biome_floor[biome]
            for y, row in enumerate(room_map):
                for x, ch in enumerate(row):
                    if ch == base and random.random() < 0.1:
                        room_map[y][x] = variant

        return room_map

    def _pick_description(self, template: Optional[dict], biome: str) -> str:
        """Pick a room description from template hooks or biome defaults."""
        import random

        if template and template.get("narrative_hooks"):
            return random.choice(template["narrative_hooks"])

        descriptions = [
            # Each biome has multiple descriptions for variety
            {"dungeon": [
                "A cold stone chamber stretches before you. Ancient dust covers the floor.",
                "Rough-hewn walls press in on either side. Water seeps through cracks in the ceiling.",
                "Rusted sconces line the walls, their torches long extinguished. The air smells of iron.",
            ]},
            {"cave": [
                "Stalactites drip overhead in this natural cavern. The air is damp.",
                "The cave opens into a wide grotto. Phosphorescent moss clings to the walls.",
                "Dripping water echoes through a low-ceilinged cavern. Something scuttles in the dark.",
            ]},
            {"crypt": [
                "Tombs line the walls of this burial chamber. The dead rest uneasily here.",
                "Stone sarcophagi stand in ordered rows. The air is thick with the scent of decay.",
                "Cobwebs veil the alcoves where the dead were laid to rest. Some alcoves are empty.",
            ]},
            {"ruins": [
                "Crumbling walls hint at former grandeur. Nature reclaims what was lost.",
                "Broken columns jut from the rubble like fractured bones. The sky is visible through gaps above.",
                "Weathered carvings adorn the fallen stones. This place was once beautiful.",
            ]},
            {"temple": [
                "Corrupted symbols cover the walls. Dark power lingers in the air.",
                "An unholy hush fills this profane hall. The altar at its center pulses faintly.",
                "Faded murals depict rituals best left forgotten. The floor is stained dark.",
            ]},
            {"volcano": [
                "Heat radiates from every surface. Lava glows in the distance.",
                "The rock beneath your feet is warm to the touch. Sulfurous fumes sting your eyes.",
                "Rivers of molten stone cast everything in an angry orange glow.",
            ]},
            {"void": [
                "Reality seems uncertain here. The darkness between worlds surrounds you.",
                "The geometry of this place defies logic. Walls bend where they shouldn't.",
                "Whispers emanate from nowhere. The void watches you back.",
            ]},
        ]

        for d in descriptions:
            if biome in d:
                return random.choice(d[biome])

        return "You enter a new area. The dungeon stretches on."

    def _spawn_fallback_enemies(self, biome: str, depth: int) -> list[dict]:
        """Spawn enemies appropriate for the biome and depth."""
        import random

        enemies_data = self.game_data.get("enemies", {}).get("enemies", {})
        if not enemies_data:
            return []

        # 55% chance of no enemies — with combat auto-starting on room entry,
        # much above ~45% enemy rooms turns exploration into a fight gauntlet
        if random.random() < 0.55:
            return []

        # Filter enemies by biome
        candidates = []
        for eid, edata in enemies_data.items():
            spawn_biomes = edata.get("spawn_biomes", [])
            if biome in spawn_biomes or "any" in spawn_biomes:
                # Filter by tier based on depth
                tier = edata.get("tier", "common")
                if depth <= 2 and tier in ("boss", "legendary", "elite"):
                    continue
                if depth <= 5 and tier in ("boss", "legendary"):
                    continue
                candidates.append(edata)

        if not candidates:
            return []

        # Pick 1 enemy (rarely 2)
        count = 1 if random.random() < 0.8 else 2
        spawned = []
        for _ in range(min(count, len(candidates))):
            enemy = random.choice(candidates)
            stats = enemy.get("stats", {})
            spawned.append({
                "id": enemy["id"],
                "name": enemy["name"],
                "hp": stats.get("hp", 20),
                "attack": stats.get("attack", 5),
                "defense": stats.get("defense", 2),
            })

        return spawned

    def _spawn_fallback_items(self, biome: str, depth: int) -> list[dict]:
        """Spawn items appropriate for the context."""
        import random

        items_data = self.game_data.get("items", {}) if "items" in self.game_data else {}
        if not items_data:
            # Load items data
            data_path = os.path.join(os.path.dirname(__file__), "..", "data", "items.json")
            if os.path.exists(data_path):
                try:
                    with open(data_path, 'r', encoding='utf-8') as f:
                        items_data = json.load(f)
                        self.game_data["items"] = items_data
                except Exception:
                    return []

        all_items = items_data.get("items", {})
        if not all_items:
            return []

        # 60% chance of no items
        if random.random() < 0.6:
            return []

        # Weight by rarity
        rarity_weights = {"common": 60, "uncommon": 25, "rare": 10, "epic": 4, "legendary": 1}

        # Filter to consumables and basic equipment for floor loot
        candidates = []
        for iid, idata in all_items.items():
            category = idata.get("category", "")
            if category in ("consumable", "tool", "scroll", "treasure"):
                rarity = idata.get("rarity", "common")
                weight = rarity_weights.get(rarity, 1)
                # Higher depth increases chance of better items slightly
                if depth > 3:
                    weight = max(1, weight + depth)
                candidates.append((idata, weight))

        if not candidates:
            return []

        # Weighted random selection
        total_weight = sum(w for _, w in candidates)
        roll = random.uniform(0, total_weight)
        cumulative = 0
        chosen = candidates[0][0]
        for item, weight in candidates:
            cumulative += weight
            if roll <= cumulative:
                chosen = item
                break

        return [{
            "id": chosen["id"],
            "name": chosen["name"],
            "quantity": 1
        }]

    def _place_entities_on_map(self, room_map: list[str], enemies: list[dict], items: list[dict]) -> list[str]:
        """Place enemy (&) and item ($) markers on floor tiles."""
        import random

        grid = [list(row) for row in room_map]
        rows = len(grid)
        cols = len(grid[0]) if rows > 0 else 0

        # Find floor tiles
        floor_tiles = []
        for y in range(1, rows - 1):
            for x in range(1, cols - 1):
                if grid[y][x] == "░":
                    floor_tiles.append((x, y))

        if not floor_tiles:
            return room_map

        random.shuffle(floor_tiles)
        idx = 0

        # Place enemies
        for _ in enemies:
            if idx < len(floor_tiles):
                ex, ey = floor_tiles[idx]
                grid[ey][ex] = "&"
                idx += 1

        # Place items
        for _ in items:
            if idx < len(floor_tiles):
                ix, iy = floor_tiles[idx]
                grid[iy][ix] = "$"
                idx += 1

        return ["".join(row) for row in grid]

    def _pick_features(self, template: Optional[dict], biome: str) -> list[str]:
        """Pick room features from template or biome defaults."""
        import random

        if template and template.get("features"):
            return template["features"]

        biome_features = {
            "dungeon": [["torch_sconce"], ["cobwebs", "torch_sconce"], ["iron_grate", "blood_stains"], ["cracked_wall"]],
            "cave": [["stalagmites"], ["mushroom_patch"], ["water_pool"], ["crystal_formation"]],
            "crypt": [["sarcophagus"], ["funeral_urns"], ["bone_pile", "cobwebs"], ["inscription"]],
            "ruins": [["fallen_pillar"], ["overgrown_vines"], ["cracked_mosaic"], ["broken_statue"]],
            "temple": [["altar"], ["candles"], ["prayer_stones"], ["dark_sigils"]],
            "volcano": [["lava_vent"], ["obsidian_formation"], ["heat_shimmer"], ["sulfur_deposit"]],
            "void": [["reality_crack"], ["floating_debris"], ["whispering_shadows"], ["null_zone"]],
        }

        options = biome_features.get(biome, [["torch_sconce"]])
        return random.choice(options)

    @timed_llm_call("generate_dialogue")
    async def generate_dialogue(
        self,
        npc_id: str,
        npc_name: str,
        personality: str,
        player_input: str,
        narrative_context: dict,
        dialogue_history: list[str]
    ) -> DialogueResponse:
        """Generate NPC dialogue response."""
        if not self.is_available():
            return DialogueResponse(
                speech=f"{npc_name} regards you silently.",
                mood="neutral"
            )

        npc_data = self.game_data.get("npcs", {}).get("npcs", {}).get(npc_id, {})
        personality_data = self.game_data.get("npcs", {}).get("personalities", {}).get(personality, {})

        history_str = "\n".join(dialogue_history[-5:]) if dialogue_history else "No previous conversation."

        prompt = f"""Generate dialogue for an NPC in the dungeon crawler.

NPC: {npc_name}
Personality: {personality} - {personality_data.get('tone', 'neutral')}
Traits: {personality_data.get('traits', [])}

Previous dialogue:
{history_str}

Player says: "{player_input}"

Story context: {narrative_context.get('story_summary', '')}

Respond with JSON:
- "speech": The NPC's spoken response (1-3 sentences, in character)
- "mood": Current mood (friendly, suspicious, helpful, cryptic, etc.)
- "hints": Array of subtle hints the NPC might give (0-2)
- "trade_available": Boolean if NPC offers trade"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperatures["dialogue"],
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content

            # Parse JSON with error handling
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"LLM returned invalid JSON for dialogue: {e}")
                return DialogueResponse(
                    speech=f"{npc_name} nods thoughtfully but says nothing.",
                    mood="neutral"
                )

            # Validate response structure
            try:
                return DialogueResponse.model_validate(data)
            except ValidationError as e:
                logger.warning(f"LLM dialogue response failed validation: {e}")
                return DialogueResponse(
                    speech=f"{npc_name} nods thoughtfully but says nothing.",
                    mood="neutral"
                )

        except Exception as e:
            logger.error(f"LLM dialogue generation failed: {e}")
            return DialogueResponse(
                speech=f"{npc_name} nods thoughtfully but says nothing.",
                mood="neutral"
            )

    @timed_llm_call("generate_combat_narration")
    async def generate_combat_narration(
        self,
        player_action: str,
        enemy_name: str,
        outcome: str,
        player_stats: dict,
        enemy_stats: dict,
        is_victory: bool,
        is_defeat: bool
    ) -> CombatNarrationResponse:
        """Generate dramatic combat narration."""
        if not self.is_available():
            return CombatNarrationResponse(
                narration=f"You {player_action} the {enemy_name}. {outcome}",
                dramatic_moment=is_victory or is_defeat
            )

        prompt = f"""Generate dramatic combat narration for the dungeon crawler.

Player action: {player_action}
Enemy: {enemy_name}
Outcome: {outcome}
Player HP: {player_stats.get('hp')}/{player_stats.get('max_hp')}
Enemy HP: {enemy_stats.get('hp', 0)}/{enemy_stats.get('max_hp', 0)}
Victory: {is_victory}
Defeat: {is_defeat}

Respond with JSON:
- "narration": Dramatic 1-2 sentence combat description
- "dramatic_moment": Boolean for especially intense moments"""

        fallback_response = CombatNarrationResponse(
            narration=f"You {player_action} the {enemy_name}. {outcome}",
            dramatic_moment=is_victory or is_defeat
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperatures["combat"],
                max_tokens=150,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content

            # Parse JSON with error handling
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                logger.warning(f"LLM returned invalid JSON for combat: {e}")
                return fallback_response

            # Validate response structure
            try:
                return CombatNarrationResponse.model_validate(data)
            except ValidationError as e:
                logger.warning(f"LLM combat response failed validation: {e}")
                return fallback_response

        except Exception as e:
            logger.error(f"LLM combat narration failed: {e}")
            return fallback_response

    @timed_llm_call("generate_item_description")
    async def generate_item_description(
        self,
        item_id: str,
        item_name: str,
        context: str
    ) -> str:
        """Generate a contextual item description."""
        if not self.is_available():
            return f"You examine the {item_name}."

        prompt = f"""Generate a brief item examination description.

Item: {item_name} (ID: {item_id})
Context: {context}

Respond with JSON:
- "description": A 1-2 sentence atmospheric description of examining/finding the item"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperatures["description"],
                max_tokens=100,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            return data.get("description", f"You examine the {item_name}.")

        except Exception as e:
            logger.error("LLM item description failed: %s", e)
            return f"You examine the {item_name}."

    @timed_llm_call("summarize_story")
    async def summarize_story(
        self,
        events: list[str],
        current_summary: str
    ) -> str:
        """Generate an updated story summary from events."""
        if not self.is_available():
            return current_summary

        prompt = f"""Update the story summary for the dungeon crawler.

Current summary:
{current_summary}

Recent events:
{chr(10).join(events)}

Respond with JSON:
- "summary": An updated 2-3 sentence summary of the adventure so far"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=150,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            data = json.loads(content)
            return data.get("summary", current_summary)

        except Exception as e:
            logger.error("LLM story summary failed: %s", e)
            return current_summary


# Global instance
_llm_engine: Optional[LLMEngine] = None


def get_llm_engine() -> LLMEngine:
    """Get the global LLM engine instance."""
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LLMEngine()
    return _llm_engine
