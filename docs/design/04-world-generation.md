# World Generation Design Document

## Overview

The World Generation system in Tile-Crawler combines traditional procedural generation techniques with LLM-powered dynamic content creation. This hybrid approach provides both structural consistency and narrative richness that pure algorithmic or pure LLM approaches cannot achieve alone.

## Core Philosophy

1. **Procedural Foundation:** Algorithms generate world structure, terrain, and room layouts
2. **LLM Enhancement:** AI adds narrative depth, descriptions, and contextual details
3. **Persistent Memory:** Generated content is stored and remains consistent
4. **Player Agency:** World responds to player actions and choices

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    World Generation Pipeline                     │
│                                                                  │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────┐ │
│  │   Seed-Based   │    │   LLM Content  │    │   World State  │ │
│  │   Procedural   │───▶│   Enhancement  │───▶│   Storage      │ │
│  │   Generator    │    │                │    │                │ │
│  └────────────────┘    └────────────────┘    └────────────────┘ │
│          │                    │                      │          │
│          ▼                    ▼                      ▼          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  Unified World Model                        │ │
│  │  (Rooms, Corridors, NPCs, Items, Events, Narrative)        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Generation Layers

### Layer 1: Macro World Structure

Large-scale world organization:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Overworld Map                            │
│                                                                  │
│    [Forest Zone]──────[Plains Zone]──────[Mountain Zone]        │
│         │                   │                   │                │
│         │                   │                   │                │
│    [Swamp Zone]────────[Castle]─────────[Desert Zone]           │
│         │                   │                   │                │
│         │                   │                   │                │
│    [Cave System]───────[Dungeon]─────────[Ruins Zone]           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 2: Zone Generation

Each zone contains multiple areas:

```typescript
interface Zone {
  id: string;
  name: string;
  biome: BiomeType;
  difficulty: number;        // 1-10
  areas: Area[];
  connections: ZoneConnection[];
  theme: NarrativeTheme;
}

type BiomeType =
  | 'forest'
  | 'dungeon'
  | 'castle'
  | 'cave'
  | 'ruins'
  | 'swamp'
  | 'desert'
  | 'mountain';
```

### Layer 3: Area/Dungeon Generation

Individual dungeons and areas within zones:

```
┌───────────────────────────────────────┐
│           Dungeon Layout              │
│                                       │
│   ┌───┐         ┌───┐                │
│   │ 1 │─────────│ 2 │                │
│   └─┬─┘         └─┬─┘                │
│     │             │                   │
│   ┌─┴─┐    ┌───┐┌─┴─┐                │
│   │ 3 │────│ 4 ││ 5 │                │
│   └───┘    └─┬─┘└───┘                │
│              │                        │
│            ┌─┴─┐                      │
│            │ B │  (Boss Room)         │
│            └───┘                      │
└───────────────────────────────────────┘
```

### Layer 4: Room Generation

Individual room layouts with tile placement:

```
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
▓░░░░░░░░░░░░░▓
▓░░░░░░░░░░░░░▓
▓░░░░░░☺░░░░░░▓     ← NPC
▓░░░░░░░░░░░░░▓
▓░░░$░░░░░░░░░▓     ← Item
▓░░░░░░░░░░░░░▓
▓░░░░░░░░@░░░░▓     ← Player
▓▓▓▓▓▓░░░▓▓▓▓▓▓     ← Door/Exit
```

## Procedural Algorithms

### Room Layout Algorithms

#### BSP (Binary Space Partitioning)

```typescript
class BSPGenerator {
  generate(width: number, height: number, depth: number): Room[] {
    const root = new BSPNode(0, 0, width, height);
    this.split(root, depth);
    return this.createRooms(root);
  }

  private split(node: BSPNode, depth: number): void {
    if (depth <= 0) return;

    const splitHorizontal = Math.random() > 0.5;
    // Split logic...
  }
}
```

#### Cellular Automata (Caves)

```typescript
class CaveGenerator {
  generate(width: number, height: number, iterations: number): Tile[][] {
    let grid = this.initializeRandom(width, height, 0.45);

    for (let i = 0; i < iterations; i++) {
      grid = this.iterate(grid);
    }

    return grid;
  }

  private iterate(grid: Tile[][]): Tile[][] {
    // 4-5 rule: become wall if 5+ neighbors are walls
    // become floor if 4+ neighbors are floors
  }
}
```

#### Drunkard's Walk (Organic Paths)

```typescript
class DrunkardWalkGenerator {
  generate(width: number, height: number, fillPercent: number): Tile[][] {
    const grid = this.createSolidGrid(width, height);
    let x = Math.floor(width / 2);
    let y = Math.floor(height / 2);

    while (this.getFloorPercent(grid) < fillPercent) {
      grid[y][x] = TileType.Floor;
      // Random direction movement
      const dir = this.randomDirection();
      x += dir.x;
      y += dir.y;
    }

    return grid;
  }
}
```

## LLM Integration

### Content Enhancement Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM Enhancement Flow                          │
│                                                                  │
│  Procedural Room                LLM Prompt                       │
│  ┌───────────────┐    ┌─────────────────────────────────────┐  │
│  │ Layout: 10x10 │    │ "Generate a description for a       │  │
│  │ Type: Library │───▶│ dungeon library room. Include:      │  │
│  │ Items: [book] │    │ - Atmospheric description           │  │
│  │ NPCs: [sage]  │    │ - NPC personality/dialogue hooks    │  │
│  └───────────────┘    │ - Item descriptions                 │  │
│                       │ - Possible secrets/interactions"    │  │
│                       └───────────────────┬─────────────────┘  │
│                                           │                     │
│                                           ▼                     │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ LLM Response:                                            │   │
│  │ "Dusty tomes line crumbling shelves in this forgotten   │   │
│  │ archive. An elderly sage mutters to himself, tracing    │   │
│  │ runes in a massive grimoire. The air smells of old      │   │
│  │ paper and secrets long buried..."                        │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Prompt Templates

```python
ROOM_DESCRIPTION_PROMPT = """
Generate a room description for a {biome} dungeon.

Room Properties:
- Type: {room_type}
- Size: {width}x{height}
- Exits: {exit_directions}
- Contains: {items}
- NPCs present: {npcs}
- Adjacent rooms: {adjacent_rooms}

Previous narrative context:
{narrative_context}

Generate:
1. A 2-3 sentence atmospheric description
2. Any interactive elements the player might notice
3. Hints about connected areas

Keep the tone {tone} and maintain consistency with previous descriptions.
"""
```

## World State Management

### Room State

```typescript
interface RoomState {
  id: string;
  position: { x: number; y: number };
  layout: string[];           // Tilemap
  description: string;        // LLM-generated
  items: Item[];
  npcs: NPC[];
  visited: boolean;
  cleared: boolean;           // All enemies defeated
  secrets: Secret[];
  events: RoomEvent[];
}
```

### Persistence

```python
# world_state.py
class WorldState:
    def __init__(self):
        self.rooms: Dict[str, RoomState] = {}
        self.player_position: Tuple[int, int] = (0, 0)
        self.discovered_zones: Set[str] = set()

    def get_room(self, x: int, y: int) -> Optional[RoomState]:
        key = f"{x},{y}"
        return self.rooms.get(key)

    def save_room(self, room: RoomState) -> None:
        key = f"{room.position['x']},{room.position['y']}"
        self.rooms[key] = room
        self._persist()
```

## Dynamic World Events

### Event System

```typescript
interface WorldEvent {
  id: string;
  type: EventType;
  trigger: EventTrigger;
  conditions: EventCondition[];
  effects: EventEffect[];
  description: string;
}

type EventType =
  | 'ambient'       // Background atmosphere
  | 'encounter'     // Enemy/NPC meeting
  | 'discovery'     // Finding something
  | 'story'         // Narrative progression
  | 'environmental' // World changes
  ;

type EventTrigger =
  | { type: 'enter_room'; roomId: string }
  | { type: 'interact'; targetId: string }
  | { type: 'time_passed'; turns: number }
  | { type: 'item_used'; itemId: string }
  ;
```

### Example Event Flow

```
Player enters room
       │
       ▼
Check event triggers
       │
       ▼
┌──────────────────────────────────────┐
│ Event: "Ancient Guardian Awakens"    │
│ Trigger: enter_room, first_visit     │
│ Conditions: player_has("artifact")   │
└──────────────────┬───────────────────┘
                   │
                   ▼
         Conditions met?
           │      │
          Yes     No
           │      │
           ▼      ▼
    Execute     Skip
     effects   event
```

## Exploration Controls

### Player Movement

The exploration system uses **Xbox controller** and **keyboard** input exclusively:

#### Controller Movement

| Input | Action |
|-------|--------|
| **Left Stick** | 8-directional movement (analog zones) |
| **D-Pad** | 4-directional cardinal movement |
| **A Button** | Interact with tile / Enter door |
| **B Button** | Cancel / Wait one turn |
| **X Button** | Examine current tile |
| **Y Button** | Open map overlay |
| **LB/RB** | Quick-turn (rotate facing) |
| **LT** | Sneak movement (slower, quieter) |
| **RT** | Run movement (faster, louder) |

#### Keyboard Movement

| Key | Action |
|-----|--------|
| **W/Up** | Move North |
| **S/Down** | Move South |
| **A/Left** | Move West |
| **D/Right** | Move East |
| **Q** | Move Northwest |
| **E** | Move Northeast |
| **Z** | Move Southwest |
| **C** | Move Southeast |
| **Space/Enter** | Interact / Enter |
| **Period (.)** | Wait one turn |
| **X** | Examine |
| **M** | Map |
| **Shift+Move** | Run |
| **Ctrl+Move** | Sneak |

### Movement Feedback

Visual and audio feedback for movement:

```
┌─────────────────────────────────────┐
│                                     │
│    ▓▓▓▓▓▓▓▓▓▓▓                     │
│    ▓░░░░░░░░░▓                     │
│    ▓░░░░↑░░░░▓  ← Direction        │
│    ▓░░░[░]░░░▓    indicator         │
│    ▓░░░░@░░░░▓  ← Player           │
│    ▓░░░░░░░░░▓                     │
│    ▓▓▓▓░░░▓▓▓▓                     │
│                                     │
│    [A] Enter    [X] Examine        │
└─────────────────────────────────────┘
```

## Biome Definitions

### Forest Biome

```typescript
const forestBiome: BiomeDefinition = {
  name: "forest",
  tiles: {
    floor: ['░', '♣', '♠'],
    wall: ['▲', '▓'],
    water: ['≈'],
    special: ['⌂', '◊']
  },
  enemies: ['wolf', 'bear', 'bandit', 'spider'],
  items: ['herb', 'wood', 'mushroom', 'berry'],
  ambientDescriptions: [
    "Sunlight filters through the canopy above.",
    "Birds chirp in the distance.",
    "The smell of pine fills the air."
  ]
};
```

### Dungeon Biome

```typescript
const dungeonBiome: BiomeDefinition = {
  name: "dungeon",
  tiles: {
    floor: ['░'],
    wall: ['▓', '╔', '═', '╗', '║', '╚', '╝'],
    water: ['≈'],
    special: ['☼', '†', '◊']
  },
  enemies: ['skeleton', 'zombie', 'ghost', 'rat'],
  items: ['torch', 'key', 'potion', 'gold'],
  ambientDescriptions: [
    "Water drips from the ceiling.",
    "The air is thick with dust.",
    "Distant echoes hint at vast chambers."
  ]
};
```

## Seeded Generation

### Seed System

```python
class SeededGenerator:
    def __init__(self, seed: str):
        self.master_seed = hash(seed)
        self.rng = random.Random(self.master_seed)

    def get_room_seed(self, x: int, y: int) -> int:
        """Deterministic seed for any room coordinate"""
        return hash((self.master_seed, x, y))

    def generate_room(self, x: int, y: int) -> RoomState:
        room_rng = random.Random(self.get_room_seed(x, y))
        # Generation using room_rng ensures reproducibility
```

### Seed Benefits

1. **Shareable Worlds:** Share seeds for identical world layouts
2. **Bug Reproduction:** Recreate exact game states
3. **Speedrun Consistency:** Same seed = same challenges
4. **Testing:** Deterministic world generation for QA

## Performance Optimization

### Lazy Generation

```python
class LazyWorldGenerator:
    def __init__(self, seed: str):
        self.seed = seed
        self.generated_rooms: Dict[str, RoomState] = {}

    def get_room(self, x: int, y: int) -> RoomState:
        key = f"{x},{y}"
        if key not in self.generated_rooms:
            self.generated_rooms[key] = self.generate_room(x, y)
        return self.generated_rooms[key]
```

### Pre-generation Radius

Generate rooms slightly ahead of player:

```
        ┌───┬───┬───┬───┬───┐
        │ G │ G │ G │ G │ G │    G = Generated
        ├───┼───┼───┼───┼───┤
        │ G │ G │ G │ G │ G │
        ├───┼───┼───┼───┼───┤
        │ G │ G │ @ │ G │ G │    @ = Player
        ├───┼───┼───┼───┼───┤
        │ G │ G │ G │ G │ G │
        ├───┼───┼───┼───┼───┤
        │ G │ G │ G │ G │ G │
        └───┴───┴───┴───┴───┘
```

## Future Enhancements

1. **Biome Blending:** Smooth transitions between zone types
2. **Vertical Dungeons:** Multi-level dungeon exploration
3. **Dynamic World Changes:** World evolves over time
4. **Player-Built Structures:** Construction system
5. **Multiplayer World Sharing:** Shared exploration
