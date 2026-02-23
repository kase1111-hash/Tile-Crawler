# Changelog

All notable changes to Tile-Crawler will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Distinctive texture characters for terrain types

## [0.1.0] - 2026-01-01

### Added

#### Core Gameplay
- Dynamic world generation powered by LLM (GPT-4o-mini default)
- Persistent world memory — previously explored areas remain consistent
- Narrative continuity system with rolling event log
- Turn-based combat with damage formulas, crits, and flee mechanics
- NPC dialogue with relationship tracking across encounters
- Inventory system with consumables, equipment, and gold
- 8 biomes (Dungeon, Cave, Crypt, Ruins, Temple, Forest, Volcano, Void)
- LLM response caching (LRU, 30-key capacity)
- Fallback room generation when LLM is unavailable

#### Backend (Python/FastAPI)
- RESTful API with Pydantic request/response models
- Session-based state isolation for concurrent users
- JWT-based user authentication (feature-flagged, off by default)
- SQLite database persistence with save/load
- OpenAI API integration with configurable model and base URL
- LLM call latency metrics
- Player name input validation and sanitization
- Rate limiting on auth endpoints

#### Glyph Registry (partial — not yet integrated into game loop)
- Glyph data model with physics, visual, narrative, and LLM properties
- Registry with lookup by ID, codepoint, and character
- Glyph definitions in `data/glyphs.json`

#### Frontend (React/TypeScript)
- React 18 with Vite build system
- Tailwind CSS styling
- 9 UI components (GameMap, PlayerStats, Inventory, Controls, Combat, Narrative, RoomItems, Dialogue, GameMenu)
- Custom game state hook (`useGame`)
- REST API client with typed error handling
- Custom tile font (`TileCrawler.otf`)

#### DevOps
- Docker and Docker Compose support
- GitHub Actions CI/CD pipeline
- Playwright E2E tests (6 specs)
- pytest backend test suite (280+ tests)
- Code coverage reporting

#### Documentation
- README with architecture overview
- API reference documentation
- Design documents for core systems

---

[Unreleased]: https://github.com/kase1111-hash/Tile-Crawler/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kase1111-hash/Tile-Crawler/releases/tag/v0.1.0
