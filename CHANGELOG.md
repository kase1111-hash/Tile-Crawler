# Changelog

All notable changes to Tile-Crawler will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Distinctive texture characters for terrain types
- SEO keywords and related project links in README
- KEYWORDS.md for project metadata

## [0.1.0] - 2026-01-01

### Added

#### Core Gameplay
- Dynamic world generation powered by LLM (GPT-4o-mini default)
- Persistent world memory - previously explored areas remain consistent
- Narrative continuity system maintaining story coherence
- Character dialogue with dynamic NPC personalities
- Inventory system for item management
- Custom font tileset rendering

#### GASR Glyph System
- 80+ semantic glyph definitions
- Unicode Private Use Area (PUA) codepoint mapping
- 6-layer SNES-style compositing system
- Multi-directional animation support
- Edge compatibility for Wave Function Collapse tiling

#### Procedural Glyph Foundry
- AI-powered tile generation pipeline
- Tile grammar with NESW edge signatures
- 12 built-in color palettes
- Combinatorial generation (3,840+ tile variants)
- Automatic validation pipeline

#### Backend (Python/FastAPI)
- RESTful API for game state management
- WebSocket support for real-time updates
- JWT-based user authentication
- SQLite/PostgreSQL database persistence
- TTS procedural audio synthesis
- OpenAI API integration

#### Frontend (React/TypeScript)
- React 18 with Vite build system
- Tailwind CSS styling
- Custom font-based tile rendering
- Real-time game state updates
- Responsive UI components

#### DevOps
- Docker and Docker Compose support
- GitHub Actions CI/CD pipeline
- Playwright E2E testing
- pytest backend test suite (260+ tests)
- Code coverage reporting

#### Documentation
- Comprehensive README with architecture overview
- SPEC.md technical specification (Glyph Engine v1.0)
- API reference documentation
- Design documents for all major systems
- Data schema definitions

### Technical Details

#### Supported Biomes
- Dungeon
- Cave
- Crypt
- Ruins
- Temple
- Forest
- Volcano
- Void

#### RPG Systems
- Character stats (STR, DEX, CON, INT, WIS, CHA)
- Turn-based combat with LLM narration
- Equipment management
- Skill progression

#### Performance Targets
- 60 FPS on desktop, 30 FPS on mobile
- <100ms input latency
- <500ms LLM response (cached)
- <3s LLM response (uncached)

---

## Version History Format

Each version entry includes:
- **Added** - New features
- **Changed** - Changes to existing functionality
- **Deprecated** - Features to be removed in future versions
- **Removed** - Features removed in this version
- **Fixed** - Bug fixes
- **Security** - Security-related changes

[Unreleased]: https://github.com/kase1111-hash/Tile-Crawler/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/kase1111-hash/Tile-Crawler/releases/tag/v0.1.0
