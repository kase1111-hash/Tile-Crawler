# Tile-Crawler

AI-powered roguelike/dungeon crawler game where LLMs act as dynamic AI dungeon masters, generating text-based tile grids rendered in-browser using custom font tilesets.

## Tech Stack

**Backend**: FastAPI (Python), Pydantic, OpenAI/Ollama LLM integration, JWT auth, WebSockets, SQLite/PostgreSQL
**Frontend**: React 18 + TypeScript, Vite, Tailwind CSS, Playwright (E2E)
**Deployment**: Docker, Docker Compose, Nginx

## Project Structure

```
backend/               # FastAPI server
  main.py             # API entry point (30+ endpoints)
  game_engine.py      # Core game logic (actions, combat, NPCs)
  llm_engine.py       # OpenAI/Ollama integration
  world_state.py      # Room persistence by coordinates
  narrative_memory.py # Story continuity (rolling 10-event log)
  inventory_state.py  # Player inventory with equipment slots
  player_state.py     # Stats, progression, status effects
  audio_engine.py     # TTS-based procedural audio
  auth/               # JWT authentication system
  database/           # Repository pattern for persistence
  glyphs/             # GASR Glyph System (80+ semantic glyphs)
  foundry/            # Procedural tile generation via grammar
  tests/              # 260+ pytest unit tests

frontend/              # React TypeScript frontend
  src/
    App.tsx           # Main component with pseudo-3D rendering
    components/       # GameMap, Controls, Inventory, Combat, Dialogue, etc.
    hooks/            # useGame, useGameWebSocket, useAudio
    services/         # api.ts, websocket.ts, audioEngine.ts
    types/game.ts     # TypeScript interfaces

data/                  # Game content JSON (glyphs, biomes, enemies, items, NPCs, quests)
docs/                  # API reference and design docs
```

## Quick Commands

```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Docker (recommended)
docker-compose up -d              # Production
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up  # Dev

# Testing
cd backend && pytest tests/ -v                    # Backend tests
cd frontend && npm run test:e2e                   # E2E tests
make test-all                                     # All tests

# Makefile shortcuts
make help    # Show all commands
make build   # Build Docker images
make up      # Start services
make down    # Stop services
make dev     # Development mode
make logs    # View logs
```

## Environment Configuration

```bash
# OpenAI (cloud)
OPENAI_API_KEY=sk-your-key
LLM_MODEL=gpt-4o-mini

# Ollama (local, free)
OPENAI_API_KEY=ollama
OPENAI_API_BASE=http://localhost:11434/v1
LLM_MODEL=llama3.2
```

## Key Patterns

- **Singleton Pattern**: Game engine via `get_game_engine()` with reset for testing
- **Repository Pattern**: Database abstraction in `backend/database/repository.py`
- **State Modules**: Four independent state modules (world, narrative, inventory, player) sync with database
- **GASR Glyph System**: Unicode PUA (E000-EAFF) for semantic tile definitions
- **6-Layer Rendering**: SNES-style compositing (background, structures, entities, effects, lighting, UI)
- **Custom Hooks**: `useGame` for centralized state, `useGameWebSocket` for real-time updates

## API Endpoints

- `POST /api/game/new` - Start new game
- `POST /api/game/move/{direction}` - Move (north/south/east/west)
- `POST /api/game/attack|flee|take|use|talk|rest` - Actions
- `GET /api/game/state` - Current game state
- `POST /api/game/save|load` - Persistence
- `POST /auth/register|login|logout` - Authentication
- `WS /ws/{player_id}` - Real-time updates
- `GET /docs` - Swagger UI

## Testing

Backend tests use pytest with asyncio. Run specific tests with:
```bash
pytest tests/test_api.py -v                # API tests
pytest tests/test_game_flow.py -v          # Game flow
pytest tests/test_auth.py -v               # Authentication
pytest tests/ --cov=. --cov-report=term    # With coverage
```

Frontend E2E tests use Playwright:
```bash
npm run test:e2e           # Headless
npm run test:e2e:ui        # Interactive
npm run test:e2e:headed    # Visible browser
```

## Game Constants

- Critical Hit: 5% chance, 2x multiplier
- New Exit Chance: 50%, Stairs: 10%
- Max Dungeon Depth: 10 floors
- Flee Base Chance: 50%
- Narrative Memory: Last 10 events

## Data Files

All game content in `data/`:
- `glyphs.json` - 80+ semantic glyph definitions
- `biomes.json` - 8 biomes (Dungeon, Cave, Crypt, Ruins, Temple, Forest, Volcano, Void)
- `enemies.json`, `items.json`, `npcs.json`, `quests.json` - Game entities
- `palettes.json` - 12 color palette system for tile generation

## Key Documentation

- `README.md` - Project overview and gameplay
- `SPEC.md` - Technical specification (66KB)
- `CONTRIBUTING.md` - Development guidelines
- `docs/api/api-reference.md` - API documentation
