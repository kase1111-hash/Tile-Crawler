# Tile-Crawler Software Audit Report

**Audit Date:** 2026-01-28
**Auditor:** Claude Code
**Scope:** Full codebase correctness and fitness for purpose audit

---

## Executive Summary

Tile-Crawler is a well-architected LLM-powered dungeon crawler with sophisticated features including procedural world generation, narrative memory, turn-based combat, and a custom glyph rendering system. The codebase demonstrates good software engineering practices overall, but has **critical architectural issues** that prevent it from functioning correctly in multi-user scenarios.

### Overall Assessment: **NEEDS REMEDIATION**

The software functions correctly for **single-user local development** but has fundamental issues that make it **unsuitable for multi-user deployment** without architectural changes.

---

## Critical Issues (Must Fix)

### 1. Global Singleton State Sharing - Multi-User Bug
**Severity:** CRITICAL
**Files:** `game_engine.py`, `world_state.py`, `player_state.py`, `inventory_state.py`, `narrative_memory.py`

**Problem:** All game state managers use global singleton patterns. Every user connecting to the same server instance shares the SAME game state.

```python
# game_engine.py:940-949
_game_engine: Optional[GameEngine] = None

def get_game_engine() -> GameEngine:
    global _game_engine
    if _game_engine is None:
        _game_engine = GameEngine()
    return _game_engine
```

**Impact:**
- If User A moves north, User B sees the change
- If User A starts combat, User B is also in combat
- Save/load operations affect all users
- This breaks fundamental game functionality for any deployment beyond single-user

**Recommendation:** Implement session-based or user-based game state management. Store state per authenticated user ID, not globally.

---

### 2. Password Exposure in Query Parameters
**Severity:** CRITICAL
**File:** `main.py:355-358`

**Problem:** The change-password endpoint accepts passwords as query parameters:

```python
async def change_password(
    old_password: str = Query(description="Current password"),
    new_password: str = Query(min_length=6, description="New password"),
    ...
)
```

**Impact:**
- Passwords logged in server access logs
- Passwords visible in browser history
- Passwords exposed in network monitoring tools
- Violates OWASP security guidelines

**Recommendation:** Change to POST body with Pydantic model:
```python
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)
```

---

### 3. WebSocket Race Conditions
**Severity:** HIGH
**File:** `websocket_manager.py:189-205`

**Problem:** Several methods access `_connections` without the async lock:

```python
def update_last_ping(self, player_id: str) -> None:
    if player_id in self._connections:  # No lock!
        self._connections[player_id].last_ping = datetime.now()

def is_connected(self, player_id: str) -> bool:
    return player_id in self._connections  # No lock!

def get_connected_players(self) -> Set[str]:
    return set(self._connections.keys())  # No lock!
```

**Impact:** Race conditions when checking connection state while another coroutine modifies connections, leading to potential KeyError exceptions or stale data.

**Recommendation:** Wrap all `_connections` access with `async with self._lock`.

---

## High Severity Issues

### 4. Deprecated datetime.utcnow() Usage
**File:** `auth/service.py:108`

Uses deprecated `datetime.utcnow()` which can cause timezone issues. Replace with:
```python
from datetime import datetime, timezone
expire = datetime.now(timezone.utc) + expires_delta
```

### 5. LLM Response Parsing Without Validation
**File:** `llm_engine.py:188-191`

LLM JSON responses are parsed and passed to Pydantic models without error boundaries. Malformed output could crash the application.

```python
content = response.choices[0].message.content
data = json.loads(content)  # Could fail if LLM returns invalid JSON
return RoomGenerationResponse(**data)  # Could fail if schema doesn't match
```

**Recommendation:** Add validation:
```python
try:
    data = json.loads(content)
    return RoomGenerationResponse.model_validate(data)
except (json.JSONDecodeError, ValidationError) as e:
    logger.warning(f"LLM returned invalid response: {e}")
    return self._generate_fallback_room(...)
```

### 6. No Rate Limiting
**Files:** `main.py` (all endpoints)

No rate limiting exists on any API endpoint. An attacker could:
- Exhaust LLM API credits with repeated room generation requests
- DOS the server with request flooding
- Brute-force authentication endpoints

**Recommendation:** Add FastAPI rate limiting middleware (e.g., `slowapi`).

### 7. Predictable Default JWT Secret
**File:** `auth/service.py:26`

```python
SECRET_KEY = _jwt_secret or "tile-crawler-dev-secret-key-not-for-production"
```

While production mode is checked, the fallback secret is hardcoded and easily discoverable. Any deployment without proper configuration is vulnerable.

### 8. Overly Permissive CORS Configuration
**File:** `main.py:276-282`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["*"],  # Too permissive
    allow_headers=["*"],  # Too permissive
)
```

**Recommendation:** Specify only the HTTP methods and headers actually needed.

---

## Medium Severity Issues

### 9. File I/O Race Conditions
**Files:** `world_state.py:89`, `player_state.py:107`, etc.

State files are written without file locking. Concurrent saves could corrupt data.

### 10. Hardcoded File Paths
**Files:** Multiple state files

```python
def __init__(self, save_path: str = "world_state.json"):
```

Files created in working directory instead of designated data folder. Could cause permission issues in different deployment scenarios.

### 11. Missing Async Context in rest()
**File:** `game_engine.py:745`

The `rest()` method is synchronous while other action methods are async:
```python
def rest(self) -> ActionResult:  # Should be: async def rest(...)
```

### 12. No Input Sanitization for player_name
**File:** `main.py:37-43`

While length is validated, special characters aren't sanitized. Could cause issues if player names are used in file paths or injected into prompts.

---

## Low Severity / Code Quality Issues

### 13. Unused Import
**File:** `llm_engine.py:10`

```python
import re  # Never used
```

### 14. Magic Numbers
**File:** `game_engine.py:313-314`

```python
if random.random() < 0.05:  # What is 0.05?
    damage *= 2
```

Should use named constants:
```python
CRITICAL_HIT_CHANCE = 0.05
```

### 15. Inconsistent Error Handling
Different endpoints handle errors differently - some return 500, others let exceptions propagate.

### 16. Test State Isolation
**File:** `backend/tests/`

Some test fixtures don't reset global singletons, which could cause test pollution.

### 17. Frontend Auto-Save Frequency
**File:** `frontend/src/App.tsx:260`

Auto-saves every 60 seconds regardless of changes, creating unnecessary server load.

---

## Positive Findings

1. **Well-Organized Architecture** - Clear separation of concerns with dedicated modules for game logic, LLM integration, state management, and rendering

2. **Strong Type Safety** - Comprehensive Pydantic models provide excellent data validation

3. **Good API Documentation** - OpenAPI/Swagger docs with detailed endpoint descriptions and examples

4. **Secure Password Handling** - bcrypt with proper CryptContext configuration

5. **Comprehensive Test Structure** - 13 test modules covering major subsystems

6. **Graceful Degradation** - LLM failures fall back to procedural generation

7. **Clean React Architecture** - Well-structured hooks and components with proper state management

8. **Database Abstraction** - Repository pattern supports both SQLite and PostgreSQL

9. **WebSocket Cleanup** - Proper connection lifecycle management with dead connection removal

10. **Narrative Memory System** - Sophisticated rolling context window for LLM story continuity

---

## Recommendations Summary

### Immediate (Before Any Multi-User Deployment)
1. Replace global singletons with user-scoped state management
2. Move passwords from query parameters to request body
3. Add async locks to all WebSocket connection checks

### Short-Term
4. Add rate limiting to all API endpoints
5. Replace deprecated datetime.utcnow() calls
6. Add proper LLM response validation with fallbacks
7. Configure stricter CORS settings

### Long-Term
8. Implement file locking for state persistence
9. Add comprehensive input sanitization
10. Create named constants for magic numbers
11. Improve test isolation with proper fixture teardown

---

## Fitness for Purpose Assessment

| Use Case | Status | Notes |
|----------|--------|-------|
| Single-user local development | **SUITABLE** | Works correctly |
| Single-user production deployment | **NEEDS FIXES** | Security issues need addressing |
| Multi-user deployment | **NOT SUITABLE** | Critical architecture issue |
| LLM-powered gameplay | **SUITABLE** | Good fallback handling |
| Real-time WebSocket updates | **PARTIAL** | Race condition risks |

---

## Conclusion

Tile-Crawler is an impressive technical achievement that demonstrates sophisticated integration of LLM content generation with roguelike game mechanics. The codebase is well-organized and maintainable.

However, the **global singleton architecture** is a fundamental design flaw that makes the current implementation unsuitable for any deployment with more than one concurrent user. This should be addressed as the highest priority before production deployment.

The security issues around password handling and rate limiting should be addressed before any public-facing deployment.

Once the critical issues are resolved, the software would be well-suited for its intended purpose as an LLM-powered dungeon crawler.
