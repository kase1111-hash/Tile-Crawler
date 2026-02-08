# TILE-CRAWLER REFOCUS GUIDE

A step-by-step plan to cut dead weight, restructure what remains, and invest in the core product: the LLM dungeon master.

**Current state:** ~40,000 lines across 131 files. Three separate products tangled into one repo.
**Target state:** ~15,000 lines. One product: an LLM-powered roguelike with a tight game loop.

---

## PHASE 0: PREPARATION (before cutting anything)

### 0.1 Tag current state
```bash
git tag v0.1.0-pre-refocus -m "Snapshot before refocus: all systems intact"
git push origin v0.1.0-pre-refocus
```
This preserves the Glyph Foundry, GASR system, and audio engine in case they become their own projects later.

### 0.2 Run the full test suite, record baseline
```bash
cd backend && pytest tests/ -v --tb=short --cov=. --cov-report=term-missing
```
Record passing test count and coverage percentage. Every phase below should end with this same command passing at equal or higher rates.

---

## PHASE 1: CUT DEAD CODE (est. ~8,900 lines removed)

These systems are not connected to the game loop. Removing them has zero impact on gameplay.

### 1.1 Delete the Procedural Glyph Foundry

**What:** `backend/foundry/` -- 8 files, 3,155 lines. AI-powered tile generation pipeline (grammar, palettes, WFC edges, PNG-to-font compiler). None of it is called by the game engine.

**Files to delete:**
```
backend/foundry/__init__.py          (82 lines)
backend/foundry/compiler.py          (550 lines)
backend/foundry/edges.py             (292 lines)
backend/foundry/font_generator.py    (768 lines)
backend/foundry/generator.py         (387 lines)
backend/foundry/grammar.py           (341 lines)
backend/foundry/palettes.py          (390 lines)
backend/foundry/validator.py         (345 lines)
```

**Test file to delete:**
```
backend/tests/test_foundry.py        (633 lines)
```

**Imports to remove from `main.py`:** Search for any `from foundry` imports and remove the corresponding endpoints. (There are foundry-related endpoints in the lower half of `main.py` -- remove those route handlers entirely.)

**Dependencies to remove from `requirements.txt`:**
```
numpy>=1.26.0       # Only used by font_generator.py
```
Keep `pillow` and `fonttools` only if other code uses them -- check with `grep -r "from PIL\|import PIL\|from fonttools\|import fonttools" backend/ --include="*.py"` excluding `foundry/`.

**Data file to keep (for now):** `data/palettes.json` is harmless and tiny.

**Docs to archive:**
```
docs/design/03-art-studio.md         (385 lines)
```
Move to a `docs/archive/` directory rather than deleting, in case the Foundry becomes its own repo.

**Script to delete:**
```
scripts/generate_font.py             (125 lines)
```

### 1.2 Gut the GASR Glyph Rendering System

**What:** `backend/glyphs/` -- 6 files, 1,714 lines. 6-layer SNES-style rendering engine with animation, legend compression, and glyph-to-unicode PUA mapping. The frontend renders plain ASCII characters; it does not use this system.

**Files to delete:**
```
backend/glyphs/engine.py             (514 lines) -- Multi-layer room rendering. Unused.
backend/glyphs/layers.py             (296 lines) -- Layer manager. Unused.
backend/glyphs/legends.py            (251 lines) -- LLM context compression. Unused.
```

**Files to KEEP:**
```
backend/glyphs/__init__.py           (57 lines)  -- Trim to only export what's kept.
backend/glyphs/models.py             (217 lines) -- Glyph data models. Useful if the frontend ever uses the glyph font.
backend/glyphs/registry.py           (379 lines) -- Loads glyphs.json. Keep as reference.
```

**Test file to trim:**
```
backend/tests/test_glyphs.py         (739 lines)
```
Remove all tests for `engine`, `layers`, and `legends`. Keep tests for `models` and `registry`. This should reduce the file to ~200 lines.

**Docs to archive:**
```
docs/design/02-glyph-rendering-system.md  (413 lines)
```

### 1.3 Delete the TTS Audio Engine

**What:** The backend generates onomatopoeia-based audio intents ("KRAKOOM!", "WHOOSH!") and the frontend has a 513-line Web Audio engine to synthesize them. But the synthesis pipeline is not wired into the game's actual playback. The `useAudio` hook (344 lines) and `AudioSettings` component (218 lines) have no visible effect on the game.

**Backend files to delete:**
```
backend/audio_engine.py              (570 lines)
```

**Frontend files to delete:**
```
frontend/src/services/audioEngine.ts (513 lines)
frontend/src/hooks/useAudio.ts       (344 lines)
frontend/src/components/AudioSettings.tsx (218 lines)
```

**Data file to delete:**
```
data/audio_schema.json               (168 lines)
```

**Cleanup in `main.py`:**
Every endpoint currently imports and calls `get_audio_engine()` and generates audio intents. This is the most labor-intensive cut. Here's what to do:

1. Remove the import: `from audio_engine import get_audio_engine` (line 27)
2. Remove the `AudioIntentResponse` model (lines 143-154)
3. Remove the `audio` field from `ActionResponse` (line 175) -- or keep it as `Optional[dict] = None` and just never populate it
4. In every endpoint handler (`new_game`, `move`, `attack`, `flee`, `take_item`, `use_item`, `talk`, `rest`), delete the audio generation blocks. These are identifiable by `audio_engine = get_audio_engine()` followed by `audio_engine.generate_*()` calls.

**Specific locations in `main.py` to clean:**
- `new_game` (lines 532-539): Remove `audio_engine` and `audio_batch` generation
- `move` (lines 778-802): Remove all audio generation in the movement handler
- `attack` (lines 869-906): Remove combat audio layering
- `flee` (lines 939-959): Remove flee/hurt audio
- `take_item` (lines 994-1004): Remove pickup audio
- `use_item` (lines 1041-1073): Remove item-use audio branching
- `talk` (lines 1140-1148): Remove NPC reaction audio
- `rest` (lines 1182-1204): Remove rest ambient audio
- WebSocket handler (lines 1345, 1370, 1381-1384, 1390-1391, 1396-1397, 1407-1408, 1417-1419, 1426-1427): Remove all `audio_engine` references

After this, set `audio=None` in all `ActionResponse(...)` return statements where you removed audio data.

**Frontend cleanup:**
- In `frontend/src/hooks/useGame.ts`: Remove the `playAudio` callback (lines 55-63), the `audioEngine` ref (line 37), the `import { getAudioEngine }` (line 5), and the `AudioBatch` type import. Remove `playAudio` from the `handleResponse` callback.
- In `frontend/src/types/game.ts`: Keep the `AudioIntent`, `AudioBatch` types for now (they're harmless), or delete them if you want a clean cut.
- In `frontend/src/components/index.ts`: Remove the `AudioSettings` export.

### 1.4 Delete speculative documentation

**Files to archive (move to `docs/archive/`):**
```
SPEC.md                              (1,573 lines) -- Describes systems that don't exist.
DLP-Powered.md                       (180 lines)   -- Theoretical framework.
Diffable-Worlds.md                   (246 lines)   -- Speculative design.
KEYWORDS.md                          (418 lines)   -- SEO-style keyword list.
docs/design/07-entity-npc-system.md  (662 lines)   -- Describes unbuilt NPC AI.
docs/design/08-save-system.md        (608 lines)   -- Over-specifies save system.
```

**Files to keep:**
```
docs/design/01-core-architecture.md  (261 lines) -- Still relevant.
docs/design/04-world-generation.md   (503 lines) -- Directly relevant to the core loop.
docs/design/05-llm-intelligence-layer.md (545 lines) -- This IS the product. Keep and update.
docs/design/06-rpg-systems.md        (532 lines) -- Combat/stats are implemented. Keep.
docs/api/api-reference.md            (791 lines) -- Keep but will need updating after cuts.
docs/schemas/data-schemas.md         (918 lines) -- Keep.
```

### 1.5 Phase 1 checkpoint

Run the full test suite. Fix any import errors from deleted modules. The game should still work identically -- you removed nothing that was connected to the game loop.

**Expected removal:** ~8,900 lines of code + ~3,700 lines of docs = ~12,600 lines total.

---

## PHASE 2: DEFER PERIPHERAL SYSTEMS (est. ~2,500 lines gated)

These systems work but add complexity without current benefit. Don't delete them -- gate them behind feature flags or make them optional.

### 2.1 Make authentication optional

**Current problem:** Every game endpoint has `current_user: Optional[User] = Depends(get_current_user_optional)` and then does `session_id = get_session_id_for_user(current_user.id if current_user else None)`. This is 5 lines of boilerplate per endpoint for a feature that has zero value in single-player.

**What to do:**
1. Keep `backend/auth/` intact (618 lines). Don't delete it.
2. Add an env flag: `AUTH_ENABLED=false` in `.env.example`
3. Create a simplified session flow: when `AUTH_ENABLED=false`, skip all `get_current_user_optional` dependency injection and use a hardcoded `session_id = "default"`.
4. In `main.py`, create a conditional dependency:

```python
# At the top of main.py, after load_dotenv()
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").lower() == "true"

# Replace get_current_user_optional in game endpoints:
async def get_optional_user():
    if not AUTH_ENABLED:
        return None
    # ... existing logic
```

5. When `AUTH_ENABLED=false`, skip the auth endpoint registration entirely (use `if AUTH_ENABLED:` around the `@app.post("/api/auth/...")` blocks).

**Files affected:** `main.py` (all game endpoints), `session_manager.py`
**Files untouched:** `backend/auth/*` stays intact for when you need it.

### 2.2 Remove rate limiting from game endpoints

**Current problem:** `@limiter.limit(RATE_LIMIT_LLM)` decorates `new_game`, `move`, all directional move shortcuts, and `talk`. A single-player game rate-limiting its own player is friction with no upside.

**What to do:**
1. Remove `@limiter.limit(...)` decorators from all game endpoints (lines 517, 759, 819, 825, 831, 837, 1128).
2. Keep rate limiting only on auth endpoints (`register`, `login`) as a security precaution -- or remove entirely if `AUTH_ENABLED=false`.
3. Keep the `slowapi` import and limiter initialization but don't apply it to game routes.

### 2.3 Remove shorthand movement endpoints

**Current problem:** Four duplicate endpoints (`/api/game/move/north`, `/south`, `/east`, `/west` at lines 817-843) that just call the main `/api/game/move` endpoint. The frontend doesn't use them.

**What to do:** Delete the four `move_north`, `move_south`, `move_east`, `move_west` handlers. The generic `POST /api/game/move` with `{"direction": "north"}` is sufficient.

### 2.4 Remove the generic action endpoint

**Current problem:** `POST /api/game/action` (lines 1244-1310) duplicates every other endpoint in a single handler. The frontend doesn't use it.

**What to do:** Delete the entire `perform_action` handler.

### 2.5 Consolidate health check endpoints

**Current problem:** Three endpoints (`/`, `/health`, `/api/health`) return identical data.

**What to do:** Keep `/api/health` (consistent with the `/api/` prefix convention). Delete the root `/` and `/health` handlers. Update Docker health checks and CI smoke tests to use `/api/health`.

### 2.6 Gate WebSocket behind a flag

**Current problem:** The WebSocket endpoint (lines 1317-1461) and `websocket_manager.py` (228 lines) duplicate the entire REST API over WebSocket. The frontend uses HTTP exclusively.

**What to do:**
1. Add env flag: `WEBSOCKET_ENABLED=false`
2. Wrap the WebSocket endpoint and `/api/ws/info` in `if WEBSOCKET_ENABLED:` guards.
3. Don't delete `websocket_manager.py` -- just don't import or use it when disabled.

**Frontend file to remove now:**
```
frontend/src/hooks/useGameWebSocket.ts  (215 lines)
frontend/src/services/websocket.ts      (253 lines)
```
These aren't imported by any component in the current `App.tsx`.

### 2.7 Phase 2 checkpoint

Run tests. The game should behave identically with `AUTH_ENABLED=false` and `WEBSOCKET_ENABLED=false`. Endpoints are fewer, handlers are simpler, and each one has ~5 fewer lines of auth/audio boilerplate.

---

## PHASE 3: RESTRUCTURE `main.py` (est. 1,508 -> ~400 lines)

After phases 1-2, `main.py` will be significantly smaller. Now split it properly.

### 3.1 Extract request/response models

**Create `backend/schemas.py`:**
Move all Pydantic models currently defined in `main.py` (lines 54-231):
- `NewGameRequest`
- `MoveRequest`
- `TakeItemRequest`
- `UseItemRequest`
- `TalkRequest`
- `ActionResponse`
- `GameStateResponse`
- `HealthResponse`
- `InventoryResponse`
- `SaveLoadResponse`

### 3.2 Extract route handlers into routers

**Create `backend/routers/` directory with:**

```
backend/routers/__init__.py
backend/routers/game.py       # /api/game/* endpoints (new, state, save, load, saves, move, prefetch)
backend/routers/combat.py     # /api/game/combat/* endpoints (attack, flee)
backend/routers/inventory.py  # /api/game/take, /api/game/use, /api/game/inventory
backend/routers/interaction.py # /api/game/talk, /api/game/rest
backend/routers/health.py     # /api/health
```

If auth is re-enabled later:
```
backend/routers/auth.py       # /api/auth/* endpoints
```

Each router file uses `APIRouter(prefix="/api/game", tags=["Game Management"])` etc.

### 3.3 Slim down `main.py`

After extraction, `main.py` should contain only:
1. FastAPI app creation and metadata (~30 lines)
2. Middleware setup (CORS) (~10 lines)
3. Router includes (`app.include_router(...)`) (~10 lines)
4. Lifespan handler (~10 lines)
5. `if __name__ == "__main__"` block (~10 lines)

Target: **~80 lines**.

### 3.4 Phase 3 checkpoint

All existing tests should pass without modification (they hit the same URL paths via `TestClient`). The only change is where the code lives.

---

## PHASE 4: BREAK UP THE GOD OBJECT (est. 1,065 -> 3 files ~350 each)

`game_engine.py` does too much. Split it by responsibility.

### 4.1 Extract combat system

**Create `backend/combat_engine.py`:**
Move from `game_engine.py`:
- `CombatState` model (lines 51-61)
- `_start_combat()` (lines 297-312)
- `attack()` (lines 314-371)
- `_end_combat_victory()` (lines 373-430)
- `_end_combat_defeat()` (lines 432-469)
- `flee()` (lines 471-519)
- Combat constants: `CRITICAL_HIT_CHANCE`, `CRITICAL_HIT_MULTIPLIER`, `FLEE_BASE_CHANCE`, `FLEE_SPEED_MODIFIER`

`CombatEngine` takes `player_state`, `narrative_memory`, `llm_engine`, and `enemy_data` as constructor args (not singletons).

### 4.2 Extract interaction system

**Create `backend/interaction_engine.py`:**
Move from `game_engine.py`:
- `take_item()` (lines 521-603)
- `use_item()` (lines 605-689)
- `talk()` (lines 691-762)
- `rest()` (lines 764-799)

`InteractionEngine` takes `world_state`, `inventory_state`, `narrative_memory`, `llm_engine`, `player_state`, and `item_data` as constructor args.

### 4.3 Slim down `GameEngine`

After extraction, `GameEngine` retains:
- `new_game()` -- Orchestrates reset and starting room generation
- `move()` -- Movement logic and room generation trigger
- `_generate_room()` -- LLM room generation orchestration
- `_determine_biome()` / `_determine_exits()` -- World generation helpers
- `get_game_state()` -- State snapshot for API responses
- `save_to_database()` / `load_from_database()` -- Persistence
- `prefetch_adjacent_rooms()`

It delegates to `CombatEngine` and `InteractionEngine` for their respective actions.

### 4.4 Replace singletons with dependency injection

**Current pattern (everywhere):**
```python
_game_engine: Optional[GameEngine] = None

def get_game_engine() -> GameEngine:
    global _game_engine
    if _game_engine is None:
        _game_engine = GameEngine()
    return _game_engine
```

**Target pattern:** Use FastAPI's `Depends()` properly:
```python
# In a new file: backend/dependencies.py
from functools import lru_cache

@lru_cache()
def get_llm_engine() -> LLMEngine:
    return LLMEngine()

def get_game_engine(llm: LLMEngine = Depends(get_llm_engine)) -> GameEngine:
    return GameEngine(llm=llm)
```

This makes every component testable by passing mocks directly instead of monkey-patching `_module_state = None` in conftest.

### 4.5 Phase 4 checkpoint

All tests pass. `conftest.py` can be simplified -- instead of patching 5 global variables, tests inject mock dependencies directly.

---

## PHASE 5: DOUBLE DOWN ON THE CORE (the investment phase)

Everything above was removal and restructuring. This phase builds new value.

### 5.1 Improve LLM room generation prompts

**File:** `backend/llm_engine.py:122-176` (the `generate_room` method)

**Current state:** One generic prompt template for all biomes. The biome name is passed as a string, but the prompt doesn't meaningfully differentiate between a dungeon and a volcano.

**What to build:**
1. **Per-biome prompt templates** -- Create `backend/prompts/` directory with a YAML or JSON file per biome:
   ```
   backend/prompts/dungeon.yaml
   backend/prompts/cave.yaml
   backend/prompts/crypt.yaml
   ```
   Each contains atmosphere keywords, enemy archetypes, item themes, architectural vocabulary, and example descriptions specific to that biome.

2. **Structured tile constraints** -- The current prompt says "use tile characters" and lists them. Instead, pass a constrained tile vocabulary per biome (e.g., caves should use `≈` for water pools, volcanos should use special characters for lava).

3. **Few-shot examples** -- Include 1-2 example room JSON responses in the prompt. This dramatically improves LLM output consistency, especially with smaller models like Llama 3.2.

### 5.2 Add response caching

**File:** New file `backend/llm_cache.py`

**Current state:** Every room generation is a fresh LLM call. Moving into the same biome at the same depth generates a brand new room every time, burning tokens.

**What to build:**
1. A simple cache keyed on `(biome, depth_range, has_enemies, has_npcs)` that stores recently generated rooms.
2. Cache hit returns a stored room with randomized enemy/item placement (don't regenerate the map, just shuffle what's in it).
3. Cache miss calls the LLM and stores the result.
4. Keep cache size small (20-50 rooms) and use LRU eviction.
5. This cuts LLM costs by ~40-60% during normal play while maintaining variety.

### 5.3 Enrich narrative memory

**File:** `backend/narrative_memory.py`

**Current state:** A rolling list of 10 events with importance scores. The `get_context_for_llm()` method returns the last 5 events as bullet points. This is functional but shallow.

**What to build:**

1. **Theme tracking.** When the LLM generates a room with features like `blood_stains` or `ancient_pillar`, extract themes and track their frequency. After 3+ rooms with blood references, the narrative context should tell the LLM: "The player has been encountering signs of violence throughout this level."

2. **NPC relationship memory.** Currently dialogue history is a flat list that gets trimmed to 10 entries. Instead, maintain a per-NPC relationship object:
   ```python
   class NPCRelationship(BaseModel):
       npc_id: str
       encounters: int = 0
       disposition: str = "neutral"  # friendly, hostile, cautious
       key_topics: list[str] = []    # things discussed
       last_seen: tuple[int,int,int] = (0,0,0)
   ```
   Feed this to the dialogue prompt so NPCs remember the player.

3. **Story arc generation.** After every N rooms (e.g., 10), call `llm_engine.summarize_story()` (which already exists at line 453) to update the story summary. The current code never calls this method -- wire it into the game loop so the LLM progressively builds a coherent narrative.

4. **Danger escalation.** Track consecutive combat encounters. If the player has fought 3 enemies in a row, the narrative context should include tension indicators. If the player hasn't fought anything in 5 rooms, the context should suggest something is watching.

### 5.4 Improve fallback room generation

**File:** `backend/llm_engine.py:210-264`

**Current state:** `_generate_fallback_room()` generates the same rectangular room every time, differing only in the 1-sentence description keyed by biome. When the LLM is unavailable, every room is identical.

**What to build:**
1. **Room template library.** Load `data/room_templates.json` (which already exists, 389 lines, and is currently unused) and randomly select templates based on biome.
2. **Random feature placement.** Place 1-3 features (torches, pillars, debris) at random floor positions.
3. **Enemy spawning.** Occasionally place enemies from `data/enemies.json` based on biome and depth.
4. **Item spawning.** Use `data/loot_tables.json` (also unused, 432 lines) to roll for items.

This makes the game playable and interesting without any LLM, which is critical for:
- Offline play
- CI/CD testing (no API key needed)
- Demo/showcase purposes
- Users who can't afford API credits

### 5.5 Polish the pseudo-3D renderer

**File:** `frontend/src/App.tsx:8-141` (`render3DView()`)

**Current state:** Renders a Wolfenstein-style perspective view using ASCII characters. Shows walls, floor, ceiling, and passages. Does not show enemies, items, NPCs, or room features.

**What to build:**
1. **Entity rendering.** If the current room has enemies, render an `&` character at the center of the forward view. If NPCs, render `☺`. Scale size based on distance.
2. **Item indicators.** If items are on the ground, render `$` near the floor.
3. **Biome atmosphere.** Vary the floor/wall/ceiling characters per biome:
   - Dungeon: `▓░·` (current)
   - Cave: `█▒·` with occasional `≈` for water
   - Crypt: `▓░†` with cross markers
   - Volcano: `▓▒` with `~` for heat shimmer
4. **Torch light effect.** If the player has an active torch buff, increase the "visible" area in the perspective calculation.

### 5.6 Add latency measurement

**File:** New file `backend/metrics.py` (simple, ~50 lines)

**What to build:** A decorator or context manager that logs LLM call latency:
```python
import time, logging
logger = logging.getLogger("llm_latency")

async def timed_llm_call(func, *args, **kwargs):
    start = time.monotonic()
    result = await func(*args, **kwargs)
    elapsed = time.monotonic() - start
    logger.info(f"LLM call took {elapsed:.2f}s")
    return result
```
Apply to `generate_room`, `generate_dialogue`, and `generate_combat_narration`. This gives you data to optimize against.

### 5.7 Phase 5 checkpoint

The game should now:
- Generate notably different rooms per biome
- Remember what the player has done and reference it
- Be playable and interesting without an LLM
- Show enemies/items in the 3D view
- Log LLM latency for every call

---

## PHASE 6: CLEAN UP TESTS

### 6.1 Delete tests for removed systems
Already handled in Phase 1 (`test_foundry.py` deleted, `test_glyphs.py` trimmed).

### 6.2 Add unit tests for game logic

**Current gap:** `test_game_flow.py` tests the game through HTTP endpoints (integration tests). There are no unit tests for combat math, flee calculations, item effects, or room generation logic.

**What to add:**
```
backend/tests/test_combat_engine.py   -- Test damage calc, crit chance, flee math
backend/tests/test_interaction.py     -- Test item effects, NPC dialogue flow
backend/tests/test_llm_prompts.py     -- Test prompt construction (no API calls)
backend/tests/test_fallback_rooms.py  -- Test fallback generator variety
```

### 6.3 Remove WebSocket tests (if WebSocket is gated)
If `WEBSOCKET_ENABLED=false` is the default, `test_websocket_manager.py` (240 lines) can be gated with `@pytest.mark.skipif(not WEBSOCKET_ENABLED)`.

---

## PHASE 7: UPDATE DOCUMENTATION

### 7.1 Rewrite README.md
The current README (566 lines) references features that will be removed. Rewrite to focus on:
1. What the game is (2 paragraphs)
2. How to run it (docker-compose up)
3. How to play (keyboard controls)
4. How LLM integration works (which models, how to configure)
5. How to run without an LLM (fallback mode)

Target: ~150 lines.

### 7.2 Update API reference
`docs/api/api-reference.md` (791 lines) will need updating to remove deleted endpoints and document the slimmer API.

### 7.3 Update CONTRIBUTING.md
Remove references to the glyph system, foundry, and audio engine.

---

## SUMMARY: FILE DISPOSITION TABLE

### DELETE (move to archive tag, then remove from main branch)

| Path | Lines | Reason |
|------|------:|--------|
| `backend/foundry/*` (8 files) | 3,155 | Disconnected tile toolkit |
| `backend/audio_engine.py` | 570 | TTS pipeline with no frontend playback |
| `backend/glyphs/engine.py` | 514 | Unused multi-layer renderer |
| `backend/glyphs/layers.py` | 296 | Unused layer manager |
| `backend/glyphs/legends.py` | 251 | Unused legend compression |
| `backend/tests/test_foundry.py` | 633 | Tests for deleted code |
| `frontend/src/services/audioEngine.ts` | 513 | Unused TTS synthesizer |
| `frontend/src/hooks/useAudio.ts` | 344 | Unused audio hook |
| `frontend/src/hooks/useGameWebSocket.ts` | 215 | Unused WebSocket hook |
| `frontend/src/services/websocket.ts` | 253 | Unused WebSocket client |
| `frontend/src/components/AudioSettings.tsx` | 218 | Unused audio UI |
| `data/audio_schema.json` | 168 | Schema for deleted audio system |
| `scripts/generate_font.py` | 125 | Script for deleted foundry |
| **Subtotal** | **7,255** | |

### ARCHIVE (move to `docs/archive/`)

| Path | Lines | Reason |
|------|------:|--------|
| `SPEC.md` | 1,573 | Speculative; describes unbuilt systems |
| `DLP-Powered.md` | 180 | Theoretical framework |
| `Diffable-Worlds.md` | 246 | Speculative design |
| `KEYWORDS.md` | 418 | SEO keyword list |
| `docs/design/02-glyph-rendering-system.md` | 413 | Docs for gutted system |
| `docs/design/03-art-studio.md` | 385 | Docs for deleted foundry |
| `docs/design/07-entity-npc-system.md` | 662 | Describes unbuilt NPC AI |
| `docs/design/08-save-system.md` | 608 | Over-specifies save system |
| **Subtotal** | **4,485** | |

### GATE (keep code, disable by default)

| Path | Lines | Flag |
|------|------:|------|
| `backend/auth/*` (4 files) | 618 | `AUTH_ENABLED=false` |
| `backend/websocket_manager.py` | 228 | `WEBSOCKET_ENABLED=false` |
| `backend/session_manager.py` | 178 | Simplified when auth disabled |
| **Subtotal** | **1,024** | |

### KEEP AND IMPROVE

| Path | Lines | Investment |
|------|------:|------------|
| `backend/llm_engine.py` | 503 | Better prompts, caching, latency tracking |
| `backend/narrative_memory.py` | 276 | Theme tracking, NPC memory, arc generation |
| `backend/game_engine.py` | 1,065 | Split into 3 files, improve fallback rooms |
| `backend/main.py` | 1,508 | Split into routers, ~80 line main |
| `frontend/src/App.tsx` | 452 | Entity rendering, biome atmosphere |
| `frontend/src/hooks/useGame.ts` | 238 | Remove audio references |
| `frontend/src/services/api.ts` | 116 | Unchanged |
| **Subtotal** | **4,158** | Core product |

---

## EXECUTION ORDER

If you can only do one thing per week:

1. **Week 1:** Phase 1 (cut dead code). Biggest impact, lowest risk.
2. **Week 2:** Phase 2 (defer peripherals) + Phase 3 (restructure main.py).
3. **Week 3:** Phase 4 (break up god object).
4. **Week 4:** Phase 5.4 (improve fallback rooms) -- makes the game playable without LLM.
5. **Week 5:** Phase 5.1 + 5.2 (better prompts + caching) -- makes the LLM experience better.
6. **Week 6:** Phase 5.3 (narrative memory) -- makes the game memorable.
7. **Week 7:** Phase 5.5 (3D renderer polish) + Phase 6 (tests) + Phase 7 (docs).

After week 7 you have a focused, well-structured, well-tested LLM roguelike with a distinctive visual style and a smart AI dungeon master. Then -- and only then -- consider what to add next.
