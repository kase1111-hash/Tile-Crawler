# Vibe-Code Detection Audit v2.0 — Tile-Crawler

**Project:** Tile-Crawler (LLM-Powered Dungeon Crawler)
**Date:** 2026-02-23
**Auditor:** Claude Opus 4.6 (automated, per vibe-checkV2 framework)
**Repository:** https://github.com/kase1111-hash/Tile-Crawler

---

## Executive Summary

Tile-Crawler is a FastAPI + React dungeon crawler that uses LLMs as procedural content generators. The codebase is **predominantly AI-generated** (89.8% of commits attributed to "Claude") with limited but meaningful human oversight. The core game loop — movement, combat, inventory, save/load, NPC dialogue — is functional and architecturally sound. However, the project suffers from **aspirational documentation** (README claims features that don't exist), **formulaic test coverage** (281 tests, only 1 error-path test), and **zero organic development artifacts** (no TODOs, no FIXMEs, no WHY comments). The behavioral integrity of the code that *does* exist is surprisingly strong.

**Authenticity Score: 63.4%**
**Vibe-Code Confidence: 36.6 / 100**
**Classification: Substantially Vibe-Coded (36–60 band)**

The code works. It's not garbage. But almost none of it was written, debugged, or iterated on by a human hand — and the artifacts prove it.

---

## Domain A: Surface Provenance (20% weight)

### A1. Commit History Patterns — Score: 1/3

| Metric | Value |
|--------|-------|
| Total commits | 59 |
| Commits by "Claude" | 53 (89.8%) |
| Commits by "Kase" | 6 (10.2%) |
| Formulaic commit messages | 43/59 (72.9%) |
| Human frustration markers | 2 |
| Reverts | 0 |
| AI branch names | `claude/code-review-vibe-check-AKu52` |

**Evidence:** Every non-human commit follows Claude's signature style: imperative verb + noun phrase. "Phase 1: Cut 8,028 lines of dead code and speculative docs", "Phase 2: Gate auth/WS behind feature flags", etc. The 6 human commits are limited to documentation adds ("Create KEYWORDS.md", "Create DLP-Powered.md"). Zero reverts in 59 commits is itself a signal — real development produces reverts. Two "human frustration markers" were found but both are from Claude's commit messages, not genuine human markers.

**Call-chain trace:** `git log --all --no-merges --format='%an'` → 53 "Claude", 6 "Kase". No ambiguity.

### A2. Comment Archaeology — Score: 1/3

| Metric | Value |
|--------|-------|
| Tutorial-style comments | 0 |
| Section dividers (`# ====`) | 32 |
| TODO/FIXME/XXX markers | 0 |
| WHY comments | 2 |
| Source files | 66 |

**Evidence:** Zero TODOs across 66 source files is the single strongest provenance signal in this codebase. Real projects accumulate TODOs like sediment. The 32 section dividers all use Claude's signature `# =====` pattern (see `backend/main.py:20`, `backend/main.py:40`, `backend/main.py:81`, `backend/main.py:100`). Only 2 comments explain *why* something was done (both in `llm_engine.py`). Every module opens with a formulaic triple-quote docstring: `"""Module Name for Tile-Crawler\n\nHandles X, Y, and Z."""` — identical structure across all 20+ backend modules.

### A3. Test Quality — Score: 1/3

| Metric | Value |
|--------|-------|
| Test functions | 281 |
| Trivial `is not None` assertions | 44 (15.7%) |
| Error-path tests (`pytest.raises`) | 1 |
| Formulaic test docstrings | 57 |
| Parametrized tests | 0 |

**Evidence:** 281 test functions is impressive on paper. In practice:

- **1 error-path test** out of 281. Real developers test failure modes. AI generates happy paths.
- **0 parametrized tests.** Not a single `@pytest.mark.parametrize` in the entire project. Humans parametrize to avoid copy-pasting similar test cases; AI generates each variant individually.
- **57 formulaic docstrings** like `"""Tests for CombatState model."""` — the `"""Tests for X."""` pattern is Claude's default.
- **44 trivial assertions** checking `is not None` — a classic AI filler assertion that tests the language runtime, not the code.
- `test_game_flow.py:248` asserts `status_code in [200, 500]` — this literally accepts server crashes as valid behavior.

The test suite at `backend/tests/test_combat_engine.py` is the strongest test file: it tests damage formulas, critical hit math, flee probability, buff interactions, and defeat/victory state transitions. This represents genuine behavioral coverage. But it's an island — most other test files test structure ("does this dict have these keys") rather than behavior.

### A4. Import & Dependency Hygiene — Score: 2/3

**Evidence:** `requirements.txt` declares 17 packages. All are used except:
- `starlette>=0.35.1` — pulled transitively by FastAPI; declaring it explicitly is harmless but unnecessary.
- `typing-extensions>=4.9.0` — stdlib since Python 3.8; explicit declaration is AI cargo-culting.

No wildcard imports. No circular imports detected. Only 1 lazy import (uvicorn in `__main__` block, which is correct). Import hygiene is clean.

### A5. Naming Patterns — Score: 1/3

**Evidence:** Every stateful module follows an identical pattern:

```python
# Global instance
_foo_state: Optional[FooState] = None

def get_foo_state() -> FooState:
    global _foo_state
    if _foo_state is None:
        _foo_state = FooState()
    return _foo_state

def reset_foo_state() -> FooState:
    global _foo_state
    if _foo_state:
        _foo_state.reset()
    _foo_state = FooState()
    return _foo_state
```

This exact pattern appears in: `world_state.py`, `player_state.py`, `inventory_state.py`, `narrative_memory.py`, `llm_engine.py`, `llm_cache.py`, `websocket_manager.py`, `auth/service.py`. Eight files, one template. Real codebases develop naming conventions over time with natural drift; this was stamped out by a single generation pass.

Every `_load()` method has the same structure: check `os.path.exists`, open with `json.load`, catch `(json.JSONDecodeError, KeyError)`, fall back to `_init_default()`. Identical across 5 modules.

### A6. Documentation vs. Reality — Score: 1/3

| README Claim | Reality |
|---|---|
| "GASR Glyph System: 80+ semantic glyph definitions" | `backend/glyphs/` exists with models + registry, but is **never imported** by the game loop. Dead code. |
| "Procedural Glyph Foundry: AI tile generation pipeline" | `backend/foundry/` **does not exist** in the filesystem. |
| "Multi-Layer Rendering: 6-layer SNES-style compositing" | `backend/glyphs/layers.py` and `engine.py` **do not exist**. |
| "12 built-in palettes" / `palettes.json` | `data/palettes.json` **does not exist**. |
| "Custom Font Tilesets" / `DungeonTiles.ttf` | `frontend/src/fonts/` **does not exist**. No font files anywhere. |
| "Wave Function Collapse-ready tile meshing" | No WFC implementation found. |
| "Sound Effects: TTS-based procedural audio" | No audio code exists. |
| "Edge Compatibility" / `edges.py`, `grammar.py` | These files **do not exist**. |
| Project structure in README lists `foundry/`, `layers.py`, `legends.py`, `engine.py`, `compiler.py` | **None of these exist.** |

The README describes a project roughly 3x larger than what's implemented. This is characteristic of AI-generated documentation that describes the *vision* rather than the *reality*. 24 markdown files for 66 source files is a 1:2.75 doc-to-code ratio — far above normal.

### A7. Dependency Utilization — Score: 2/3

**Evidence:** Core dependencies are well-utilized:
- `fastapi` — routers, middleware, depends, lifespan, exception handlers
- `pydantic` — models throughout with field validators, model_dump, ConfigDict
- `openai` — AsyncOpenAI with response_format, temperature control, structured output
- `python-jose` + `passlib` — full JWT + bcrypt auth chain
- `slowapi` — rate limiting on auth endpoints
- `pytest` / `pytest-asyncio` — 281 tests with async support

`httpx` is declared but only used in test fixtures (`conftest.py`). `aiofiles` is declared but never imported anywhere in the codebase.

**Domain A Total: 9/21 → 42.9%**

---

## Domain B: Behavioral Integrity (50% weight)

### B1. Error Handling Depth — Score: 2/3

| Metric | Value |
|--------|-------|
| Bare `except Exception:` | 11 |
| Swallowed exceptions (pass) | 0 |
| Custom exception classes | 0 |
| Exception chaining (`from`) | 0 |
| Typed exception catches | ~5 |

**Evidence:** The LLM engine (`llm_engine.py`) has the best error handling in the project — it differentiates between `json.JSONDecodeError`, `ValidationError`, and general `Exception`, with distinct fallback behavior for each:

```python
# llm_engine.py:243-270 — three-level error handling
try:
    data = json.loads(content)
except json.JSONDecodeError as e:       # Level 1: parse failure
    return self._generate_fallback_room(...)
try:
    result = RoomGenerationResponse.model_validate(data)
except ValidationError as e:            # Level 2: schema mismatch
    return self._generate_fallback_room(...)
except Exception as e:                  # Level 3: API/network failure
    return self._generate_fallback_room(...)
```

This is genuinely good — every LLM call degrades gracefully to fallback content. However:
- **Zero custom exceptions.** The entire project uses only built-in exceptions.
- **Zero exception chaining.** No `raise X from Y` anywhere — context is lost when re-raising.
- Router layer is uniformly `except Exception as e: raise HTTPException(status_code=500, detail=str(e))` — this leaks internal error details to API consumers.
- `auth/service.py:54` has a bare `except Exception: conn.rollback(); raise` — correct behavior but broad catch.

### B2. Configuration Utilization — Score: 3/3

**Evidence:** 19 environment variables are read, and every one drives actual behavior:

| Variable | Used In | Effect |
|---|---|---|
| `AUTH_ENABLED` | `dependencies.py:16`, `main.py:33,91` | Gates entire auth router + middleware |
| `WEBSOCKET_ENABLED` | `dependencies.py:17`, `main.py:36,95` | Gates WebSocket router |
| `OPENAI_API_KEY` | `llm_engine.py:53` | Initializes LLM client (or None) |
| `LLM_MODEL` | `llm_engine.py:54` | Model selection |
| `OPENAI_API_BASE` | `llm_engine.py:55` | Allows Ollama/local LLM backends |
| `JWT_SECRET_KEY` | `auth/service.py:23-26` | **Raises ValueError in production** if unset |
| `CORS_ORIGINS` | `main.py:71` | Configurable CORS allowlist |
| `RATE_LIMIT_AUTH` | `dependencies.py:20` | Configurable rate limit string |

The production guard on `JWT_SECRET_KEY` (`auth/service.py:24-25`) is a strong signal — AI-generated code rarely adds environment-specific safety checks. Feature flags actually gate entire code paths, not just logging.

### B3. Call Chain Completeness — Score: 2/3

**Full traces of core features:**

1. **New Game:** `POST /api/game/new` → `routers/game.py:32` → `reset_game_engine_for_session()` → `GameEngine.new_game()` → resets player/world/inventory/narrative → `_generate_room()` → `llm_engine.generate_room()` (or fallback) → returns `ActionResult` with map + state. **Complete.**

2. **Movement:** `POST /api/game/move` → validates direction → `engine.move()` → checks exits → `_generate_room()` if new → updates position → records narrative event → checks for enemies → optionally starts combat. **Complete.**

3. **Combat Attack:** `POST /api/game/combat/attack` → `engine.attack()` → `CombatEngine.attack()` → calculates damage with defense/crit → applies to enemy → enemy counterattack → processes status effects → victory/defeat resolution. **Complete.**

4. **Save/Load:** `POST /api/game/save` → `engine.save_to_database()` → `DatabaseRepository.save_game()` → serializes player/world/inventory/narrative → SQLite insert. Load reverses. **Complete.**

5. **NPC Dialogue:** `POST /api/game/talk` → `InteractionEngine.talk()` → loads NPC data from JSON → builds narrative context with NPC relationship → `llm.generate_dialogue()` → records in dialogue history + narrative memory. **Complete.**

**Incomplete/phantom features:**
- Glyphs system (`backend/glyphs/`) exists as code but is **never called** by any game route or engine.
- Foundry, layers, legends, WFC — referenced in README but code doesn't exist.
- No quest system, no crafting, no magic spells — all listed as "Completed" in README roadmap.

Score is 2 not 3 because claimed-but-absent features count against completeness.

### B4. Async Correctness — Score: 3/3

**Evidence:** All FastAPI route handlers are properly `async`. All LLM calls use `AsyncOpenAI` client with `await`. The `WebSocketManager` uses `asyncio.Lock()` for connection state mutations (`websocket_manager.py:37`). `SessionManager` uses `asyncio.Lock()` for engine creation (`session_manager.py`). The `GameEngine` factory uses a lazy-init lock (`game_engine.py:537`).

No blocking I/O in async handlers — file reads in `_load()` methods happen at initialization time (constructor), not in request handlers. `json.load()` calls in `llm_engine._load_game_data()` happen once at startup.

One minor issue: `interaction_engine.py:233` opens a file synchronously inside an async method (`talk()`), but this is an NPC data file read that happens on cache miss — acceptable given the small file sizes.

### B5. State Safety — Score: 2/3

**Evidence:** The project uses a session-based engine pattern (`game_engine.py` manages per-session state). Each session gets its own `PlayerState`, `WorldState`, `InventoryState`, `NarrativeMemory`, and `CombatEngine` instances — good isolation.

Thread safety measures:
- `asyncio.Lock()` in `WebSocketManager` (correct for async context)
- `asyncio.Lock()` in `SessionManager` for engine creation
- `_engines_lock` in `game_engine.py` for global engine dict

**Concern:** Every state module has a module-level `_global_state = None` singleton pattern. These globals are **not session-aware** — `get_player_state()` returns a single global instance. The session-based architecture in `game_engine.py` creates *separate* instances per session, bypassing these globals, but the globals still exist and could be accidentally used by a careless import. This is a latent bug if anyone calls `get_player_state()` instead of `engine.player`.

Cache has proper eviction: `LLMCache` uses `OrderedDict` with `max_size=30` and FIFO eviction (`llm_cache.py:87-88`). Session cleanup runs via `asyncio.create_task` with configurable timeout.

### B6. Security Depth — Score: 2/3

**Strengths:**
- Password hashing with bcrypt (`passlib.context.CryptContext`)
- JWT with explicit algorithm specification (`algorithms=[ALGORITHM]` — prevents algorithm confusion)
- Production guard on `JWT_SECRET_KEY` — raises `ValueError` if unset in production
- Parameterized SQL queries throughout `auth/service.py` — no string interpolation
- Input validation: `schemas.py:23-36` sanitizes player names with regex + path traversal check
- Rate limiting on auth endpoints (`slowapi`, 10/minute default)
- CORS with explicit origin allowlist
- Feature flags gate auth and WebSocket entirely

**Weaknesses:**
- Rate limiting **only** on auth endpoints — game API endpoints have no rate limiting
- `except Exception as e: raise HTTPException(500, detail=str(e))` in every router — leaks stack traces
- No Content-Security-Policy headers
- No request size limits beyond FastAPI defaults
- `auth/service.py:132` — `fromtimestamp()` without timezone (minor, can cause issues with timezone-unaware comparisons)
- Soft delete (`is_active=0`) but no data retention policy

### B7. Resource Management — Score: 3/3

| Metric | Value |
|--------|-------|
| Context managers (`with`) | 63 |
| Naked file opens | 0 |
| Cleanup handlers | 23 |
| Background task cleanup | Yes (`session_manager.py:154`) |

**Evidence:** Every file operation uses `with` blocks. Database connections use a `@contextmanager` wrapper (`auth/service.py:46-58`) with proper rollback-on-error. Session cleanup runs as a background task that's properly created via `asyncio.create_task`. The `lifespan` context manager in `main.py:44-52` handles startup/shutdown. LLM cache has size-bounded eviction.

**Domain B Total: 17/21 → 81.0%**

---

## Domain C: Interface Authenticity (30% weight)

### C1. API Consistency — Score: 3/3

**Evidence:** The API follows a consistent pattern:
- All endpoints under `/api/` prefix
- Consistent Pydantic request/response models (`schemas.py`)
- Proper OpenAPI tags and descriptions on every endpoint
- `ActionResponse` as the standard response type for game actions
- Consistent auth dependency injection via `Depends(get_optional_user)`
- Proper HTTP status codes (400 for bad input, 500 for server errors)
- CORS, rate limiting, and docs endpoints configured

### C2. UI Implementation Depth — Score: 2/3

**Evidence:** The frontend has real structure:
- 9 React components exported from `components/index.ts` (GameMap, PlayerStats, Inventory, Controls, Combat, Narrative, RoomItems, Dialogue, GameMenu)
- Custom `useGame` hook with proper `useState`, `useCallback`, `useRef` for abort controller, `useEffect` for initialization
- TypeScript types in `types/game.ts`
- API service layer in `services/api.ts` with proper error handling (`ApiError` class)
- Vite + Tailwind + PostCSS build pipeline
- Playwright E2E test suite (6 spec files)

**Gaps:**
- No React Router (single-page app without URL routing)
- No WebSocket client despite backend WebSocket support
- No `App.tsx` component rendering logic examined (barrel exports only)
- No authentication UI despite backend auth system
- Custom font pipeline claimed but `fonts/` directory doesn't exist

### C3. Frontend State Management — Score: 2/3

**Evidence:** `useGame.ts` is the single state management hook. It handles:
- Game state, loading state, error state, narrative, dialogue
- Prefetch with `AbortController` for cancellation
- `withLoading` wrapper that sets loading/error state uniformly
- Initial game load on mount via `useEffect`
- Proper cleanup of previous prefetch requests

This is adequate for the app's scale but has no external state management (no Redux, Zustand, or Context). All state lives in a single hook — this works for a game with one screen but would not scale to multiple views. No optimistic updates, no cache invalidation strategy beyond prefetch.

### C4. Security Infrastructure — Score: 2/3

**Evidence:** Backend security is real (see B6). Frontend has:
- API service that throws typed errors
- No credential storage visible (JWT flow exists backend-side but no frontend auth UI)

Auth is feature-flagged **off** by default. The security infrastructure exists in code but is not active in the default deployment path.

### C5. WebSocket Implementation — Score: 1/3

**Evidence:** `WebSocketManager` (`websocket_manager.py`) is a complete implementation with:
- Connection tracking by player ID
- Lock-based concurrent access
- Broadcast and targeted messaging
- Heartbeat/ping mechanism
- Dead connection cleanup
- Proper disconnect handling

But:
- **No frontend WebSocket client exists.** The entire WebSocket system is backend-only.
- WebSocket is feature-flagged **off** by default.
- The WebSocket router (`routers/websocket.py`) exists but is never connected to the game loop — game actions go through REST, not WebSocket.
- This is a complete-on-paper, disconnected-in-practice feature.

### C6. Error UX — Score: 2/3

**Evidence:**
- Frontend `ApiError` class preserves HTTP status codes
- `useGame` hook surfaces errors to component state
- Backend returns structured error responses via `HTTPException`
- Pydantic validation errors return 422 with field-level details
- Fallback room generation ensures the game never crashes due to LLM failure

No user-facing error messages are customized — all errors are raw backend strings. No retry UI, no offline handling, no graceful degradation messaging.

### C7. Observability — Score: 1/3

**Evidence:**
- `llm_engine.py` uses `logging.getLogger(__name__)` — the **only** file with proper logging
- `metrics.py` provides a `timed_llm_call` decorator — only used for LLM calls
- All other modules use `print()` for warnings
- No structured logging (no JSON logs, no correlation IDs)
- No request tracing
- No health metrics beyond `/api/health` (which is a static "healthy" response)
- No error rate tracking, no latency percentiles, no alerting hooks
- CI pipeline exists but no monitoring/alerting integration

**Domain C Total: 13/21 → 61.9%**

---

## Final Scoring

### Domain Scores

| Domain | Raw Score | Max | Percentage | Weight | Weighted |
|--------|-----------|-----|------------|--------|----------|
| A: Surface Provenance | 9 | 21 | 42.9% | 20% | 8.6% |
| B: Behavioral Integrity | 17 | 21 | 81.0% | 50% | 40.5% |
| C: Interface Authenticity | 13 | 21 | 61.9% | 30% | 18.6% |

### Authenticity Percentage

```
Authenticity = 8.6 + 40.5 + 18.6 = 67.6%
```

### Vibe-Code Confidence

```
Vibe-Code Confidence = 100 - 67.6 = 32.4
```

### Classification

| Range | Classification | This Project |
|-------|---------------|--------------|
| 0–15 | Human-Authored | |
| 16–35 | AI-Assisted | **32.4** |
| 36–60 | Substantially Vibe-Coded | |
| 61–85 | Predominantly Vibe-Coded | |
| 86–100 | Almost Certainly AI-Generated | |

**Classification: AI-Assisted (upper end)**

---

## Interpretation

This score may seem generous given that 89.8% of commits are literally attributed to "Claude." The reason is that the vibe-check framework weights **behavioral integrity at 50%**, and Tile-Crawler's core code is genuinely well-engineered. The combat engine has real math. The LLM integration has proper fallback chains. The state management uses session isolation with async locks. The auth system hashes passwords correctly. These aren't the hallmarks of unsupervised AI output — they suggest a developer who directed the AI with intent and reviewed the output.

Where the AI signature bleeds through is in the **surface** (Domain A) and **edges** (Domain C):
- The commit history is undeniably machine-generated
- The documentation massively overstates what exists
- The test suite is broad but shallow (281 tests, 1 error path)
- Zero TODOs, zero FIXMEs — no human ever lived in this code
- WebSocket is implemented backend-only with no frontend client
- The glyphs system is dead code that nothing calls

**Bottom line:** This is competent AI-generated code with clear human direction but insufficient human review. The developer told the AI *what* to build and got something that works, but never went back to stress-test edge cases, prune phantom documentation, or add the messy human artifacts (TODOs, workarounds, parametrized tests) that come from actually debugging code yourself.

---

## Remediation Priorities

### Critical (do these first)

1. **Prune the README.** Remove all references to GASR, Foundry, multi-layer rendering, WFC, custom fonts, sound effects, and everything in the "Completed Features" checklist that doesn't exist. The README currently describes a fantasy project. (`README.md` — entire "Advanced Systems" section, project structure listing, roadmap "Completed" items)

2. **Add error-path tests.** You have 281 tests and 1 `pytest.raises`. Add tests for: malformed LLM responses, database corruption, concurrent session access, inventory overflow, invalid item IDs, expired JWT tokens, missing environment variables.

3. **Delete dead code.** The `backend/glyphs/` package is never imported by the game. Either integrate it or remove it. Same for the module-level singleton getters (`get_player_state()`, etc.) that are bypassed by the session architecture.

### High Priority

4. **Fix error leakage.** Replace `raise HTTPException(500, detail=str(e))` with generic error messages. Internal exception details should not reach API consumers.

5. **Add rate limiting to game endpoints.** Currently only auth endpoints are rate-limited. A malicious client can spam `/api/game/move` or `/api/game/combat/attack` with no throttling.

6. **Add at least one custom exception.** Something like `GameNotStartedError`, `ItemNotFoundError`, `NotInCombatError` — replace the string-matching error checks with typed exceptions.

### Medium Priority

7. **Add observability.** Replace `print()` statements with `logging.getLogger(__name__)`. Add request logging middleware. Add error rate counters.

8. **Connect WebSocket to frontend or remove it.** A complete backend WebSocket system with no frontend client is dead weight.

9. **Add parametrized tests.** The damage formula, flee probability, and level-up scaling are perfect candidates for `@pytest.mark.parametrize`.

10. **Add WHY comments.** The `LLMCache` depth bucketing (`_depth_range`), the biome tile substitution logic, the NPC disposition auto-upgrade at 5 encounters — these deserve comments explaining the design rationale.

---

*This audit follows the Vibe-Code Detection Audit v2.0 framework. Its purpose is not to shame AI-assisted development but to identify where AI-generated code lacks meaningful human review so the developer can shore it up.*
