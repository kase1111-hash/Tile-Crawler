# Core Architecture Design Document

## Overview

Tile-Crawler is a next-generation roguelike that merges procedural world generation, LLM storytelling, and ASCII/roguelike visual aesthetics. The architecture is designed around a client-server model where an LLM acts as the game master, generating dynamic content in real-time.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (React/TypeScript)                 │
│  ┌───────────────┬───────────────┬───────────────────────────┐  │
│  │   Input       │   Rendering   │      UI Components        │  │
│  │   Manager     │   Engine      │   (HUD, Inventory, etc)   │  │
│  │ (Controller/  │  (Glyph-based)│                           │  │
│  │  Keyboard)    │               │                           │  │
│  └───────┬───────┴───────┬───────┴───────────────────────────┘  │
│          │               │                                       │
│          ▼               ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Game State Manager                            │  │
│  │  (Local state, input buffering, render state)             │  │
│  └───────────────────────────┬───────────────────────────────┘  │
└──────────────────────────────┼───────────────────────────────────┘
                               │ REST API / WebSocket
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI/Python)                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    API Gateway                             │  │
│  │  (Request validation, rate limiting, session management)  │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   LLM Engine                               │  │
│  │  (Prompt construction, response parsing, caching)         │  │
│  └───────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────┬────────────┼────────────┬──────────────────┐  │
│  │ World State  │  Narrative │  Inventory │   RPG Systems    │  │
│  │   Manager    │   Memory   │   System   │  (Stats, Combat) │  │
│  └──────────────┴────────────┴────────────┴──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Input System Architecture

### Supported Input Methods

Tile-Crawler is designed exclusively for **Xbox controller** and **keyboard** input. Mouse input is **not supported** for gameplay - the mouse can only be used for button mapping configuration in the settings menu.

#### Xbox Controller Support

The primary input method is the Xbox controller, providing an intuitive console-style experience:

| Button/Input | Action |
|-------------|--------|
| **Left Stick** | 8-directional movement |
| **D-Pad** | 4-directional movement (cardinal) |
| **A Button** | Confirm / Interact / Talk |
| **B Button** | Cancel / Back |
| **X Button** | Primary Action (Attack/Use) |
| **Y Button** | Secondary Action (Inventory/Map) |
| **LB** | Cycle target left / Previous menu item |
| **RB** | Cycle target right / Next menu item |
| **LT** | Defend / Block |
| **RT** | Special Attack / Sprint |
| **Left Stick Click** | Crouch / Sneak |
| **Right Stick Click** | Center camera |
| **Start** | Pause menu |
| **Select/Back** | Quick menu / Character sheet |

#### Keyboard Support

Full keyboard support with rebindable keys:

| Default Key | Action |
|------------|--------|
| **W/Up Arrow** | Move North |
| **S/Down Arrow** | Move South |
| **A/Left Arrow** | Move West |
| **D/Right Arrow** | Move East |
| **Q/E** | Diagonal movement (NW/NE) |
| **Z/C** | Diagonal movement (SW/SE) |
| **Space/Enter** | Confirm / Interact / Talk |
| **Escape** | Cancel / Back / Pause |
| **F** | Primary Action (Attack/Use) |
| **I** | Inventory |
| **M** | Map |
| **Tab** | Cycle targets |
| **Shift** | Defend / Block |
| **Ctrl** | Crouch / Sneak |
| **R** | Special Attack |

#### Button Mapping Configuration

The settings menu provides button mapping functionality where players can:
- Remap any keyboard key to any action
- Remap any controller button to any action
- Use mouse clicks **only** to select buttons during remapping
- View current control schemes
- Reset to default mappings

**Note:** Mouse movement and clicking are intentionally disabled during gameplay to maintain the authentic roguelike experience and ensure consistent input handling across platforms.

### Input Processing Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                    Input Detection Layer                      │
│  ┌─────────────────┐    ┌─────────────────┐                  │
│  │  Gamepad API    │    │  Keyboard API   │                  │
│  │  (Controller)   │    │  (Key events)   │                  │
│  └────────┬────────┘    └────────┬────────┘                  │
│           │                      │                            │
│           ▼                      ▼                            │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              Input Normalization Layer                    ││
│  │  (Maps raw inputs to abstract game actions)               ││
│  └──────────────────────────────┬───────────────────────────┘│
│                                 │                             │
│                                 ▼                             │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              Input Buffer / Queue                         ││
│  │  (Handles input timing, prevents double-inputs)           ││
│  └──────────────────────────────┬───────────────────────────┘│
│                                 │                             │
│                                 ▼                             │
│  ┌──────────────────────────────────────────────────────────┐│
│  │              Action Dispatcher                            ││
│  │  (Routes actions to appropriate game systems)             ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. Frontend Modules

#### Input Manager (`input/`)
- `ControllerHandler.ts` - Xbox controller input processing
- `KeyboardHandler.ts` - Keyboard input processing
- `InputMapper.ts` - Abstract action mapping
- `ButtonConfig.ts` - Rebindable button configuration

#### Rendering Engine (`rendering/`)
- `GlyphRenderer.ts` - Custom font tileset rendering
- `MapRenderer.ts` - Tilemap display
- `UIRenderer.ts` - HUD and menu rendering
- `AnimationManager.ts` - Transition effects

#### State Management (`state/`)
- `GameState.ts` - Core game state
- `UIState.ts` - UI/menu state
- `InputState.ts` - Current input state tracking

### 2. Backend Modules

#### API Layer (`api/`)
- `main.py` - FastAPI application entry
- `routes/` - API endpoint definitions
- `middleware/` - Request processing middleware

#### Game Logic (`game/`)
- `llm_engine.py` - LLM integration
- `world_state.py` - World persistence
- `narrative_memory.py` - Story continuity
- `inventory_state.py` - Item management
- `combat_system.py` - Combat mechanics
- `npc_manager.py` - NPC behavior

## Data Flow

### Turn-Based Game Loop

```
1. Player Input (Controller/Keyboard)
           │
           ▼
2. Input Validation & Normalization
           │
           ▼
3. Action Resolution (Local)
   - Check valid moves
   - Update UI feedback
           │
           ▼
4. API Request to Backend
   {
     "action": "move",
     "direction": "north",
     "session_id": "..."
   }
           │
           ▼
5. Backend Processing
   - Load current state
   - Construct LLM prompt
   - Generate response
   - Update world state
           │
           ▼
6. Response to Frontend
   {
     "map": [...],
     "description": "...",
     "events": [...],
     "state_updates": {...}
   }
           │
           ▼
7. Frontend State Update & Render
```

## Technology Stack

### Frontend
- **Framework:** React 18+ with TypeScript
- **State Management:** Zustand or Redux Toolkit
- **Styling:** Tailwind CSS
- **Build Tool:** Vite
- **Input Handling:** Gamepad API, Keyboard Events

### Backend
- **Framework:** FastAPI (Python 3.10+)
- **LLM Integration:** OpenAI API / Anthropic API
- **Data Storage:** JSON files (MVP) → SQLite/PostgreSQL (future)
- **Caching:** In-memory / Redis (future)

## Performance Considerations

### Input Latency
- Target: < 16ms input-to-visual feedback
- Controller polling at 60Hz minimum
- Keyboard events processed immediately
- Input buffering for network latency compensation

### Rendering
- Glyph-based rendering is lightweight
- Target: 60 FPS minimum
- Smooth transitions between game states

### Network
- Optimistic UI updates for movement
- Request debouncing for rapid inputs
- Graceful handling of network delays

## Security Considerations

- Input sanitization for all user inputs
- Rate limiting on API endpoints
- Session management and validation
- No sensitive data in client-side state

## Extensibility

The architecture supports future additions:
- Additional controller types (PlayStation, generic)
- Network multiplayer support
- Plugin system for custom tilesets
- Modding support for game content
