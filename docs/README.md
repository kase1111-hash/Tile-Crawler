# Tile-Crawler Documentation

Welcome to the Tile-Crawler technical documentation. This documentation covers the architecture, systems, and APIs that power the LLM-driven dungeon crawler.

## Quick Links

- [Core Architecture](./design/01-core-architecture.md) - System overview and input handling
- [API Reference](./api/api-reference.md) - REST API documentation
- [Data Schemas](./schemas/data-schemas.md) - Data structure definitions

## Input System

**Important:** Tile-Crawler is designed exclusively for **Xbox controller** and **keyboard** controls. Mouse input is **not supported** during gameplay - the mouse can only be used to select button mappings in the settings menu.

### Primary Controls

| Controller | Keyboard | Action |
|------------|----------|--------|
| Left Stick / D-Pad | WASD / Arrows | Movement |
| A Button | Space / Enter | Interact / Confirm |
| B Button | Escape | Cancel / Back |
| X Button | F | Attack / Primary Action |
| Y Button | I | Inventory / Secondary Action |
| LB / RB | Q / E | Cycle Targets / Tab Navigation |
| LT | Shift | Defend / Block |
| RT | Ctrl | Special Action / Sneak |
| Start | Escape | Pause Menu |
| Select | Tab | Quick Menu |

## Documentation Structure

```
docs/
├── README.md                          # This file
├── design/                            # Design documents
│   ├── 01-core-architecture.md        # System architecture & input handling
│   ├── 02-glyph-rendering-system.md   # Tileset rendering
│   ├── 03-art-studio.md               # Tileset creation tools
│   ├── 04-world-generation.md         # Procedural & LLM world gen
│   ├── 05-llm-intelligence-layer.md   # AI integration
│   ├── 06-rpg-systems.md              # Combat, stats, equipment
│   ├── 07-entity-npc-system.md        # NPCs and enemies
│   └── 08-save-system.md              # Save/load functionality
├── api/
│   └── api-reference.md               # REST API documentation
└── schemas/
    └── data-schemas.md                # TypeScript/JSON schemas
```

## Design Documents

### [01. Core Architecture](./design/01-core-architecture.md)
The foundational architecture document covering:
- System overview and data flow
- Frontend/backend separation
- **Input system architecture (Controller & Keyboard)**
- Technology stack
- Performance considerations

### [02. Glyph Rendering System](./design/02-glyph-rendering-system.md)
The visual rendering system documentation:
- Custom font tileset rendering
- Character-to-tile mapping
- Layer system
- Animation support
- Color and effects

### [03. Art Studio](./design/03-art-studio.md)
The integrated tileset creation toolkit:
- **Cursor-based pixel art editing (no mouse)**
- Glyph editor with controller/keyboard controls
- Tileset management
- Import/export functionality
- Color palette system

### [04. World Generation](./design/04-world-generation.md)
Procedural and LLM-powered world creation:
- Macro world structure
- Zone and room generation algorithms
- LLM content enhancement
- Biome definitions
- **Exploration controls**

### [05. LLM Intelligence Layer](./design/05-llm-intelligence-layer.md)
AI integration for dynamic content:
- Context management
- Prompt engineering
- Response parsing
- Memory systems
- **Input action interpretation**

### [06. RPG Systems](./design/06-rpg-systems.md)
Core gameplay mechanics:
- Character statistics
- **Combat system with controller/keyboard controls**
- Equipment and inventory
- Skill trees
- Level progression

### [07. Entity & NPC System](./design/07-entity-npc-system.md)
Non-player characters and enemies:
- Entity hierarchy
- Enemy AI behaviors
- **NPC interaction controls**
- Dialogue system
- Quest system

### [08. Save System](./design/08-save-system.md)
Game persistence:
- Save file structure
- **Save/load menu controls**
- Auto-save system
- Version migration
- Data integrity

## API Documentation

### [API Reference](./api/api-reference.md)
Complete REST API documentation:
- Authentication
- Game state endpoints
- Action endpoints
- Inventory/shop endpoints
- Save/load endpoints
- WebSocket events
- **Input device mapping**

## Data Schemas

### [Data Schemas](./schemas/data-schemas.md)
TypeScript interface definitions for:
- Player data
- Item definitions
- Entity structures
- World state
- Quest data
- **Input configuration schemas**
- Save file format

## Control Scheme Summary

### Why No Mouse Support?

Tile-Crawler is designed as an authentic roguelike experience optimized for:

1. **Controller-first gameplay** - Couch gaming with Xbox controller
2. **Keyboard efficiency** - Classic roguelike keyboard controls
3. **Consistent input handling** - Same experience across platforms
4. **Accessibility** - Predictable button-based navigation

Mouse input adds complexity without benefit for tile-based, turn-based gameplay. All menus, dialogs, and interactions are navigable with directional controls and action buttons.

### Button Mapping

The settings menu allows full customization of both controller and keyboard bindings. When remapping controls:

1. Navigate to the control you want to change (using controller/keyboard)
2. Press the confirm button
3. Press the new button/key you want to assign
4. (Mouse clicks are accepted here only for UI button selection)

## Getting Started

1. **For Players:** Start with the [Core Architecture](./design/01-core-architecture.md) for control scheme details
2. **For Developers:** Review the [API Reference](./api/api-reference.md) and [Data Schemas](./schemas/data-schemas.md)
3. **For Artists:** See the [Art Studio](./design/03-art-studio.md) and [Glyph Rendering System](./design/02-glyph-rendering-system.md)
4. **For Game Designers:** Explore [RPG Systems](./design/06-rpg-systems.md) and [World Generation](./design/04-world-generation.md)

## Version

Documentation Version: 1.0.0
Last Updated: January 2026
