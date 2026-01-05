# Tile-Crawler Engine Specification

## Glyph Engine v1.0 - Technical Design Document

---

## Executive Summary

**Tile-Crawler** is an LLM-augmented tile-based RPG engine that combines custom font-rendered tilesets, procedural world generation, and AI-driven interaction systems. Unlike ASCII-City's ShadowEngine (where the LLM controls behavioral circuits and rendering), Glyph Engine uses LLMs specifically for **semantic interpretation, NPC control, and dynamic interaction** while the rendering pipeline remains deterministic and performant.

### Core Philosophy

```
┌─────────────────────────────────────────────────────────────────┐
│                    SEPARATION OF CONCERNS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   RENDERING LAYER          │    INTELLIGENCE LAYER              │
│   (Deterministic)          │    (LLM-Powered)                   │
│                            │                                     │
│   • Tile composition       │    • Scene interpretation          │
│   • Font glyph mapping     │    • NPC behavior & dialogue       │
│   • Animation frames       │    • Quest generation              │
│   • Camera & viewport      │    • World event narration         │
│   • Lighting & shadows     │    • Sprite personality control    │
│   • UI composition         │    • Environmental storytelling    │
│                            │                                     │
│   ↓ 60 FPS guaranteed      │    ↓ Async, non-blocking           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. Architecture Overview

### 1.1 System Layers

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              PLAYER INPUT                                 │
│                    (Keyboard, Mouse, Touch, Gamepad)                      │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                           INPUT PROCESSOR                                 │
│              Command parsing, input buffering, action queue               │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 ↓
        ┌────────────────────────┴────────────────────────┐
        ↓                                                  ↓
┌───────────────────┐                          ┌────────────────────────────┐
│   GAME LOGIC      │                          │   LLM INTELLIGENCE LAYER   │
│   (Deterministic) │                          │   (Async Processing)       │
├───────────────────┤                          ├────────────────────────────┤
│ • Physics/Movement│◄─────────────────────────│ • Scene Interpreter        │
│ • Collision       │         Context          │ • NPC Mind Controller      │
│ • Combat Math     │         Exchange         │ • Quest Orchestrator       │
│ • Inventory       │─────────────────────────►│ • Dialogue Generator       │
│ • Stats/Leveling  │                          │ • Environment Narrator     │
│ • Procedural Gen  │                          │ • Sprite Behavior Director │
└─────────┬─────────┘                          └────────────────────────────┘
          ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                        WORLD STATE MANAGER                                │
│           Unified state for overworld, dungeons, and underworld           │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Overworld   │  │   Dungeon    │  │  Underworld  │  │   Interiors  │  │
│  │   Chunks     │  │    Floors    │  │    Caverns   │  │    Rooms     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────┬────────────────────────────────────────────────────────────────┘
          ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                         GLYPH RENDER ENGINE                               │
│              Custom font composition & tile-based rendering               │
├──────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ Tile Layer  │  │ Entity Layer│  │ Effect Layer│  │   UI Overlay    │  │
│  │  (Terrain)  │  │  (Sprites)  │  │ (Particles) │  │  (HUD/Menus)    │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────┬────────────────────────────────────────────────────────────────┘
          ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                           DISPLAY OUTPUT                                  │
│                    Browser Canvas / Terminal / Native                     │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Differences from ASCII-City

| Aspect | ASCII-City (ShadowEngine) | Tile-Crawler (Glyph Engine) |
|--------|---------------------------|------------------------------|
| **LLM Role** | Controls behavioral circuits, physics interpretation, rendering decisions | Scene interpretation, NPC control, dialogue, narrative only |
| **Rendering** | ASCII characters, LLM can influence what renders | Custom font glyphs, deterministic pipeline |
| **Tileset** | Standard ASCII/Unicode | Custom designed font tilesets |
| **Art Tools** | Player ASCII art studio | Full internal tile & sprite editor |
| **World Scope** | Single layer city simulation | Multi-layer (sky, surface, underground) |
| **Game Type** | Emergent narrative simulation | Traditional RPG with AI enhancement |
| **Performance** | LLM in critical path | LLM async, never blocks rendering |

---

## 2. Custom Font Tileset System

### 2.1 Glyph Architecture

The engine uses custom fonts where each Unicode codepoint maps to a hand-crafted tile image. This provides pixel-perfect rendering while maintaining text-based data representation.

```
┌─────────────────────────────────────────────────────────────────┐
│                    GLYPH MAPPING SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Unicode Range         Purpose              Example Glyphs      │
│   ─────────────────────────────────────────────────────────────  │
│   U+E000 - U+E0FF      Terrain tiles        Grass, stone, water  │
│   U+E100 - U+E1FF      Wall tiles           Brick, wood, metal   │
│   U+E200 - U+E2FF      Floor tiles          Carpet, tile, dirt   │
│   U+E300 - U+E3FF      Nature tiles         Trees, flowers, rock │
│   U+E400 - U+E4FF      Interactive objects  Doors, chests, levers│
│   U+E500 - U+E5FF      Items                Weapons, potions     │
│   U+E600 - U+E6FF      Creatures (frames)   Monsters, animals    │
│   U+E700 - U+E7FF      NPCs (frames)        Villagers, merchants │
│   U+E800 - U+E8FF      Player (frames)      Hero animations      │
│   U+E900 - U+E9FF      Effects              Fire, magic, sparks  │
│   U+EA00 - U+EAFF      UI elements          Borders, icons       │
│   U+EB00 - U+EBFF      Underground tiles    Cave, crystal, lava  │
│   U+EC00 - U+ECFF      Sky/Weather          Clouds, rain, sun    │
│   U+ED00 - U+EDFF      User-created tiles   Custom content       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Font File Structure

```
fonts/
├── tilesets/
│   ├── default/
│   │   ├── GlyphTiles-Regular.ttf      # Base tileset
│   │   ├── GlyphTiles-Animated.ttf     # Animation frames
│   │   └── manifest.json               # Glyph metadata
│   ├── fantasy/
│   │   ├── FantasyTiles-Regular.ttf
│   │   └── manifest.json
│   ├── scifi/
│   │   └── ...
│   └── user/
│       └── custom-tileset.ttf          # Player-created
└── sprites/
    ├── entities.json                    # Entity-to-glyph mapping
    └── animations.json                  # Frame sequences
```

### 2.3 Tile Manifest Format

```json
{
  "name": "Default Fantasy Tileset",
  "version": "1.0.0",
  "tileSize": 32,
  "author": "Tile-Crawler Team",
  "glyphs": {
    "terrain": {
      "grass": { "codepoint": "U+E000", "variants": 4, "walkable": true },
      "water": { "codepoint": "U+E001", "animated": true, "frames": 4, "walkable": false },
      "stone": { "codepoint": "U+E002", "variants": 2, "walkable": true }
    },
    "entities": {
      "player_idle": { "codepoint": "U+E800", "frames": 2, "frameRate": 500 },
      "player_walk_n": { "codepoint": "U+E804", "frames": 4, "frameRate": 150 },
      "player_walk_s": { "codepoint": "U+E808", "frames": 4, "frameRate": 150 },
      "player_walk_e": { "codepoint": "U+E80C", "frames": 4, "frameRate": 150 },
      "player_walk_w": { "codepoint": "U+E810", "frames": 4, "frameRate": 150 }
    }
  },
  "palettes": {
    "default": ["#1a1c2c", "#5d275d", "#b13e53", "#ef7d57", "#ffcd75"],
    "night": ["#0d0d1a", "#2d1b4e", "#5d3a7a", "#8b5fbf", "#b8a0d1"],
    "underground": ["#1a0f0a", "#3d2817", "#5c3d24", "#8b5a3c", "#b8845c"]
  }
}
```

---

## 3. Internal Art Creation Studio

### 3.1 Studio Overview

The built-in art studio allows players and developers to create custom tiles, entities, and sprite animations without external tools. All creations are automatically compiled into usable font glyphs.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ART CREATION STUDIO                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐      │
│  │   TILE EDITOR   │    │  SPRITE EDITOR  │    │ ANIMATION EDITOR│      │
│  │                 │    │                 │    │                 │      │
│  │ • Pixel canvas  │    │ • Multi-frame   │    │ • Timeline      │      │
│  │ • Palette tools │    │ • Layered       │    │ • Onion skin    │      │
│  │ • Tile variants │    │ • Hitbox editor │    │ • Preview       │      │
│  │ • Auto-tile     │    │ • Pivot points  │    │ • Export        │      │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘      │
│           │                      │                      │                │
│           └──────────────────────┴──────────────────────┘                │
│                                  ↓                                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      GLYPH COMPILER                                │  │
│  │   Converts pixel art to font glyphs with automatic Unicode mapping │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                  ↓                                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                      TILESET MANAGER                               │  │
│  │   Import, export, merge, and organize custom tilesets              │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Tile Editor Features

```typescript
interface TileEditorConfig {
  canvasSize: 16 | 32 | 48 | 64;           // Tile resolution
  gridEnabled: boolean;                     // Pixel grid overlay
  symmetryMode: 'none' | 'horizontal' | 'vertical' | 'quad';

  tools: {
    pencil: { size: 1 | 2 | 4 };
    fill: { tolerance: number };
    line: { antialiased: boolean };
    shape: 'rectangle' | 'ellipse' | 'polygon';
    eraser: { size: 1 | 2 | 4 };
    eyedropper: boolean;
    selection: 'rectangle' | 'lasso' | 'wand';
  };

  palette: {
    colors: string[];                       // Max 16 colors per tile
    transparency: boolean;                  // Alpha channel support
  };

  autoTile: {
    enabled: boolean;
    template: '4-corner' | '8-corner' | '16-tile' | '47-tile';
  };
}
```

### 3.3 Sprite Editor Features

```typescript
interface SpriteEditorConfig {
  frameSize: { width: number; height: number };
  maxFrames: 16;
  layers: {
    maxLayers: 8;
    blendModes: ['normal', 'multiply', 'screen', 'overlay'];
  };

  hitboxEditor: {
    shapes: ['rectangle', 'circle', 'polygon'];
    categories: ['body', 'attack', 'interact'];
  };

  pivotPoint: { x: number; y: number };     // Anchor for rotation/scaling

  directions: {
    count: 4 | 8;                           // Cardinal or 8-way
    autoMirror: boolean;                    // Generate mirrored frames
  };
}
```

### 3.4 Animation System

```typescript
interface AnimationDefinition {
  name: string;
  sprite: string;                           // Reference to sprite
  frames: number[];                         // Frame indices
  frameRate: number;                        // MS per frame
  loop: boolean;

  transitions: {
    [fromState: string]: {
      [toState: string]: {
        frames: number[];                   // Transition frames
        duration: number;
      };
    };
  };

  events: {
    frame: number;
    type: 'sound' | 'particle' | 'callback';
    data: any;
  }[];
}
```

---

## 4. Multi-Layer World System

### 4.1 Vertical World Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WORLD VERTICAL LAYERS                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Layer +3   ┌─────────────────────────────────────────┐   SKY           │
│              │  Floating islands, airships, clouds     │                 │
│              └─────────────────────────────────────────┘                 │
│                                                                          │
│   Layer +2   ┌─────────────────────────────────────────┐   HIGH GROUND   │
│              │  Mountain peaks, treetops, towers       │                 │
│              └─────────────────────────────────────────┘                 │
│                                                                          │
│   Layer +1   ┌─────────────────────────────────────────┐   ELEVATED      │
│              │  Hills, raised platforms, bridges       │                 │
│              └─────────────────────────────────────────┘                 │
│                                                                          │
│   Layer  0   ┌─────────────────────────────────────────┐   SURFACE       │
│              │  Towns, forests, plains, roads          │   (Primary)     │
│              └─────────────────────────────────────────┘                 │
│                                                                          │
│   Layer -1   ┌─────────────────────────────────────────┐   SHALLOW       │
│              │  Basements, sewers, shallow caves       │                 │
│              └─────────────────────────────────────────┘                 │
│                                                                          │
│   Layer -2   ┌─────────────────────────────────────────┐   UNDERGROUND   │
│              │  Deep caverns, dungeons, mines          │                 │
│              └─────────────────────────────────────────┘                 │
│                                                                          │
│   Layer -3   ┌─────────────────────────────────────────┐   ABYSS         │
│              │  Ancient ruins, lava chambers, voids    │                 │
│              └─────────────────────────────────────────┘                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Chunk System

```typescript
interface WorldChunk {
  id: string;                               // "x:y:z" format
  position: { x: number; y: number; z: number };
  size: { width: 32; height: 32 };          // Tiles per chunk

  layers: {
    ground: TileData[][];                   // Base terrain
    objects: TileData[][];                  // Placeable objects
    entities: EntityRef[];                  // NPCs, creatures
    metadata: ChunkMetadata;
  };

  state: 'ungenerated' | 'generating' | 'loaded' | 'dormant';
  lastAccess: number;                       // For LRU unloading
  modified: boolean;                        // Needs persistence
}

interface ChunkMetadata {
  biome: BiomeType;
  difficulty: number;                       // 1-10 scale
  discovered: boolean;
  pointsOfInterest: POI[];
  connectedChunks: string[];                // Adjacent chunk IDs

  // LLM-enriched data
  narrativeContext?: string;                // Scene description for LLM
  activeEvents?: WorldEvent[];
}
```

### 4.3 Transition System

```typescript
interface LayerTransition {
  type: 'stairs' | 'ladder' | 'hole' | 'elevator' | 'portal' | 'rope';
  from: { chunk: string; tile: [number, number] };
  to: { chunk: string; tile: [number, number] };

  requirements?: {
    item?: string;                          // Key, rope, etc.
    skill?: string;                         // Climbing, magic
    quest?: string;                         // Quest completion
  };

  bidirectional: boolean;
  animation: string;                        // Transition animation
}
```

---

## 5. Procedural Generation System

### 5.1 Generation Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PROCEDURAL GENERATION PIPELINE                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   SEED ──────┐                                                           │
│              ↓                                                           │
│   ┌─────────────────────┐                                               │
│   │  CONTINENTAL SCALE  │  Perlin noise for major landmasses             │
│   │  (World Map)        │  Mountain ranges, ocean basins                 │
│   └──────────┬──────────┘                                               │
│              ↓                                                           │
│   ┌─────────────────────┐                                               │
│   │  REGIONAL SCALE     │  Voronoi for biome distribution                │
│   │  (Biomes)           │  Climate simulation                            │
│   └──────────┬──────────┘                                               │
│              ↓                                                           │
│   ┌─────────────────────┐                                               │
│   │  LOCAL SCALE        │  Wave Function Collapse for terrain            │
│   │  (Chunks)           │  Detail heightmaps                             │
│   └──────────┬──────────┘                                               │
│              ↓                                                           │
│   ┌─────────────────────┐                                               │
│   │  STRUCTURE SCALE    │  Template + randomization                      │
│   │  (Buildings/Caves)  │  Room connectivity graphs                      │
│   └──────────┬──────────┘                                               │
│              ↓                                                           │
│   ┌─────────────────────┐                                               │
│   │  POPULATION SCALE   │  Entity placement rules                        │
│   │  (Entities/Items)   │  Loot tables, spawn logic                      │
│   └──────────┬──────────┘                                               │
│              ↓                                                           │
│   ┌─────────────────────┐                                               │
│   │  NARRATIVE SCALE    │  LLM enrichment (async)                        │
│   │  (Story Context)    │  Names, descriptions, quests                   │
│   └─────────────────────┘                                               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Biome Definitions

```typescript
interface BiomeDefinition {
  id: string;
  name: string;

  elevation: { min: number; max: number };
  moisture: { min: number; max: number };
  temperature: { min: number; max: number };

  terrain: {
    primary: TileType;                      // Most common tile
    secondary: TileType[];                  // Accent tiles
    distribution: number[];                 // Percentages
  };

  vegetation: {
    density: number;                        // 0-1
    types: { tile: TileType; weight: number }[];
  };

  structures: {
    type: StructureTemplate;
    frequency: number;                      // Per chunk
    conditions: GenerationCondition[];
  }[];

  entities: {
    type: EntityType;
    spawnRate: number;
    groupSize: { min: number; max: number };
    timeOfDay?: 'day' | 'night' | 'any';
  }[];

  underground: {
    caveFrequency: number;
    oreDistribution: { type: string; rarity: number }[];
    specialFeatures: string[];              // Crystals, underground lakes
  };

  ambience: {
    palette: string;                        // Color palette name
    sounds: string[];                       // Ambient sound IDs
    weather: { type: string; probability: number }[];
  };
}
```

### 5.3 Dungeon Generation

```typescript
interface DungeonGenerator {
  algorithm: 'bsp' | 'cellular' | 'drunkard' | 'template' | 'wfc';

  parameters: {
    // BSP (Binary Space Partition)
    bsp?: {
      minRoomSize: { width: number; height: number };
      maxRoomSize: { width: number; height: number };
      splitIterations: number;
    };

    // Cellular Automata
    cellular?: {
      fillProbability: number;
      smoothingPasses: number;
      birthLimit: number;
      deathLimit: number;
    };

    // Drunkard's Walk
    drunkard?: {
      fillPercent: number;
      weightedDirection: boolean;
      tunnelWidth: number;
    };

    // Wave Function Collapse
    wfc?: {
      tileRules: WFCRule[];
      constraints: WFCConstraint[];
    };
  };

  features: {
    entrances: number;
    exits: number;
    secretRooms: { probability: number; maxCount: number };
    traps: { types: string[]; density: number };
    puzzles: { types: string[]; count: number };
  };

  population: {
    enemies: EnemySpawnTable;
    loot: LootTable;
    npcs: NPCSpawnTable;
  };
}
```

---

## 6. LLM Intelligence Layer

### 6.1 LLM Role Definition

The LLM in Glyph Engine is **NOT** responsible for:
- Tile rendering decisions
- Physics calculations
- Combat math
- Pathfinding
- Frame-by-frame updates

The LLM **IS** responsible for:
- Scene interpretation and description
- NPC personality and dialogue
- Quest generation and progression
- Environmental storytelling
- Sprite behavior direction (high-level)
- Dynamic world events

### 6.2 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       LLM INTELLIGENCE LAYER                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      CONTEXT AGGREGATOR                             │ │
│  │   Collects world state, player state, and history for LLM context  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                   ↓                                      │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        REQUEST ROUTER                               │ │
│  │   Dispatches to specialized prompt templates based on request type  │ │
│  └──┬──────────┬──────────┬──────────┬──────────┬─────────────────────┘ │
│     ↓          ↓          ↓          ↓          ↓                        │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────┐                   │
│  │Scene │  │ NPC  │  │Quest │  │Event │  │ Behavior │                   │
│  │Interp│  │ Mind │  │ Gen  │  │Narr. │  │ Director │                   │
│  └──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘  └────┬─────┘                   │
│     └─────────┴─────────┴─────────┴───────────┘                          │
│                          ↓                                               │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      RESPONSE PARSER                                │ │
│  │   Validates, sanitizes, and transforms LLM output to game actions  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                          ↓                                               │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                       ACTION QUEUE                                  │ │
│  │   Non-blocking queue of LLM-directed actions for game loop          │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.3 Specialized Modules

#### 6.3.1 Scene Interpreter

Provides rich descriptions of game scenes based on visible tiles and context.

```typescript
interface SceneInterpreterRequest {
  visibleTiles: TileData[][];               // Current viewport
  playerPosition: Vector2;
  timeOfDay: number;                        // 0-24
  weather: WeatherState;
  recentEvents: GameEvent[];
  playerState: PlayerState;
}

interface SceneInterpreterResponse {
  description: string;                      // Narrative text
  atmosphere: 'peaceful' | 'tense' | 'mysterious' | 'dangerous';
  pointsOfInterest: {
    position: Vector2;
    description: string;
    interactionHint?: string;
  }[];
  ambientSuggestions?: string[];            // Sound/music hints
}
```

#### 6.3.2 NPC Mind Controller

Manages NPC personalities, memories, and dialogue.

```typescript
interface NPCMind {
  id: string;
  name: string;

  personality: {
    traits: string[];                       // "friendly", "suspicious", etc.
    background: string;                     // Character history
    goals: string[];                        // Current motivations
    knowledge: string[];                    // What they know
  };

  memory: {
    playerInteractions: InteractionLog[];
    worldEvents: WorldEventLog[];
    relationships: RelationshipMap;
  };

  currentState: {
    mood: string;
    activity: string;
    location: string;
  };
}

interface DialogueRequest {
  npc: NPCMind;
  player: PlayerState;
  context: string;                          // What triggered dialogue
  playerInput?: string;                     // Player's spoken text
}

interface DialogueResponse {
  text: string;                             // NPC's spoken words
  emotion: string;                          // For sprite expression
  actions?: NPCAction[];                    // Physical reactions
  memoryUpdate?: Partial<NPCMind>;          // Changes to NPC state
  questTrigger?: string;                    // Quest to activate
}
```

#### 6.3.3 Quest Orchestrator

Generates and manages dynamic quests.

```typescript
interface QuestTemplate {
  type: 'fetch' | 'escort' | 'investigate' | 'combat' | 'puzzle' | 'social';
  complexity: 1 | 2 | 3;                    // Simple to complex

  requirements: {
    playerLevel?: { min: number; max: number };
    completedQuests?: string[];
    items?: string[];
    reputation?: { faction: string; level: number };
  };
}

interface GeneratedQuest {
  id: string;
  title: string;
  description: string;

  objectives: {
    id: string;
    type: string;
    target: string;
    count?: number;
    location?: string;
    completed: boolean;
  }[];

  rewards: {
    experience: number;
    gold: number;
    items: string[];
    reputation: { faction: string; change: number }[];
  };

  dialogue: {
    introduction: string;
    progress: { [objectiveId: string]: string };
    completion: string;
  };

  timeLimit?: number;                       // Game hours
  failureConsequences?: string;
}
```

#### 6.3.4 Sprite Behavior Director

High-level behavior commands for entity sprites.

```typescript
interface BehaviorDirective {
  entityId: string;

  // Movement behaviors
  movement?: {
    type: 'patrol' | 'wander' | 'follow' | 'flee' | 'approach' | 'idle';
    target?: string | Vector2;
    speed?: 'slow' | 'normal' | 'fast';
    path?: Vector2[];
  };

  // Animation state
  animation?: {
    state: string;                          // "idle", "working", "talking"
    facing: 'n' | 's' | 'e' | 'w';
    emotion?: string;                       // Affects sprite variant
  };

  // Interaction behavior
  interaction?: {
    approachable: boolean;
    dialogueReady: boolean;
    hostility: 'friendly' | 'neutral' | 'hostile';
  };

  // Scheduled actions
  schedule?: {
    time: number;                           // Game hour
    action: string;
    location?: Vector2;
  }[];

  duration: number;                         // How long this directive lasts
}
```

### 6.4 Async Processing Model

```typescript
class LLMIntelligenceLayer {
  private requestQueue: PriorityQueue<LLMRequest>;
  private responseCache: LRUCache<string, LLMResponse>;
  private pendingRequests: Map<string, Promise<LLMResponse>>;

  // Priority levels (lower = higher priority)
  static PRIORITY = {
    DIALOGUE: 1,          // Player is waiting
    SCENE: 2,             // New area entered
    QUEST: 3,             // Quest update needed
    BEHAVIOR: 4,          // NPC behavior update
    ENRICHMENT: 5,        // Background world enrichment
  };

  async request(req: LLMRequest): Promise<LLMResponse> {
    // Check cache first
    const cacheKey = this.computeCacheKey(req);
    if (this.responseCache.has(cacheKey)) {
      return this.responseCache.get(cacheKey);
    }

    // Deduplicate in-flight requests
    if (this.pendingRequests.has(cacheKey)) {
      return this.pendingRequests.get(cacheKey);
    }

    // Queue new request
    const promise = this.processRequest(req);
    this.pendingRequests.set(cacheKey, promise);

    return promise;
  }

  // Never blocks game loop
  async processRequest(req: LLMRequest): Promise<LLMResponse> {
    // ... async LLM call
  }
}
```

---

## 7. RPG Systems

### 7.1 Character System

```typescript
interface PlayerCharacter {
  // Identity
  name: string;
  class: CharacterClass;
  level: number;
  experience: number;

  // Core Stats
  stats: {
    health: { current: number; max: number };
    mana: { current: number; max: number };
    stamina: { current: number; max: number };
  };

  // Attributes
  attributes: {
    strength: number;         // Physical damage, carry weight
    dexterity: number;        // Speed, accuracy, critical
    constitution: number;     // Health, resistances
    intelligence: number;     // Magic damage, mana pool
    wisdom: number;           // Magic resist, perception
    charisma: number;         // NPC interactions, prices
  };

  // Derived Stats
  derived: {
    attackPower: number;
    defense: number;
    magicPower: number;
    magicResist: number;
    speed: number;
    criticalChance: number;
    criticalDamage: number;
  };

  // Progression
  skills: Skill[];
  abilities: Ability[];
  talents: Talent[];

  // Equipment
  equipment: {
    head: Item | null;
    body: Item | null;
    hands: Item | null;
    feet: Item | null;
    mainHand: Item | null;
    offHand: Item | null;
    accessory1: Item | null;
    accessory2: Item | null;
  };

  // Inventory
  inventory: InventorySlot[];
  gold: number;

  // Reputation
  factionStanding: Map<string, number>;
}
```

### 7.2 Combat System

```typescript
interface CombatSystem {
  type: 'turnBased' | 'realTimeWithPause' | 'actionQueue';

  // Turn-based specifics
  turnBased?: {
    initiativeFormula: string;              // e.g., "1d20 + dexterity"
    actionsPerTurn: number;
    movementPerTurn: number;
  };

  // Damage calculation
  damageFormula: {
    physical: string;                       // e.g., "(str * 2 + weaponDamage) - defense"
    magical: string;
    critical: string;
  };

  // Status effects
  statusEffects: StatusEffect[];

  // AI behavior (non-LLM, deterministic)
  aiPatterns: {
    aggressive: CombatAIPattern;
    defensive: CombatAIPattern;
    supportive: CombatAIPattern;
    boss: CombatAIPattern;
  };
}

interface CombatEncounter {
  id: string;
  enemies: Enemy[];
  environment: {
    terrain: TileData[][];
    hazards: Hazard[];
    cover: CoverPoint[];
  };

  // LLM provides flavor, not mechanics
  llmContext: {
    narrativeIntro?: string;
    victoryText?: string;
    defeatText?: string;
    specialMomentTriggers?: {
      condition: string;
      narrative: string;
    }[];
  };
}
```

### 7.3 Inventory & Items

```typescript
interface Item {
  id: string;
  name: string;
  description: string;

  type: 'weapon' | 'armor' | 'accessory' | 'consumable' | 'material' | 'key' | 'quest';
  rarity: 'common' | 'uncommon' | 'rare' | 'epic' | 'legendary';

  // Visual
  sprite: string;                           // Glyph codepoint
  groundSprite?: string;                    // When on ground

  // Stats (for equipment)
  stats?: {
    [stat: string]: number;
  };

  // Effects (for consumables)
  effects?: ItemEffect[];

  // Use conditions
  requirements?: {
    level?: number;
    class?: string[];
    stats?: { [stat: string]: number };
  };

  // Economy
  value: number;
  stackable: boolean;
  maxStack?: number;

  // Special properties
  properties?: string[];                    // "fireproof", "cursed", etc.
}
```

### 7.4 Skill System

```typescript
interface Skill {
  id: string;
  name: string;
  description: string;

  type: 'passive' | 'active' | 'toggle';
  category: 'combat' | 'magic' | 'crafting' | 'social' | 'exploration';

  // Requirements
  requirements: {
    level: number;
    class?: string[];
    prerequisites?: string[];               // Other skill IDs
  };

  // Progression
  maxLevel: number;
  currentLevel: number;
  experienceToNext: number;

  // Effects per level
  levelEffects: {
    [level: number]: {
      description: string;
      stats?: { [stat: string]: number };
      abilities?: string[];
    };
  };
}

interface Ability {
  id: string;
  name: string;
  description: string;

  // Costs
  cost: {
    mana?: number;
    stamina?: number;
    health?: number;
    cooldown: number;                       // Turns or seconds
  };

  // Targeting
  targeting: {
    type: 'self' | 'single' | 'area' | 'line' | 'cone';
    range: number;
    areaSize?: number;
  };

  // Effects
  effects: AbilityEffect[];

  // Animation
  animation: {
    cast: string;
    projectile?: string;
    impact: string;
  };
}
```

---

## 8. Rendering Engine

### 8.1 Render Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GLYPH RENDER PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   WORLD STATE                                                            │
│       ↓                                                                  │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    VIEWPORT CALCULATOR                           │   │
│   │   Determines visible chunks and tiles based on camera position   │   │
│   └────────────────────────────────┬────────────────────────────────┘   │
│                                    ↓                                     │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    LAYER COMPOSITOR                              │   │
│   │   Combines terrain, objects, entities, effects in Z-order        │   │
│   └────────────────────────────────┬────────────────────────────────┘   │
│                                    ↓                                     │
│   ┌──────────────────────────────────────────────────────────────────┐  │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │  │
│   │  │   Ground   │  │   Objects  │  │  Entities  │  │   Effects  │  │  │
│   │  │   Layer    │  │   Layer    │  │   Layer    │  │   Layer    │  │  │
│   │  │            │  │            │  │            │  │            │  │  │
│   │  │ • Terrain  │  │ • Walls    │  │ • NPCs     │  │ • Particles│  │  │
│   │  │ • Water    │  │ • Doors    │  │ • Monsters │  │ • Magic    │  │  │
│   │  │ • Paths    │  │ • Items    │  │ • Player   │  │ • Weather  │  │  │
│   │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │  │
│   └────────────────────────────────┬────────────────────────────────────┘│
│                                    ↓                                     │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    LIGHTING SYSTEM                               │   │
│   │   Applies ambient, point lights, shadows, and fog of war         │   │
│   └────────────────────────────────┬────────────────────────────────┘   │
│                                    ↓                                     │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    ANIMATION TICKER                              │   │
│   │   Updates sprite frames based on timing                          │   │
│   └────────────────────────────────┬────────────────────────────────┘   │
│                                    ↓                                     │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    GLYPH RENDERER                                │   │
│   │   Converts tile grid to font glyphs on canvas                    │   │
│   └────────────────────────────────┬────────────────────────────────┘   │
│                                    ↓                                     │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                    UI OVERLAY                                    │   │
│   │   HUD, menus, dialogue boxes, inventory                          │   │
│   └─────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                     │
│                              DISPLAY                                     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Viewport System

```typescript
interface Viewport {
  // Position in world coordinates
  center: Vector2;

  // Size in tiles
  width: number;
  height: number;

  // Zoom level
  zoom: number;                             // 1.0 = normal

  // Camera behavior
  follow?: {
    target: string;                         // Entity ID
    smoothing: number;                      // 0 = instant, 1 = slow
    deadZone: { width: number; height: number };
  };

  // Boundaries
  bounds?: {
    min: Vector2;
    max: Vector2;
  };
}
```

### 8.3 Lighting System

```typescript
interface LightingSystem {
  ambientLight: {
    color: string;
    intensity: number;                      // 0-1
  };

  timeOfDayCycle: {
    enabled: boolean;
    dayLength: number;                      // Real seconds per game day
    phases: {
      dawn: { start: number; color: string; intensity: number };
      day: { start: number; color: string; intensity: number };
      dusk: { start: number; color: string; intensity: number };
      night: { start: number; color: string; intensity: number };
    };
  };

  pointLights: PointLight[];

  fogOfWar: {
    enabled: boolean;
    exploredOpacity: number;                // 0-1, for seen but not visible
    unexploredOpacity: number;              // 0-1, for never seen
    revealRadius: number;                   // Tiles
  };

  shadowCasting: {
    enabled: boolean;
    quality: 'low' | 'medium' | 'high';
    maxDistance: number;
  };
}

interface PointLight {
  position: Vector2;
  radius: number;
  color: string;
  intensity: number;
  flicker?: {
    amount: number;
    speed: number;
  };
  attachedTo?: string;                      // Entity ID
}
```

---

## 9. Save System

### 9.1 Save Data Structure

```typescript
interface SaveData {
  version: string;
  timestamp: number;
  playTime: number;

  player: PlayerCharacter;

  world: {
    seed: number;
    currentChunk: string;
    currentLayer: number;

    // Only modified chunks are saved
    modifiedChunks: Map<string, ChunkSaveData>;

    // Discovered locations
    discoveredLocations: string[];

    // Active world events
    activeEvents: WorldEvent[];
  };

  npcs: {
    [npcId: string]: NPCMind;
  };

  quests: {
    active: GeneratedQuest[];
    completed: string[];
    failed: string[];
  };

  narrative: {
    log: NarrativeEvent[];
    flags: Map<string, any>;
  };

  settings: {
    difficulty: string;
    customizations: any;
  };
}
```

### 9.2 Auto-Save System

```typescript
interface AutoSaveConfig {
  enabled: boolean;
  interval: number;                         // Seconds
  maxSlots: number;

  triggers: {
    onChunkTransition: boolean;
    onQuestComplete: boolean;
    onLevelUp: boolean;
    onSignificantEvent: boolean;
  };

  compression: boolean;
  encryption: boolean;                      // For sensitive data
}
```

---

## 10. Configuration & Extensibility

### 10.1 Game Configuration

```typescript
interface GameConfig {
  // Display
  display: {
    tileSize: 16 | 32 | 48 | 64;
    viewportTiles: { width: number; height: number };
    targetFPS: 30 | 60;
    pixelPerfect: boolean;
  };

  // Gameplay
  gameplay: {
    difficulty: 'easy' | 'normal' | 'hard' | 'nightmare';
    permadeath: boolean;
    hungerSystem: boolean;
    weatherEffects: boolean;
  };

  // World Generation
  worldGen: {
    seed?: number;                          // Omit for random
    worldSize: 'small' | 'medium' | 'large' | 'infinite';
    dungeonDensity: number;
    npcDensity: number;
  };

  // LLM
  llm: {
    provider: 'openai' | 'anthropic' | 'local';
    model: string;
    temperature: number;
    maxTokens: number;
    cacheResponses: boolean;
    offlineMode: boolean;                   // Use fallback templates
  };

  // Audio
  audio: {
    musicVolume: number;
    sfxVolume: number;
    ambientVolume: number;
  };

  // Controls
  controls: {
    scheme: 'keyboard' | 'mouse' | 'gamepad' | 'touch';
    keybindings: KeyBindings;
  };
}
```

### 10.2 Mod System

```typescript
interface ModManifest {
  id: string;
  name: string;
  version: string;
  author: string;
  description: string;

  requires: {
    engineVersion: string;
    mods?: string[];
  };

  provides: {
    tilesets?: string[];
    entities?: string[];
    items?: string[];
    quests?: string[];
    biomes?: string[];
    scripts?: string[];
  };

  hooks: {
    onLoad?: string;
    onGameStart?: string;
    onTick?: string;
    onEvent?: { event: string; handler: string }[];
  };
}
```

---

## 11. Technical Requirements

### 11.1 Client Requirements

```
Browser Target:
├── Chrome/Edge 90+
├── Firefox 88+
├── Safari 14+
└── Mobile browsers (iOS Safari, Chrome Android)

Performance Targets:
├── 60 FPS minimum on desktop
├── 30 FPS minimum on mobile
├── < 100ms input latency
├── < 500ms LLM response (cached)
└── < 3s LLM response (uncached)

Memory Budget:
├── Base game: < 100MB
├── Loaded chunks: < 50MB
├── LLM context: < 10MB
└── Audio buffers: < 30MB
```

### 11.2 Server Requirements

```
Backend:
├── Python 3.10+ with FastAPI
├── Async LLM client (OpenAI/Anthropic SDK)
├── Redis for session/cache (optional)
└── PostgreSQL for persistence (optional)

API Rate Limits:
├── LLM calls: 10/minute base, burst to 30
├── Save operations: 1/second
└── Chunk generation: 5/second
```

### 11.3 Development Stack

```
Frontend:
├── React 18+ with TypeScript
├── Vite for build/dev
├── Canvas API for rendering
├── Web Audio API for sound
└── IndexedDB for local saves

Backend:
├── FastAPI (Python)
├── Pydantic for validation
├── LangChain for LLM orchestration
└── JSON/SQLite for persistence

Art Tools:
├── Custom canvas-based editors
├── FontForge integration for glyph export
└── WebGL for preview rendering
```

---

## 12. File Structure

```
tile-crawler/
├── backend/
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Configuration management
│   ├── api/
│   │   ├── routes/
│   │   │   ├── game.py              # Game state endpoints
│   │   │   ├── world.py             # World generation endpoints
│   │   │   ├── llm.py               # LLM interaction endpoints
│   │   │   └── studio.py            # Art studio endpoints
│   │   └── middleware/
│   ├── core/
│   │   ├── world/
│   │   │   ├── generator.py         # Procedural generation
│   │   │   ├── chunk.py             # Chunk management
│   │   │   ├── biome.py             # Biome definitions
│   │   │   └── dungeon.py           # Dungeon generation
│   │   ├── entities/
│   │   │   ├── player.py            # Player character
│   │   │   ├── npc.py               # NPC entities
│   │   │   ├── monster.py           # Monster entities
│   │   │   └── item.py              # Item entities
│   │   ├── systems/
│   │   │   ├── combat.py            # Combat system
│   │   │   ├── inventory.py         # Inventory management
│   │   │   ├── quest.py             # Quest system
│   │   │   └── skill.py             # Skill/ability system
│   │   └── save/
│   │       ├── manager.py           # Save/load logic
│   │       └── serializer.py        # Data serialization
│   ├── llm/
│   │   ├── engine.py                # LLM orchestration
│   │   ├── prompts/
│   │   │   ├── scene.py             # Scene interpretation prompts
│   │   │   ├── dialogue.py          # NPC dialogue prompts
│   │   │   ├── quest.py             # Quest generation prompts
│   │   │   └── behavior.py          # Sprite behavior prompts
│   │   ├── context.py               # Context aggregation
│   │   ├── cache.py                 # Response caching
│   │   └── fallback.py              # Offline fallback templates
│   ├── data/
│   │   ├── biomes.json              # Biome definitions
│   │   ├── entities.json            # Entity definitions
│   │   ├── items.json               # Item database
│   │   ├── skills.json              # Skill definitions
│   │   └── dialogues/               # Fallback dialogue templates
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── main.tsx                 # App entry point
│   │   ├── App.tsx                  # Root component
│   │   ├── components/
│   │   │   ├── game/
│   │   │   │   ├── GameCanvas.tsx   # Main game rendering
│   │   │   │   ├── Viewport.tsx     # Camera/viewport
│   │   │   │   ├── TileLayer.tsx    # Tile rendering
│   │   │   │   ├── EntityLayer.tsx  # Entity rendering
│   │   │   │   └── EffectsLayer.tsx # Particles/effects
│   │   │   ├── ui/
│   │   │   │   ├── HUD.tsx          # Heads-up display
│   │   │   │   ├── Inventory.tsx    # Inventory screen
│   │   │   │   ├── Dialogue.tsx     # Dialogue box
│   │   │   │   ├── QuestLog.tsx     # Quest tracker
│   │   │   │   └── Menu.tsx         # Game menus
│   │   │   └── studio/
│   │   │       ├── TileEditor.tsx   # Tile creation
│   │   │       ├── SpriteEditor.tsx # Sprite creation
│   │   │       ├── AnimEditor.tsx   # Animation editor
│   │   │       └── TilesetManager.tsx
│   │   ├── engine/
│   │   │   ├── renderer.ts          # Glyph render engine
│   │   │   ├── camera.ts            # Camera system
│   │   │   ├── lighting.ts          # Lighting system
│   │   │   ├── animation.ts         # Animation system
│   │   │   └── input.ts             # Input handling
│   │   ├── state/
│   │   │   ├── gameStore.ts         # Global game state
│   │   │   ├── worldStore.ts        # World state
│   │   │   └── uiStore.ts           # UI state
│   │   ├── api/
│   │   │   └── client.ts            # Backend API client
│   │   ├── utils/
│   │   │   ├── glyph.ts             # Glyph mapping utilities
│   │   │   ├── pathfinding.ts       # A* pathfinding
│   │   │   └── random.ts            # Seeded random
│   │   ├── fonts/
│   │   │   └── ...                  # Custom font files
│   │   └── assets/
│   │       ├── audio/
│   │       └── data/
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── package.json
├── tools/
│   ├── font-compiler/               # Pixel art to font converter
│   └── tileset-validator/           # Tileset validation tool
├── docs/
│   ├── api.md                       # API documentation
│   ├── modding.md                   # Modding guide
│   └── tileset-creation.md          # Tileset creation guide
├── SPEC.md                          # This file
├── README.md
└── LICENSE
```

---

## 13. Development Roadmap

### Phase 1: Foundation
- [ ] Core glyph rendering engine
- [ ] Basic tile/sprite editor
- [ ] Single-layer world generation
- [ ] Player movement and collision
- [ ] Basic LLM scene interpretation

### Phase 2: RPG Core
- [ ] Character stat system
- [ ] Inventory and equipment
- [ ] Turn-based combat
- [ ] Basic NPC dialogue (LLM)
- [ ] Quest system foundation

### Phase 3: World Depth
- [ ] Multi-layer world (underground)
- [ ] Dungeon generation
- [ ] Lighting and fog of war
- [ ] Weather system
- [ ] Time of day cycle

### Phase 4: Intelligence
- [ ] Full NPC mind system
- [ ] Dynamic quest generation
- [ ] Sprite behavior director
- [ ] Memory persistence
- [ ] Relationship system

### Phase 5: Polish
- [ ] Full art studio suite
- [ ] Audio system
- [ ] Save/load system
- [ ] Performance optimization
- [ ] Mod support

### Phase 6: Extended
- [ ] Multiplayer foundation
- [ ] Advanced combat (abilities/skills)
- [ ] Crafting system
- [ ] Achievement system
- [ ] Steam/distribution packaging

---

## Appendix A: Comparison Matrix

| Feature | ASCII-City | Tile-Crawler (Original) | Glyph Engine (This Spec) |
|---------|------------|-------------------------|--------------------------|
| Rendering | ASCII chars | Custom font glyphs | Custom font glyphs |
| LLM Control | Full behavioral | Tilemap generation | Interpretation only |
| World Layers | Single | Single | Multi (sky to abyss) |
| Art Tools | ASCII studio | External | Built-in full suite |
| Game Type | Simulation | Roguelike | RPG |
| Combat | Emergent | LLM-narrated | Deterministic + narration |
| NPCs | Behavioral circuits | Basic dialogue | Full mind simulation |
| Rendering FPS | Variable | Variable | Guaranteed 60 |
| LLM in render | Yes | Yes | Never (async only) |

---

*Glyph Engine v1.0 Specification - Tile-Crawler Project*
