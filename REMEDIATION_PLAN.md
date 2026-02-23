# Tile-Crawler Remediation Plan

**Based on:** Vibe-Code Detection Audit v2.0 (VIBE_CHECK_REPORT.md)
**Current Score:** 32.4 Vibe-Code Confidence (AI-Assisted)
**Target Score:** <20 (Human-Authored classification)
**Date:** 2026-02-23

---

## Overview

This plan addresses every finding from the audit across 7 phases, ordered by
impact on both code quality and authenticity score. Each phase is independent
and can be merged separately. Estimated line counts are rough — the point is
scope, not precision.

**Phase order rationale:** Phases 1–3 fix things that are actively wrong
(lying docs, leaked errors, dead code). Phases 4–5 strengthen things that are
weak (tests, logging). Phases 6–7 remove or integrate orphaned features.

---

## Phase 1: Documentation Truth (Audit §A6)

**Goal:** Make the README describe the project that exists, not the project
that was imagined.

### 1.1 Strip phantom features from README.md

**File:** `README.md`

Remove or clearly mark as "Planned" every claim that references non-existent
code:

| Claim to remove/rewrite | Why |
|---|---|
| "GASR Glyph System: 80+ semantic glyph definitions" under Completed | `backend/glyphs/` exists but is never imported by the game loop |
| "Procedural Glyph Foundry: AI tile generation pipeline" | `backend/foundry/` does not exist |
| "Multi-Layer Rendering: 6-layer SNES-style compositing" | `backend/glyphs/layers.py`, `engine.py` do not exist |
| "Sound Effects: TTS-based procedural audio synthesis" | No audio code anywhere |
| Entire "Procedural Glyph Foundry" section (§🏭) | `grammar.py`, `edges.py`, `generator.py`, `validator.py`, `compiler.py` — none exist |
| "12 built-in palettes" | `data/palettes.json` does not exist |
| "Custom Font Tilesets" / `DungeonTiles.ttf` references | `frontend/src/fonts/` does not exist |
| "Wave Function Collapse-ready tile meshing" | No WFC code |
| Project structure listing `foundry/`, `layers.py`, `legends.py`, `engine.py`, `compiler.py` | None exist |
| Roadmap "Completed" checkmarks for the above items | Move to "Planned" |

**Actions:**
1. Rewrite the "Advanced Systems" section to say "Planned / In Progress"
2. Remove the `🏭 Procedural Glyph Foundry` section entirely (or move to `docs/design/`)
3. Fix the project structure tree to match the actual filesystem
4. Move unchecked items from "Completed Features ✅" to "Planned Features"
5. Remove the "6-Layer Rendering" code block (or label it as a design goal)
6. Remove `palettes.json` from the data file listing

### 1.2 Audit other documentation files

**Files:** `CHANGELOG.md`, `EVALUATION.md`, `REFOCUS_GUIDE.md`, `AUDIT_REPORT.md`

Cross-reference each against reality. These are internal docs so they matter
less, but any that reference glyph foundry, WFC, etc. should be updated.

### 1.3 Remove SEO keyword stuffing from README

**File:** `README.md`

Lines like "**AI roguelike** | **procedural game design** | **natural language
gaming**" and the repeated bold-keyword pattern throughout read as
AI-generated marketing copy. Rewrite the intro paragraph in a human voice.

---

## Phase 2: Error Handling Hardening (Audit §B1, §B6, §C6)

**Goal:** Stop leaking internal errors to API consumers. Add typed exceptions.
Improve security posture.

### 2.1 Create custom exception hierarchy

**New file:** `backend/exceptions.py`

```python
"""Game-specific exceptions for Tile-Crawler."""


class TileCrawlerError(Exception):
    """Base exception for all game errors."""
    pass


class GameNotStartedError(TileCrawlerError):
    """Raised when an action requires an active game but none exists."""
    pass


class NotInCombatError(TileCrawlerError):
    """Raised when a combat action is attempted outside combat."""
    pass


class ItemNotFoundError(TileCrawlerError):
    """Raised when an item is not found in room or inventory."""
    pass


class InvalidDirectionError(TileCrawlerError):
    """Raised for invalid movement directions."""
    pass


class SessionNotFoundError(TileCrawlerError):
    """Raised when a session cannot be resolved."""
    pass
```

### 2.2 Replace string-based error returns with exceptions

**Files to modify:**

| File | Current pattern | Replace with |
|---|---|---|
| `combat_engine.py:93-97` | `return ActionResult(success=False, message="Not in combat!")` | `raise NotInCombatError()` |
| `combat_engine.py:249-254` | Same for `flee()` | `raise NotInCombatError()` |
| `interaction_engine.py:45-50` | `"Cannot pick up items during combat!"` | `raise NotInCombatError("Cannot pick up items during combat")` |
| `interaction_engine.py:213-218` | `"Cannot talk during combat!"` | `raise NotInCombatError("Cannot talk during combat")` |
| `interaction_engine.py:67-72` | `"Item not found in this room"` | `raise ItemNotFoundError(item_id)` |
| `game_engine.py:161-165` | `"Cannot move while in combat!"` | `raise NotInCombatError()` |
| `game_engine.py:182-187` | `"Invalid direction"` | `raise InvalidDirectionError(direction)` |

### 2.3 Add exception handler middleware to sanitize 500 errors

**File:** `backend/main.py` — add after the rate limit handler:

```python
from fastapi import Request
from fastapi.responses import JSONResponse
from exceptions import TileCrawlerError

@app.exception_handler(TileCrawlerError)
async def game_error_handler(request: Request, exc: TileCrawlerError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "error_type": type(exc).__name__}
    )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"}
    )
```

### 2.4 Replace bare `except Exception` in routers

**Files:** All 6 router files (`game.py`, `combat.py`, `interaction.py`,
`inventory.py`, `auth.py`, `websocket.py`)

**Current pattern (13 occurrences across routers):**
```python
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))
```

**Replace with:** Let the custom exception handlers catch game errors.
Remove the try/except wrappers from router functions entirely — FastAPI's
exception handlers will do the right thing. Keep try/except only where you
need to transform an error (e.g., the prefetch endpoint that intentionally
returns `{"success": False}`).

### 2.5 Add exception chaining where context matters

**Files:** `llm_engine.py`, `database/repository.py`

Where exceptions are caught and re-raised or wrapped, use `raise X from Y`:

```python
# llm_engine.py:268 — currently
except Exception as e:
    logger.error(f"LLM room generation failed: {e}")
    return self._generate_fallback_room(...)

# No change needed here — fallback is intentional, not a re-raise.
# But in repository.py:
except Exception:
    conn.rollback()
    raise  # Add: raise SomethingUseful from original_exception
```

### 2.6 Add rate limiting to game endpoints

**File:** `backend/dependencies.py` — add a game rate limit:

```python
RATE_LIMIT_GAME = os.getenv("RATE_LIMIT_GAME", "60/minute")
```

**Files:** `routers/game.py`, `routers/combat.py`, `routers/interaction.py`,
`routers/inventory.py` — add `@limiter.limit(RATE_LIMIT_GAME)` to each
endpoint and pass `request: Request` as the first parameter.

---

## Phase 3: Dead Code Removal (Audit §A6, §B3)

**Goal:** Remove code that nothing calls. Reduce surface area.

### 3.1 Decision: glyphs/ package

The `backend/glyphs/` package (3 files, ~380 lines + 274-line test file) is
**never imported** by any game code. Only `tests/test_glyphs.py` imports it.

**Options:**
- **A) Delete it.** Remove `backend/glyphs/`, `backend/tests/test_glyphs.py`,
  and `data/glyphs.json`. Clean cut.
- **B) Keep it but mark as experimental.** Add a `# EXPERIMENTAL: not yet
  integrated into game loop` comment to `__init__.py`. Remove from test CI
  gate.

**Recommendation:** Option A. If the glyph system is ever needed, it can be
recovered from git history. Dead code that passes tests gives a false sense
of coverage.

### 3.2 Remove deprecated global engine functions

**File:** `backend/game_engine.py:593-613`

```python
def get_game_engine() -> GameEngine:          # DEPRECATED
def reset_game_engine() -> GameEngine:        # DEPRECATED
```

These are marked DEPRECATED and bypassed by the session architecture. However,
`routers/websocket.py:5,23,83-84` still imports and uses them:

```python
from game_engine import get_game_engine, reset_game_engine
...
engine = get_game_engine()          # line 23 — uses global, not session
reset_game_engine()                 # line 83 — same
```

**Action:**
1. Fix `routers/websocket.py` to use `get_game_engine_for_session()` and
   `reset_game_engine_for_session()` (requires passing a session ID through
   the WebSocket handshake).
2. Then delete `get_game_engine()` and `reset_game_engine()` from
   `game_engine.py`.
3. Also delete `_game_engine: Optional[GameEngine] = None` global.

### 3.3 Remove unused module-level singleton getters

**Files:** `player_state.py`, `world_state.py`, `narrative_memory.py`,
`inventory_state.py`

Each file has `get_X()` and `reset_X()` functions at module level. These
are used in two places:
1. `GameEngine.__init__()` calls all four `get_X()` functions (line 42-45).
2. Tests use them via fixtures.

Since `GameEngine.__init__` is only called inside `get_game_engine_for_session`
which immediately overwrites the state objects with session-specific ones
(lines 564-567), the `get_X()` globals are creating throwaway objects.

**Action:** Refactor `GameEngine.__init__` to accept state objects as
parameters instead of calling globals:

```python
class GameEngine:
    def __init__(self, world, narrative, inventory, player):
        self.world = world
        self.narrative = narrative
        self.inventory = inventory
        self.player = player
        ...
```

Then update `get_game_engine_for_session` and `reset_game_engine_for_session`
to pass session state directly. After that, the module-level singletons can
be deleted from all four state files.

### 3.4 Remove phantom dependencies from requirements.txt

**File:** `backend/requirements.txt`

- Remove `aiofiles>=23.2.1` — never imported anywhere in the codebase.
- Remove `starlette>=0.35.1` — transitive dependency of FastAPI, explicit
  declaration serves no purpose.
- Consider removing `typing-extensions>=4.9.0` — stdlib since Python 3.8,
  and the project's CI runs Python 3.11.

### 3.5 Clean up redundant documentation files

**Files to evaluate:**
- `docs/archive/` — 8 files describing systems that don't exist (DLP-Powered,
  Diffable-Worlds, KEYWORDS, art-studio, entity-npc-system, save-system,
  glyph-rendering-system). If any of these describe implemented features,
  keep them. Otherwise, delete or consolidate into a single `DESIGN_IDEAS.md`.
- `PHASE0_BASELINE.md`, `REFOCUS_GUIDE.md`, `EVALUATION.md` — these are
  process artifacts from the AI-driven refactoring phases. Keep if useful for
  project history; otherwise archive.

---

## Phase 4: Test Quality Upgrade (Audit §A3)

**Goal:** Transform tests from "proves it doesn't crash" to "proves it
handles failure correctly." Target: 20+ error-path tests, 5+
parametrized test cases.

### 4.1 Add error-path tests to combat

**File:** `backend/tests/test_combat_engine.py`

Add tests for:
```python
class TestCombatEdgeCases:
    async def test_attack_after_combat_ends(self, combat_engine):
        """Attack after victory should fail gracefully."""

    async def test_start_combat_with_empty_enemy_dict(self, combat_engine):
        """Starting combat with {} should use sane defaults."""

    async def test_double_start_combat(self, combat_engine):
        """Starting combat when already in combat."""

    async def test_flee_when_dead(self, combat_engine, player):
        """Flee attempt when player HP is already 0."""

    async def test_attack_with_negative_defense(self, combat_engine):
        """Enemy with negative defense (data corruption scenario)."""
```

### 4.2 Add error-path tests to inventory

**File:** `backend/tests/test_inventory_state.py`

```python
class TestInventoryErrors:
    def test_remove_item_not_in_inventory(self, inventory):
        success, msg = inventory.remove_item("nonexistent")
        assert success is False

    def test_use_non_consumable(self, inventory):
        """Using an equipment item should fail."""

    def test_equip_non_equippable(self, inventory):
        """Equipping a consumable should fail."""

    def test_add_item_when_full(self, inventory):
        """Adding to a full inventory should fail."""

    def test_remove_gold_insufficient(self, inventory):
        """Removing more gold than available should fail."""

    def test_unequip_item_not_equipped(self, inventory):
        """Unequipping something that isn't equipped."""
```

### 4.3 Add error-path tests to API layer

**File:** `backend/tests/test_api.py`

```python
class TestAPIErrors:
    def test_move_invalid_direction(self, test_client):
        resp = test_client.post("/api/game/move", json={"direction": "sideways"})
        assert resp.status_code == 400

    def test_take_nonexistent_item(self, test_client):
        test_client.post("/api/game/new", json={})
        resp = test_client.post("/api/game/take", json={"item_id": "unobtainium"})
        assert resp.status_code == 200
        assert resp.json()["success"] is False

    def test_attack_not_in_combat(self, test_client):
        test_client.post("/api/game/new", json={})
        resp = test_client.post("/api/game/combat/attack")
        assert resp.status_code in [200, 400]
        assert resp.json()["success"] is False

    def test_load_with_no_saves(self, test_client):
        test_client.post("/api/game/new", json={})
        resp = test_client.post("/api/game/load")
        assert resp.json()["success"] is False

    def test_player_name_injection(self, test_client):
        resp = test_client.post("/api/game/new", json={"player_name": "../../../etc/passwd"})
        assert resp.status_code == 422  # Pydantic validation
```

### 4.4 Add error-path tests to auth

**File:** `backend/tests/test_auth.py`

```python
class TestAuthErrors:
    def test_login_wrong_password(self, auth_service):
        """Login with incorrect password returns None."""

    def test_login_nonexistent_user(self, auth_service):
        """Login for user that doesn't exist."""

    def test_register_duplicate_username(self, auth_service):
        """Registering with taken username returns None."""

    def test_verify_expired_token(self, auth_service):
        """Expired JWT should return None."""

    def test_verify_tampered_token(self, auth_service):
        """Modified JWT should fail verification."""

    def test_change_password_wrong_old(self, auth_service):
        """Changing password with wrong old password should fail."""
```

### 4.5 Add parametrized tests

**File:** `backend/tests/test_combat_engine.py`

```python
@pytest.mark.parametrize("player_attack,enemy_defense,expected_damage", [
    (5, 0, 5),      # No defense
    (5, 4, 3),      # Partial defense (5 - 4//2 = 3)
    (5, 100, 1),    # Massive defense, minimum 1
    (1, 0, 1),      # Minimum attack
    (100, 10, 95),  # High attack
])
async def test_damage_formula(self, combat_engine, player, player_attack, enemy_defense, expected_damage):
    ...
```

**File:** `backend/tests/test_player_state.py`

```python
@pytest.mark.parametrize("heal_amount,current_hp,max_hp,expected_heal", [
    (50, 50, 100, 50),   # Partial heal
    (200, 50, 100, 50),  # Overheal capped
    (10, 100, 100, 0),   # Already full
    (0, 50, 100, 0),     # Zero heal
])
def test_heal_formula(self, player, heal_amount, current_hp, max_hp, expected_heal):
    ...
```

**File:** `backend/tests/test_game_engine.py` (new or extend test_game_flow)

```python
@pytest.mark.parametrize("depth,expected_biomes", [
    (0, {"dungeon", "cave"}),
    (3, {"dungeon", "crypt", "ruins"}),
    (8, {"volcano", "temple"}),
    (10, {"void"}),
])
def test_biome_selection_by_depth(self, depth, expected_biomes):
    ...
```

### 4.6 Replace trivial assertions

**All test files** — grep for `is not None` and replace with meaningful
assertions:

```python
# Before
assert result is not None

# After
assert result.success is True
assert result.message == "expected message"
```

Target: reduce 44 trivial assertions to <10 (keep only where nullability is
genuinely the thing under test).

### 4.7 Fix the test that accepts 500 as valid

**File:** `backend/tests/test_game_flow.py:248`

```python
# Before
assert move_resp.status_code in [200, 500]  # Accepts crashes

# After
assert move_resp.status_code == 200
# OR test the specific error behavior:
assert move_resp.status_code in [200, 400]
assert "error" in move_resp.json() or move_resp.json().get("success") is not None
```

---

## Phase 5: Observability (Audit §C7)

**Goal:** Replace `print()` with structured logging. Add request tracing.

### 5.1 Add logging to all backend modules

**Files to modify:** Every `.py` file in `backend/` that currently uses
`print()` for warnings.

**Pattern to apply:**

```python
import logging

logger = logging.getLogger(__name__)

# Replace:
print(f"Warning: Could not load {filename}: {e}")
# With:
logger.warning("Failed to load %s: %s", filename, e)
```

**Specific files:**
| File | Lines with `print()` | Replace with |
|---|---|---|
| `llm_engine.py:116,125` | `print(f"Warning: ...")` | `logger.warning(...)` |
| `llm_engine.py:880` | `print(f"LLM item description failed: {e}")` | `logger.error(...)` |
| `llm_engine.py:921` | `print(f"LLM story summary failed: {e}")` | `logger.error(...)` |
| `world_state.py:69` | `print(f"Warning: Could not load world state: {e}")` | `logger.warning(...)` |
| `player_state.py:75` | `print(f"Warning: Could not load player state: {e}")` | `logger.warning(...)` |
| `inventory_state.py:63` | `print(f"Warning: Could not load inventory: {e}")` | `logger.warning(...)` |
| `narrative_memory.py:83` | `print(f"Warning: Could not load narrative: {e}")` | `logger.warning(...)` |
| `session_manager.py:152` | `print(f"Session cleanup: ...")` | `logger.info(...)` |
| `game_engine.py:523` | `print(f"Prefetch failed for {direction}: {e}")` | `logger.warning(...)` |
| `main.py:47-52` | `print("Tile-Crawler Backend Starting...")` | `logger.info(...)` |

### 5.2 Add request logging middleware

**File:** `backend/main.py` — add middleware:

```python
import time
import logging

request_logger = logging.getLogger("tile_crawler.requests")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    request_logger.info(
        "%s %s %d %.2fs",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response
```

### 5.3 Make health endpoint dynamic

**File:** `backend/routers/health.py`

Currently returns static `"healthy"`. Enhance:

```python
@router.get("/api/health")
async def health_check():
    llm_engine = get_llm_engine()
    session_mgr = get_session_manager()

    return HealthResponse(
        status="healthy" if llm_engine.is_available() else "degraded",
        llm_available=llm_engine.is_available(),
        version="0.1.0",
    )
```

### 5.4 Configure logging in main.py

**File:** `backend/main.py` — add at top:

```python
import logging

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
```

---

## Phase 6: WebSocket Decision (Audit §C5)

**Goal:** Either connect WebSocket to frontend or remove it.

### Option A: Remove (Recommended if WebSocket isn't needed soon)

1. Delete `backend/websocket_manager.py` (226 lines)
2. Delete `backend/routers/websocket.py` (134 lines)
3. Delete `backend/tests/test_websocket_manager.py` (249 lines)
4. Remove `WEBSOCKET_ENABLED` from `dependencies.py`
5. Remove WebSocket conditional imports from `main.py:36-37,95-97`
6. Remove WebSocket tag from `main.py:37`
7. Update README to remove WebSocket from "Technical Features"
8. Remove WebSocket E2E tests if any reference it

**Savings:** ~609 lines of dead code removed.

### Option B: Integrate (If WebSocket is on the roadmap)

1. Fix `routers/websocket.py` to use session-based engine (currently uses
   deprecated global `get_game_engine()`)
2. Add WebSocket client to frontend (`frontend/src/services/ws.ts`)
3. Add `useWebSocket` hook to `frontend/src/hooks/`
4. Wire the `useGame` hook to use WebSocket instead of REST when connected
5. Add reconnection logic with exponential backoff
6. Add WebSocket E2E tests

### Decision criteria

If no one is actively building multiplayer or real-time features, **Option A**.
The code can be recovered from git history. Dead code that passes tests
inflates coverage numbers and creates a false sense of completeness.

---

## Phase 7: Human Artifacts (Audit §A2, §A5)

**Goal:** Add the organic development markers that real projects accumulate
naturally. This is NOT about faking authenticity — it's about doing the work
that makes code maintainable.

### 7.1 Add WHY comments where decisions aren't obvious

| File:Line | What to explain |
|---|---|
| `llm_cache.py:27-36` | Why depth is bucketed into ranges instead of exact values |
| `llm_engine.py:153-160` | Why the cache lookup tries all enemy/npc variants |
| `combat_engine.py:104` | Why defense is halved (design decision for balance) |
| `combat_engine.py:26` | Why 5% crit chance was chosen |
| `narrative_memory.py:308-309` | Why disposition auto-upgrades at exactly 5 encounters |
| `narrative_memory.py:141-151` | Why event trimming preserves importance over recency |
| `game_engine.py:296` | Why NEW_EXIT_CHANCE is 0.5 (50% — what does this mean for dungeon density?) |
| `game_engine.py:123-126` | Why `new_game()` calls `.reset()` instead of `reset_X()` globals |
| `session_manager.py:28` | Why session data lives on disk instead of in-memory only |
| `llm_engine.py:66-71` | Why temperature differs per context (exploration vs combat vs dialogue) |

### 7.2 Add TODO markers for known gaps

```python
# game_engine.py — near prefetch
# TODO: prefetch should be rate-limited per session to prevent abuse

# combat_engine.py — near loot generation
# TODO: loot tables are simplified — integrate data/loot_tables.json

# interaction_engine.py:229 — NPC data loading
# TODO: cache NPC data instead of re-reading JSON on every talk()

# auth/service.py:132 — token verification
# TODO: fromtimestamp() should use timezone.utc for consistency

# main.py — CORS
# TODO: tighten CORS origins for production deployment

# websocket_manager.py — if kept
# TODO: add heartbeat timeout to disconnect stale connections
```

### 7.3 Break the singleton naming monotony

The `get_X()` / `reset_X()` pattern is identical across 8 files. After Phase
3.3 eliminates most of these, the remaining ones (if any) should use
context-appropriate names. For example:

- `get_llm_engine()` → fine, keep it (it's a true singleton)
- `get_auth_service()` → fine, keep it
- `get_session_manager()` → fine, keep it
- `get_llm_cache()` → fine, keep it

The repetition that matters was in the state objects (player, world,
inventory, narrative) — Phase 3.3 removes those.

---

## Phase Summary

| Phase | Files Changed | Lines Added | Lines Removed | Audit Criteria Addressed |
|---|---|---|---|---|
| 1. Documentation Truth | ~5 markdown files | ~20 | ~200 | A6 |
| 2. Error Handling | ~12 Python files | ~120 | ~50 | B1, B6, C6 |
| 3. Dead Code Removal | ~15 files | ~30 | ~800+ | A6, B3, A4, A5 |
| 4. Test Quality | ~8 test files | ~400 | ~50 | A3 |
| 5. Observability | ~12 Python files | ~80 | ~20 | C7 |
| 6. WebSocket Decision | 3-7 files | 0-200 | 0-609 | C5 |
| 7. Human Artifacts | ~10 Python files | ~40 | 0 | A2, A5 |

### Expected Score Impact

| Domain | Current | After Remediation | Delta |
|---|---|---|---|
| A: Surface Provenance | 42.9% | ~65% | +22 |
| B: Behavioral Integrity | 81.0% | ~90% | +9 |
| C: Interface Authenticity | 61.9% | ~75% | +13 |
| **Weighted Total** | **67.6%** | **~80%** | **+12** |
| **Vibe-Code Confidence** | **32.4** | **~20** | **-12** |

This would bring the project to the Human-Authored / AI-Assisted boundary —
which is the honest truth for a project that was AI-generated with meaningful
human direction, and then remediated with human review.

---

## Execution Order for Single Developer

If you're working through this alone, the most impactful order is:

1. **Phase 1** (30 min) — Biggest honesty win. Just editing markdown.
2. **Phase 3** (1-2 hrs) — Removing dead code is satisfying and shrinks scope.
3. **Phase 2** (2-3 hrs) — Error handling requires touching many files but is
   mechanical.
4. **Phase 4** (3-4 hrs) — Test writing is the most time-consuming but highest
   value.
5. **Phase 5** (1-2 hrs) — Logging is mechanical search-and-replace.
6. **Phase 6** (30 min or 4 hrs) — Depends on keep vs delete decision.
7. **Phase 7** (1 hr) — Adding comments requires understanding the code,
   which you'll have after phases 1-6.

---

*This plan was generated from the Vibe-Code Detection Audit v2.0 findings.
Each phase can be implemented and merged independently.*
