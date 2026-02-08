# PROJECT EVALUATION REPORT

**Primary Classification:** Good Concept, Bad Execution
**Secondary Tags:** Feature Creep, Multiple Ideas in One

---

## CONCEPT ASSESSMENT

**What real problem does this solve?**
Existing roguelikes have static, hand-authored content that gets stale. Tile-Crawler uses an LLM as a dynamic dungeon master to generate rooms, narrate combat, and drive NPC dialogue on the fly, so every playthrough feels genuinely unique. That is a real problem worth solving.

**Who is the user?**
Roguelike enthusiasts who want procedural narrative depth, not just procedural layouts. The pain is real -- procedural generation today means randomized tiles, not randomized storytelling.

**Is this solved better elsewhere?**
AI Dungeon proved the LLM-as-game-master concept at scale but is text-only. No shipped product combines an LLM dungeon master with a visual tilemap engine in a browser. The niche is defensible.

**Value prop in one sentence:**
A browser-based roguelike where an LLM generates every room, narrates every fight, and voices every NPC in real time.

**Verdict:** Sound -- the core loop of "move, LLM generates room, fight, LLM narrates" is a tight idea with a clear audience. The concept does not need to be bigger.

---

## EXECUTION ASSESSMENT

### Architecture: Overbuilt for current state

The codebase has a 1,508-line `main.py` monolith containing 29 route handlers, all request/response models, CORS config, rate limiting, auth, OpenAPI metadata, and the WebSocket endpoint in a single file. This is a FastAPI anti-pattern -- routes should be in routers, models in schemas. A file this size actively slows development.

`game_engine.py` (1,065 lines) is a god object: movement, combat math, room generation orchestration, dialogue handling, loot drops, status effects, save/load coordination, and NPC interaction all live in one class. The `GameEngine.__init__` grabs five singletons (`world`, `narrative`, `inventory`, `player`, `llm`), making it untestable without resetting global state -- which is exactly what `conftest.py` does by monkey-patching private `_module_state = None` variables.

### Code quality: Competent but shallow

The Python is clean, readable, and uses Pydantic models consistently. Input validation (player name sanitization in `NewGameRequest`) is present. Error handling in `llm_engine.py` includes fallback room generation when the LLM fails. These are signs of a developer who understands production concerns.

However:
- **Singletons everywhere.** `get_game_engine()`, `get_llm_engine()`, `get_world_state()`, `get_audio_engine()` -- all module-level singletons. This makes multi-session support fragile. The `get_game_engine_for_session()` variant exists but is bolted on after the fact.
- **No dependency injection.** FastAPI has `Depends()` for exactly this. Instead, the codebase uses bare function calls to fetch global instances.
- **Synchronous file I/O in async handlers.** `_load_item_data()` and `_load_enemy_data()` in `game_engine.py:84-98` use synchronous `open()` inside an otherwise async application. `aiofiles` is in `requirements.txt` but unused in these paths.
- **No database migration story.** SQLite/PostgreSQL is supported via a repository pattern, but there are no Alembic migrations or schema versioning. The first schema change will break all existing saves.

### Tech stack: Appropriate with caveats

FastAPI + React + Vite is a solid choice for this kind of project. The OpenAI client supports both cloud and Ollama, which is smart for a game that burns tokens. Pydantic v2 for validation, JWT for auth, `slowapi` for rate limiting -- all reasonable.

The `numpy`, `pillow`, and `fonttools` dependencies for the Glyph Foundry are heavy for what amounts to a speculative feature (no evidence the font generation pipeline is integrated into the main game loop).

### Frontend: Surprisingly focused

`App.tsx` (452 lines) is the monolith here, but it does one thing: render a pseudo-3D ASCII dungeon view with keyboard controls. The `useGame` hook cleanly separates API calls from rendering. The `api.ts` service layer is minimal and correct. `render3DView()` is a clever piece of work -- pure math, no dependencies, generates a Wolfenstein-style perspective from boolean exit data.

The frontend has no state management library, no router, no component library. For a game with one screen, this is correct.

### Test quality: Present but shallow

13 test files with proper fixtures is more than most hobby projects. `conftest.py` shows understanding of test isolation. But the tests are integration-heavy (hitting the FastAPI `TestClient`) rather than unit-testing game logic functions directly. The `test_game_flow.py` tests are brittle -- they depend on LLM fallback behavior producing specific room structures.

CI pipeline (`ci.yml`) is comprehensive: lint, unit test, coverage, Docker build, integration smoke tests, Playwright E2E. This is production-grade CI for a v0.1.0 project.

**Verdict:** Under-developed core, over-developed periphery. The actual game loop (move, generate, fight) works but the surrounding infrastructure (auth, sessions, audio, glyph foundry, 8 design documents, 66KB spec) outweighs the game itself.

---

## SCOPE ANALYSIS

**Core Feature:** LLM-powered room generation and narrative continuity during dungeon exploration

**Supporting:**
- Turn-based combat with LLM narration (`game_engine.py:314-371`)
- Persistent world memory so revisited rooms stay consistent (`world_state.py`)
- Narrative memory that feeds story context back to the LLM (`narrative_memory.py`)
- Fallback room generation when LLM is unavailable (`llm_engine.py:136`)
- Inventory system for item pickups and usage (`inventory_state.py`)

**Nice-to-Have:**
- NPC dialogue via LLM
- 8-biome system with depth-based progression
- Pseudo-3D first-person rendering (`App.tsx:8-141`)
- Room prefetching for faster navigation (`useGame.ts:41-52`, `/api/game/prefetch`)
- WebSocket for real-time updates (`websocket_manager.py`)

**Distractions:**
- TTS audio synthesis engine (`audio_engine.py`, 17KB) -- generates onomatopoeia intents for a Web Audio pipeline that does not exist in the frontend. The frontend `audioEngine.ts` receives these intents but there is no evidence of actual TTS playback being functional.
- GASR Glyph System (`glyphs/` directory, 5 files) -- an 80-glyph Unicode PUA mapping system with 6-layer SNES-style rendering. The frontend renders ASCII characters with a basic font, not this system. The layers, animations, and legend compression are unused by the actual game.
- Procedural Glyph Foundry (`foundry/` directory, 7 files) -- AI-powered tile generation pipeline with WFC edge compatibility, 12 palettes, 3,840+ combinatorial variants. None of this connects to the game. It's a standalone tool that happens to live in the same repo.
- 66KB SPEC.md -- a design document larger than the entire frontend codebase. Specifies systems (overworld chunks, underworld caverns, sprite editors, camera systems, fog of war) that do not exist in code.

**Wrong Product:**
- JWT authentication with user registration, password change, bcrypt hashing (`auth/` directory) -- this is infrastructure for a multi-user SaaS platform. The game is single-player. Auth adds complexity to every endpoint via `get_current_user_optional` dependency injection, session-to-user mapping, and per-user save isolation. If multiplayer is the goal, it belongs in a separate milestone, not wired into v0.1.0.
- Rate limiting on 4 tiers (`RATE_LIMIT_DEFAULT`, `RATE_LIMIT_AUTH`, `RATE_LIMIT_GAME`, `RATE_LIMIT_LLM`) -- a single-player game does not need rate limiting. This is defensive infrastructure for a public API that doesn't exist yet.
- Session manager (`session_manager.py`) for multi-user session isolation -- again, SaaS infrastructure in a single-player game.
- 8 design documents in `docs/design/` describing systems not yet built

**Scope Verdict:** Feature Creep + Multiple Products. There are at least three distinct projects here:
1. **The actual game** (game engine + LLM integration + React frontend)
2. **A glyph/tileset creation toolkit** (GASR system + Foundry + font generation)
3. **A multi-user game platform** (auth + sessions + rate limiting + database persistence)

---

## RECOMMENDATIONS

### CUT

- **`backend/audio_engine.py`** and **`frontend/src/services/audioEngine.ts`** -- The TTS audio system sends onomatopoeia intents ("KRAKOOM!") but the frontend has no Web Audio processing pipeline. Remove until a real audio system is designed and built.
- **`backend/foundry/`** (all 7 files) -- The Procedural Glyph Foundry is a standalone tool with no integration point to the game. Extract to a separate repo or delete.
- **`backend/glyphs/`** `layers.py`, `legends.py`, `engine.py` -- The 6-layer rendering engine and legend compression system. Keep `models.py` and `registry.py` if you plan to use glyph mapping, but the rendering layer is dead code relative to what the frontend actually renders.
- **`SPEC.md`** (66KB) -- A speculative design document describing systems that don't exist. It creates the illusion of progress while the actual game loop has gaps. Archive it or extract the relevant portions into focused issues.
- **3 health check endpoints** (`/`, `/health`, `/api/health`) -- Pick one. Three endpoints returning the same data is confusing.
- **`numpy`** dependency -- Only pulled in for the font generation pipeline. That's ~30MB of dependency for unused code.

### DEFER

- **Authentication system** (`backend/auth/`) -- Keep the code but make it optional. Strip `Depends(get_current_user_optional)` from game endpoints. Add auth back when multiplayer is real.
- **Rate limiting** -- Remove from game endpoints. Re-add when the API is public.
- **WebSocket support** -- The game works fine over HTTP request/response. WebSocket adds complexity for no current benefit (the game is turn-based, not real-time).
- **PostgreSQL support** -- SQLite is fine for single-player. Defer PostgreSQL until there's a deployment target that needs it.
- **Biomes beyond 3-4** -- 8 biomes with depth-based selection is premature. The LLM generates room content regardless of biome. Focus on making 3 biomes feel distinct before adding more.

### DOUBLE DOWN

- **The LLM-to-room pipeline** (`llm_engine.py:generate_room` + `game_engine.py:_generate_room`). This is the product. The prompt engineering, response parsing, fallback generation, and narrative context injection are where the magic happens. Invest in:
  - Better prompt templates per biome
  - Structured output validation (the current Pydantic parsing is good, do more of it)
  - Response caching so repeated biome/depth combos don't burn tokens
  - Latency measurement and optimization
- **Narrative memory** (`narrative_memory.py`). This is the differentiator. The rolling event log that feeds context back to the LLM is what makes this more than "random room generator." Make it smarter: track recurring themes, reference old events more aggressively, build story arcs.
- **The pseudo-3D renderer** (`App.tsx:render3DView`). This is charming, distinctive, and cheap. It gives the game visual identity with zero dependencies. Polish it: add entity rendering, item indicators, atmospheric effects using ASCII art.
- **Fallback mode** (`llm_engine.py:_generate_fallback_room`). The game must be playable without an LLM. This fallback path is critical for offline play, CI testing, and demo purposes. Make it generate more varied rooms.

---

### FINAL VERDICT: Refocus

The core game loop works and the concept is sound. But the project has accumulated significant dead weight: an unused glyph rendering system, a disconnected font generation toolkit, premature auth/session/rate-limiting infrastructure, and a 66KB spec document describing a game 10x larger than what exists.

The developer clearly has strong engineering instincts (proper CI, Pydantic validation, test fixtures, Docker setup, fallback paths). The problem isn't skill -- it's discipline. The roadmap in the README lists multiplayer, crafting, magic systems, achievements, AR/VR mode, and modder tile generation. None of that matters until the core loop is compelling.

**Next Step:** Delete or extract the Glyph Foundry and GASR rendering system into a separate repo. Then spend the freed-up mental energy on making the LLM generate rooms that are genuinely surprising and narratively connected. The game's only moat is the quality of its AI dungeon master -- everything else is commodity roguelike infrastructure.
