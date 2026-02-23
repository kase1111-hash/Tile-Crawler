Tile-Crawler
An LLM-Powered Dungeon Crawler

Tile-Crawler is a roguelike dungeon crawler where an LLM acts as the dungeon master. Rooms, enemies, items, and NPC dialogue are generated dynamically by the AI, while a FastAPI backend tracks world state, narrative memory, and inventory. A React frontend renders the ASCII tile maps and provides the game UI.

## Overview

Instead of hardcoded room layouts and scripted encounters, Tile-Crawler sends context (your position, recent events, inventory) to an LLM and gets back a JSON room with a tile map, description, enemies, and items. Previously explored rooms are persisted so the world stays consistent as you backtrack.
```
Player input (move, talk, take, use)
       ↓
FastAPI Backend → LLM Engine → generates room JSON
       ↓                ↓
World Memory    Narrative Memory    Inventory
       ↓
React Frontend renders ASCII tile map + UI
```

## Features

**Gameplay:**
- LLM-generated rooms with tile maps, enemies, NPCs, and items
- Persistent world memory — revisited rooms stay consistent
- Narrative memory — rolling event log gives the LLM story context
- Turn-based combat with damage formulas, crits, flee mechanics
- NPC dialogue with relationship tracking across encounters
- Inventory system with consumables, equipment, and gold

**Technical:**
- FastAPI backend with session-based state isolation
- OpenAI / compatible LLM integration with fallback room generation
- SQLite database persistence with save/load
- JWT authentication (feature-flagged, off by default)
- React + TypeScript + Vite + Tailwind frontend
- Playwright E2E tests + pytest backend tests (280+)
- CI/CD pipeline with GitHub Actions

### Tile Map Characters

The LLM generates rooms as text grids using these characters:

```
#  Wall        .  Floor       @  Player
!  Item        ☺  NPC         ≈  Water
^  Trap        +  Door        $  Treasure
```

## Project Structure

```
tile-crawler/
├── backend/
│   ├── main.py                  # FastAPI app, middleware, lifespan
│   ├── game_engine.py           # Core game loop and state management
│   ├── llm_engine.py            # OpenAI integration, prompt building, fallbacks
│   ├── combat_engine.py         # Turn-based combat: damage, crits, flee
│   ├── interaction_engine.py    # NPC dialogue, item use, resting
│   ├── world_state.py           # Room persistence by coordinate
│   ├── narrative_memory.py      # Rolling event log for LLM context
│   ├── player_state.py          # Stats, leveling, status effects
│   ├── inventory_state.py       # Items, equipment, gold
│   ├── session_manager.py       # Per-user session isolation
│   ├── llm_cache.py             # LRU cache for LLM room responses
│   ├── metrics.py               # LLM call latency tracking
│   ├── schemas.py               # Pydantic request/response models
│   ├── dependencies.py          # Feature flags, shared deps
│   ├── routers/                 # API route handlers
│   ├── auth/                    # JWT auth (feature-flagged)
│   ├── database/                # SQLite persistence, repository pattern
│   ├── glyphs/                  # Glyph registry (not yet integrated)
│   └── tests/                   # pytest suite (280+ tests)
├── data/
│   ├── biomes.json              # 8 biome configurations
│   ├── enemies.json             # Enemy stat templates
│   ├── items.json               # Item definitions
│   ├── npcs.json                # NPC definitions
│   ├── tiles.json               # Tile character mappings
│   ├── glyphs.json              # Glyph definitions
│   ├── loot_tables.json         # Loot drop tables
│   └── room_templates.json      # Fallback room templates
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main React component
│   │   ├── components/          # 9 UI components
│   │   ├── hooks/useGame.ts     # Game state management hook
│   │   ├── services/api.ts      # REST API client
│   │   ├── types/game.ts        # TypeScript type definitions
│   │   └── utils/tileGlyphs.ts  # Tile rendering utilities
│   ├── e2e/                     # Playwright E2E tests (6 specs)
│   ├── public/fonts/            # TileCrawler.otf custom font
│   └── vite.config.ts           # Vite build config
├── docs/                        # Design docs and API reference
├── .github/workflows/ci.yml     # CI pipeline
└── docker-compose.yml           # Docker deployment
```

## How to Play

### Controls

**Movement:**
- **NORTH** - Move up
- **SOUTH** - Move down
- **EAST** - Move right
- **WEST** - Move left

**Actions:**
- **TALK** - Speak with NPCs in your current location
- **TAKE** - Pick up items you find
- **USE** - Utilize items from your inventory

### Gameplay Loop

1. **Start** in a procedurally generated dungeon
2. **Explore** by moving through rooms
3. **Discover** NPCs, items, and narrative events
4. **Interact** with the world through commands
5. **Experience** a coherent story maintained by the AI

### Example Session
```
> NORTH
You step into a corridor of cold stone. Torches flicker weakly on 
the walls, casting dancing shadows across ancient carvings.

> TAKE torch
You pick up an old torch. The flame sputters but holds steady.
Inventory: ["torch"]

> EAST
A narrow bridge crosses a dark chasm. The wind howls from below.

> TALK
A hooded figure emerges from the shadows.
"The deeper passages hold secrets," they whisper, "but few return."

> USE torch
You raise the torch high. Its light reveals glyphs on the bridge 
supports - a warning in an old tongue.
```

## How It Works

Each turn, the LLM receives the current room context (position, biome, nearby rooms, narrative history, inventory) and returns a JSON response with a tile map, description, enemies, items, and NPCs.

Three memory systems keep the world consistent:
- **World Memory** — stores rooms by `(x, y, z)` coordinate so revisited rooms don't regenerate
- **Narrative Memory** — rolling log of the last 10 events, passed to the LLM for story continuity
- **Inventory** — persisted across sessions, referenced by the LLM for contextual item interactions

If the LLM is unavailable or returns invalid JSON, the engine falls back to procedurally generated rooms from templates.

The frontend renders the tile map using `TileCrawler.otf` (a custom font in `public/fonts/`), falling back to the system monospace font.

## Configuration

LLM settings are controlled via environment variables:

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` | Model to use |
| `OPENAI_API_BASE` | (OpenAI default) | Override for local LLMs (e.g., Ollama) |
| `AUTH_ENABLED` | `false` | Enable JWT authentication |
| `WEBSOCKET_ENABLED` | `false` | Enable WebSocket endpoint |
| `SESSION_TIMEOUT_MINUTES` | `60` | Inactive session cleanup |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

See `backend/.env.example` for the full list.

## Roadmap

### Implemented

- [x] Turn-based combat with damage formulas, crits, and flee mechanics
- [x] 8 biomes (Dungeon, Cave, Crypt, Ruins, Temple, Forest, Volcano, Void)
- [x] Database persistence (SQLite) with save/load
- [x] JWT authentication (feature-flagged)
- [x] OpenAPI/Swagger documentation
- [x] Playwright E2E test suite
- [x] GitHub Actions CI pipeline
- [x] NPC dialogue with relationship memory
- [x] LLM response caching
- [x] Session-based multiplayer isolation

### Partially Implemented

- [ ] Glyph registry: data model and registry exist (`backend/glyphs/`) but not integrated into the game loop
- [ ] WebSocket: backend manager exists but no frontend client; feature-flagged off

### Planned

- [ ] Quest system
- [ ] Character classes
- [ ] Magic system with spells
- [ ] Crafting
- [ ] Fog of war
- [ ] Mobile-friendly controls
- [ ] Custom tileset pipeline (procedural glyph generation)

## Quick Start

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
echo "OPENAI_API_KEY=sk-your-key" > .env
uvicorn main:app --reload

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173` to play.

## License

MIT — see [LICENSE](LICENSE) for details.

## Related Projects

- [Shredsquatch](https://github.com/kase1111-hash/Shredsquatch) — 3D snowboarding infinite runner
- [Midnight-pulse](https://github.com/kase1111-hash/Midnight-pulse) — Procedural synthwave night drive
- [Long-Home](https://github.com/kase1111-hash/Long-Home) — Atmospheric indie game (Godot)
