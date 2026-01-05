# LLM Intelligence Layer Design Document

## Overview

The LLM Intelligence Layer is the cognitive core of Tile-Crawler, providing dynamic content generation, narrative continuity, NPC behavior, and adaptive gameplay. It transforms the game from a static dungeon crawler into a living, responsive world.

## Core Responsibilities

1. **Dynamic Content Generation:** Create rooms, descriptions, and events
2. **Narrative Management:** Maintain story continuity and tone
3. **NPC Intelligence:** Drive character behavior and dialogue
4. **Adaptive Difficulty:** Adjust challenges based on player performance
5. **Quest Generation:** Create dynamic objectives and storylines

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Intelligence Layer                        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Context Manager                        │   │
│  │  (Assembles prompts from game state, memory, history)   │   │
│  └───────────────────────────┬─────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────┬────────────┼────────────┬──────────────────┐  │
│  │              │            │            │                  │  │
│  ▼              ▼            ▼            ▼                  │  │
│ ┌────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ │  │
│ │Content │ │Narrative│ │  NPC    │ │ Quest    │ │ Combat  │ │  │
│ │Gen     │ │Manager  │ │ Brain   │ │ Engine   │ │ Narrator│ │  │
│ └────────┘ └─────────┘ └─────────┘ └──────────┘ └─────────┘ │  │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    LLM API Interface                     │   │
│  │  (Request batching, caching, fallback handling)         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│                     [OpenAI / Anthropic API]                    │
└─────────────────────────────────────────────────────────────────┘
```

## Context Management

### Context Window Optimization

Managing the limited context window effectively:

```python
class ContextManager:
    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens

    def build_context(
        self,
        game_state: GameState,
        narrative_memory: NarrativeMemory,
        current_request: str
    ) -> str:
        context_parts = []

        # Priority 1: System prompt (always included)
        context_parts.append(self.get_system_prompt())

        # Priority 2: Current game state
        context_parts.append(self.summarize_state(game_state))

        # Priority 3: Recent narrative (last N events)
        context_parts.append(self.get_recent_narrative(narrative_memory))

        # Priority 4: Relevant historical context
        remaining_tokens = self.calculate_remaining(context_parts)
        context_parts.append(
            self.get_relevant_history(narrative_memory, remaining_tokens)
        )

        # Priority 5: Current request
        context_parts.append(current_request)

        return self.join_context(context_parts)
```

### Memory Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                      Memory Hierarchy                            │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Immediate Context (Always in prompt)                    │   │
│  │  - Current room state                                    │   │
│  │  - Player status                                         │   │
│  │  - Active NPCs                                           │   │
│  │  - Last 3 player actions                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Short-term Memory (Rolling window)                      │   │
│  │  - Last 10 narrative events                              │   │
│  │  - Recent NPC interactions                               │   │
│  │  - Current quest progress                                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Long-term Memory (Summarized, retrieved as needed)      │   │
│  │  - Major story events                                    │   │
│  │  - NPC relationship history                              │   │
│  │  - Completed quests                                      │   │
│  │  - World changes                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Prompt Engineering

### System Prompt Structure

```python
SYSTEM_PROMPT = """
You are the Game Master for Tile-Crawler, a text-based dungeon crawler.

Your responsibilities:
1. Generate atmospheric room descriptions
2. Control NPC dialogue and behavior
3. Narrate combat and events
4. Maintain story continuity
5. Create engaging, coherent content

Style guidelines:
- Write in second person ("You enter...")
- Keep descriptions concise (2-4 sentences)
- Maintain a {tone} atmosphere
- Reference previous events when relevant
- Include sensory details (sight, sound, smell)

Output format:
Return JSON with the structure defined in each request.
Never break character or reference being an AI.
"""
```

### Request Templates

#### Room Generation

```python
ROOM_GENERATION_PROMPT = """
Generate content for a new room.

Current state:
- Player entered from: {entry_direction}
- Zone: {zone_name} ({biome})
- Difficulty: {difficulty}/10
- Player stats: HP {hp}/{max_hp}, Level {level}
- Inventory includes: {key_items}

Narrative context:
{narrative_summary}

Generate a room with:
1. Tilemap (10x10 grid using standard characters)
2. Description (2-3 atmospheric sentences)
3. Items (0-3 items appropriate to zone)
4. NPCs (0-1 NPCs with personality)
5. Exits (1-4 directions)

Return as JSON:
{
  "map": ["row1", "row2", ...],
  "description": "...",
  "items": [{"id": "...", "name": "...", "description": "..."}],
  "npcs": [{"id": "...", "name": "...", "personality": "...", "dialogue_hook": "..."}],
  "exits": ["north", "east"]
}
"""
```

#### NPC Dialogue

```python
NPC_DIALOGUE_PROMPT = """
Generate dialogue for NPC interaction.

NPC Profile:
- Name: {npc_name}
- Role: {npc_role}
- Personality: {personality}
- Previous interactions: {interaction_history}
- Knows about: {knowledge}

Current situation:
- Location: {location}
- Player action: {player_action}
- Relevant items: {relevant_items}

Conversation history:
{dialogue_history}

Generate the NPC's response. Include:
1. Dialogue text (in character)
2. Emotional state
3. Any items offered/requested
4. Hints or quest information (if appropriate)

Return as JSON:
{
  "dialogue": "...",
  "emotion": "friendly/hostile/nervous/etc",
  "offers": [],
  "hints": [],
  "quest_update": null
}
"""
```

## Response Parsing

### Structured Output Handling

```python
class LLMResponseParser:
    def parse_room_response(self, response: str) -> RoomData:
        try:
            data = json.loads(response)
            return RoomData(
                tilemap=self.validate_tilemap(data['map']),
                description=data['description'],
                items=self.parse_items(data.get('items', [])),
                npcs=self.parse_npcs(data.get('npcs', [])),
                exits=data.get('exits', [])
            )
        except (json.JSONDecodeError, KeyError) as e:
            return self.generate_fallback_room()

    def validate_tilemap(self, tilemap: List[str]) -> List[str]:
        """Ensure tilemap is valid and properly formatted"""
        validated = []
        for row in tilemap:
            # Ensure consistent width
            row = row[:10].ljust(10, '░')
            # Replace invalid characters
            row = ''.join(c if c in VALID_TILES else '░' for c in row)
            validated.append(row)
        return validated
```

### Fallback Handling

```python
class FallbackGenerator:
    """Generate content when LLM fails or is unavailable"""

    def generate_room(self, zone: str, difficulty: int) -> RoomData:
        """Procedural fallback for room generation"""
        template = self.room_templates[zone]
        return RoomData(
            tilemap=template.generate_layout(),
            description=random.choice(template.descriptions),
            items=template.generate_items(difficulty),
            npcs=[],
            exits=template.generate_exits()
        )
```

## Caching Strategy

### Response Caching

```python
class LLMCache:
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size

    def get_cache_key(self, prompt_type: str, context_hash: str) -> str:
        return f"{prompt_type}:{context_hash}"

    def get(self, prompt_type: str, context: dict) -> Optional[str]:
        key = self.get_cache_key(prompt_type, self.hash_context(context))
        return self.cache.get(key)

    def set(self, prompt_type: str, context: dict, response: str) -> None:
        if len(self.cache) >= self.max_size:
            self.evict_oldest()
        key = self.get_cache_key(prompt_type, self.hash_context(context))
        self.cache[key] = {
            'response': response,
            'timestamp': time.time()
        }
```

### Pre-generation Queue

```python
class PreGenerationQueue:
    """Queue for pre-generating content ahead of player"""

    def __init__(self, llm_engine: LLMEngine):
        self.queue = asyncio.Queue()
        self.llm_engine = llm_engine

    async def enqueue_adjacent_rooms(self, player_pos: Position) -> None:
        """Queue generation of rooms adjacent to player"""
        for direction in ['north', 'south', 'east', 'west']:
            adjacent_pos = self.get_adjacent(player_pos, direction)
            if not self.is_generated(adjacent_pos):
                await self.queue.put(('room', adjacent_pos))

    async def process_queue(self) -> None:
        """Background task to process generation queue"""
        while True:
            task_type, data = await self.queue.get()
            if task_type == 'room':
                await self.llm_engine.generate_room(data)
```

## Input Processing for LLM

### Action Interpretation

The LLM processes player actions from controller/keyboard input:

```python
class ActionInterpreter:
    """Convert game actions to LLM-understandable commands"""

    def interpret_action(
        self,
        action_type: str,
        context: GameContext
    ) -> str:
        """
        Actions come from controller/keyboard input:
        - Movement: D-pad/Left stick/WASD
        - Interact: A button/Space/Enter
        - Attack: X button/F key
        - etc.
        """
        if action_type == 'move':
            return f"Player moves {context.direction}"
        elif action_type == 'interact':
            target = context.get_interaction_target()
            if target:
                return f"Player interacts with {target.name}"
            return "Player examines surroundings"
        elif action_type == 'talk':
            npc = context.get_nearby_npc()
            if npc:
                return f"Player speaks to {npc.name}"
            return "Player calls out"
        elif action_type == 'attack':
            target = context.get_attack_target()
            if target:
                return f"Player attacks {target.name} with {context.weapon}"
            return "Player swings at air"
        elif action_type == 'use_item':
            return f"Player uses {context.item.name}"
        else:
            return f"Player performs action: {action_type}"
```

### Controller Action Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│              Controller/Keyboard to LLM Action Flow              │
│                                                                  │
│  Controller Input          Game Action          LLM Command      │
│  ────────────────          ───────────          ───────────      │
│  D-Pad Up            →     move_north      →    "move north"     │
│  A Button            →     interact        →    "interact with X"│
│  X Button            →     attack          →    "attack target"  │
│  Y Button            →     inventory       →    (UI only)        │
│  LT Hold + A         →     sneak_interact  →    "quietly examine"│
│  RT + X              →     power_attack    →    "heavy attack"   │
│                                                                  │
│  Keyboard Input           Game Action          LLM Command       │
│  ──────────────           ───────────          ───────────       │
│  W Key               →     move_north      →    "move north"     │
│  Space/Enter         →     interact        →    "interact with X"│
│  F Key               →     attack          →    "attack target"  │
│  I Key               →     inventory       →    (UI only)        │
│  Ctrl + Space        →     sneak_interact  →    "quietly examine"│
│  Shift + F           →     power_attack    →    "heavy attack"   │
└─────────────────────────────────────────────────────────────────┘
```

## Model Configuration

### Supported Models

```python
MODEL_CONFIGS = {
    'gpt-4o-mini': {
        'max_tokens': 4096,
        'temperature': 0.7,
        'best_for': ['room_generation', 'dialogue'],
        'cost_tier': 'low'
    },
    'gpt-4o': {
        'max_tokens': 8192,
        'temperature': 0.7,
        'best_for': ['complex_narrative', 'quest_generation'],
        'cost_tier': 'high'
    },
    'claude-3-haiku': {
        'max_tokens': 4096,
        'temperature': 0.7,
        'best_for': ['room_generation', 'dialogue'],
        'cost_tier': 'low'
    },
    'claude-3-sonnet': {
        'max_tokens': 8192,
        'temperature': 0.7,
        'best_for': ['complex_narrative', 'quest_generation'],
        'cost_tier': 'medium'
    }
}
```

### Temperature Settings

```python
TEMPERATURE_BY_TASK = {
    'room_description': 0.8,    # Creative, varied
    'npc_dialogue': 0.7,        # Balanced
    'combat_narration': 0.6,    # Somewhat consistent
    'quest_generation': 0.7,    # Creative but coherent
    'item_description': 0.5,    # More consistent
    'tilemap_generation': 0.3   # Predictable structure
}
```

## Rate Limiting & Cost Management

### Request Throttling

```python
class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.request_times = []

    async def acquire(self) -> None:
        now = time.time()
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]

        if len(self.request_times) >= self.rpm:
            sleep_time = 60 - (now - self.request_times[0])
            await asyncio.sleep(sleep_time)

        self.request_times.append(time.time())
```

### Cost Tracking

```python
class CostTracker:
    def __init__(self):
        self.total_tokens = 0
        self.total_cost = 0.0

    def log_request(self, model: str, tokens: int) -> None:
        cost_per_token = MODEL_COSTS[model]
        cost = tokens * cost_per_token
        self.total_tokens += tokens
        self.total_cost += cost

    def get_session_cost(self) -> float:
        return self.total_cost
```

## Error Handling

### Retry Strategy

```python
class LLMRetryHandler:
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except RateLimitError:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
            except APIError as e:
                last_error = e
                if not e.is_retryable:
                    break

        # Return fallback content
        return self.get_fallback(*args, **kwargs)
```

## Performance Metrics

### Tracking

```python
class LLMMetrics:
    def __init__(self):
        self.request_count = 0
        self.total_latency = 0.0
        self.cache_hits = 0
        self.cache_misses = 0

    def record_request(self, latency: float, cached: bool) -> None:
        self.request_count += 1
        self.total_latency += latency
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def get_average_latency(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_latency / self.request_count

    def get_cache_hit_rate(self) -> float:
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return self.cache_hits / total
```

## Future Enhancements

1. **Multi-Model Routing:** Use different models for different tasks
2. **Fine-tuned Models:** Custom models for game-specific content
3. **Local Model Support:** Run smaller models locally for offline play
4. **Streaming Responses:** Progressive content delivery
5. **Player Preference Learning:** Adapt content style to player preferences
