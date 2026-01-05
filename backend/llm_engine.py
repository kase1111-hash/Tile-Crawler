"""
LLM Engine for Tile-Crawler

Handles OpenAI API integration, prompt management, and response parsing
for dynamic content generation.
"""

import json
import os
import re
from typing import Optional
from openai import AsyncOpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

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

        # Temperature settings for different contexts
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

        files_to_load = ["tiles.json", "npcs.json", "enemies.json", "biomes.json"]

        for filename in files_to_load:
            filepath = os.path.join(data_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        key = filename.replace(".json", "")
                        data[key] = json.load(f)
                except Exception as e:
                    print(f"Warning: Could not load {filename}: {e}")

        return data

    def is_available(self) -> bool:
        """Check if the LLM engine is available."""
        return self.client is not None

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

        # Get biome data for context
        biome_data = self.game_data.get("biomes", {}).get("biomes", {}).get(biome, {})
        biome_atmosphere = biome_data.get("atmosphere", {})
        biome_enemies = biome_data.get("common_enemies", [])
        biome_items = biome_data.get("common_items", [])

        # Build the prompt
        exits_str = ", ".join([d for d, available in exits.items() if available])

        prompt = f"""Generate a room for the dungeon crawler game.

Location: ({x}, {y}, floor {z})
Biome: {biome}
Available exits: {exits_str}
Atmosphere: {biome_atmosphere}

Story context:
{narrative_context.get('story_summary', 'A brave adventurer explores the depths.')}

Recent events:
{chr(10).join(narrative_context.get('recent_events', ['- Just entered the dungeon']))}

Player inventory:
{inventory_summary}

Generate a JSON response with:
- "map": Array of strings forming an 11x15 character grid using the tile characters
- "description": Atmospheric 2-3 sentence room description
- "enemies": Array of enemy objects with "id", "name", "hp", "attack" (0-2 enemies, use {biome_enemies})
- "items": Array of item objects with "id", "name" (0-2 items, use {biome_items})
- "npcs": Array of NPC IDs if any are present (rare, maybe 10% chance)
- "features": Array of notable features like "torch_sconce", "ancient_pillar", "blood_stains"

Rules:
- Player (@) should be placed near the entrance
- Mark exits with spaces in the walls
- Place enemies (&) and items ($) appropriately
- Keep it interesting but not overwhelming
- Match the {biome} atmosphere"""

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
            data = json.loads(content)

            return RoomGenerationResponse(**data)

        except Exception as e:
            print(f"LLM room generation failed: {e}")
            return self._generate_fallback_room(x, y, z, biome, exits)

    def _generate_fallback_room(
        self,
        x: int,
        y: int,
        z: int,
        biome: str,
        exits: dict[str, bool]
    ) -> RoomGenerationResponse:
        """Generate a basic room without LLM."""
        # Basic room template
        room_map = [
            "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓",
            "▓░░░░░░░░░░░░░▓",
            "▓░░░░░░░░░░░░░▓",
            "▓░░░░░░░░░░░░░▓",
            "▓░░░░░░░░░░░░░▓",
            "▓░░░░░@░░░░░░░▓",
            "▓░░░░░░░░░░░░░▓",
            "▓░░░░░░░░░░░░░▓",
            "▓░░░░░░░░░░░░░▓",
            "▓░░░░░░░░░░░░░▓",
            "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"
        ]

        # Add exits
        room_map = [list(row) for row in room_map]
        if exits.get("north"):
            room_map[0][7] = " "
        if exits.get("south"):
            room_map[10][7] = " "
        if exits.get("east"):
            room_map[5][14] = " "
        if exits.get("west"):
            room_map[5][0] = " "
        room_map = ["".join(row) for row in room_map]

        descriptions = {
            "dungeon": "A cold stone chamber stretches before you. Ancient dust covers the floor.",
            "cave": "Stalactites drip overhead in this natural cavern. The air is damp.",
            "crypt": "Tombs line the walls of this burial chamber. The dead rest uneasily here.",
            "ruins": "Crumbling walls hint at former grandeur. Nature reclaims what was lost.",
            "temple": "Corrupted symbols cover the walls. Dark power lingers in the air.",
            "forest": "Twisted trees form walls of wood and shadow. The path ahead is unclear.",
            "volcano": "Heat radiates from every surface. Lava glows in the distance.",
            "void": "Reality seems uncertain here. The darkness between worlds surrounds you."
        }

        return RoomGenerationResponse(
            map=room_map,
            description=descriptions.get(biome, descriptions["dungeon"]),
            enemies=[],
            items=[],
            npcs=[],
            features=["torch_sconce"]
        )

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
            data = json.loads(content)
            return DialogueResponse(**data)

        except Exception as e:
            print(f"LLM dialogue generation failed: {e}")
            return DialogueResponse(
                speech=f"{npc_name} nods thoughtfully but says nothing.",
                mood="neutral"
            )

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
            data = json.loads(content)
            return CombatNarrationResponse(**data)

        except Exception as e:
            print(f"LLM combat narration failed: {e}")
            return CombatNarrationResponse(
                narration=f"You {player_action} the {enemy_name}. {outcome}",
                dramatic_moment=is_victory or is_defeat
            )

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
            print(f"LLM item description failed: {e}")
            return f"You examine the {item_name}."

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
            print(f"LLM story summary failed: {e}")
            return current_summary


# Global instance
_llm_engine: Optional[LLMEngine] = None


def get_llm_engine() -> LLMEngine:
    """Get the global LLM engine instance."""
    global _llm_engine
    if _llm_engine is None:
        _llm_engine = LLMEngine()
    return _llm_engine
