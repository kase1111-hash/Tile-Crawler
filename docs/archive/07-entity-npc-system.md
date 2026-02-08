# Entity & NPC System Design Document

## Overview

The Entity & NPC System manages all non-player characters, enemies, and interactive entities in Tile-Crawler. It combines deterministic behavior patterns with LLM-powered dialogue and decision-making to create believable, dynamic characters.

## Entity Hierarchy

```
┌─────────────────────────────────────────────────────────────────┐
│                      Entity Hierarchy                            │
│                                                                  │
│                        ┌─────────────┐                          │
│                        │   Entity    │                          │
│                        │   (Base)    │                          │
│                        └──────┬──────┘                          │
│                               │                                  │
│         ┌─────────────────────┼─────────────────────┐           │
│         │                     │                     │           │
│         ▼                     ▼                     ▼           │
│   ┌───────────┐        ┌───────────┐        ┌───────────┐      │
│   │  Enemy    │        │    NPC    │        │   Item    │      │
│   │           │        │           │        │  Entity   │      │
│   └─────┬─────┘        └─────┬─────┘        └───────────┘      │
│         │                    │                                   │
│    ┌────┼────┐         ┌─────┼─────┐                            │
│    │    │    │         │     │     │                            │
│    ▼    ▼    ▼         ▼     ▼     ▼                            │
│  Melee Range Boss   Merchant Quest Companion                    │
│                     NPC    Giver                                │
└─────────────────────────────────────────────────────────────────┘
```

## Base Entity Structure

```typescript
interface Entity {
  id: string;
  name: string;
  glyph: string;           // Character representation
  position: Position;
  faction: Faction;        // Determines friend/foe
  stats: EntityStats;
  state: EntityState;
  behaviors: Behavior[];
  inventory: Item[];
  dialogue: DialogueTree | null;
}

interface EntityStats {
  hp: number;
  maxHp: number;
  attack: number;
  defense: number;
  speed: number;
  level: number;
}

enum EntityState {
  IDLE = 'idle',
  PATROL = 'patrol',
  ALERT = 'alert',
  HOSTILE = 'hostile',
  FLEEING = 'fleeing',
  TALKING = 'talking',
  DEAD = 'dead'
}

enum Faction {
  PLAYER = 'player',
  FRIENDLY = 'friendly',
  NEUTRAL = 'neutral',
  HOSTILE = 'hostile',
  WILDLIFE = 'wildlife'
}
```

## Enemy System

### Enemy Types

#### Basic Enemies

| Name | Glyph | Behavior | Difficulty |
|------|-------|----------|------------|
| Rat | `R` | Swarm, flee at low HP | 1 |
| Bat | `B` | Erratic movement | 1 |
| Goblin | `G` | Basic melee | 2 |
| Skeleton | `S` | Relentless pursuit | 3 |
| Orc | `O` | Heavy damage | 4 |
| Zombie | `Z` | Slow but durable | 3 |
| Wolf | `W` | Pack tactics | 3 |
| Ghost | `φ` | Phase through walls | 5 |

#### Elite Enemies

| Name | Glyph | Special Ability |
|------|-------|-----------------|
| Goblin Shaman | `g` | Heals nearby goblins |
| Orc Berserker | `o` | Enrage at low HP |
| Skeletal Mage | `s` | Ranged magic attacks |
| Alpha Wolf | `w` | Summons pack |
| Vampire | `V` | Life drain |

#### Bosses

| Name | Glyph | Phase Mechanics |
|------|-------|-----------------|
| Dragon | `D` | Fire breath, flight, tail sweep |
| Lich King | `L` | Summons undead, magic immunity phases |
| Demon Lord | `Ω` | Corruption aura, dimensional shifts |

### Enemy AI Behaviors

```typescript
interface Behavior {
  type: BehaviorType;
  priority: number;
  conditions: Condition[];
  action: () => void;
}

enum BehaviorType {
  IDLE = 'idle',
  PATROL = 'patrol',
  PURSUE = 'pursue',
  ATTACK = 'attack',
  FLEE = 'flee',
  SUPPORT = 'support',
  SPECIAL = 'special'
}

class EnemyAI {
  behaviors: Behavior[];

  selectBehavior(context: AIContext): Behavior {
    // Sort by priority, evaluate conditions
    const validBehaviors = this.behaviors
      .filter(b => b.conditions.every(c => c.evaluate(context)))
      .sort((a, b) => b.priority - a.priority);

    return validBehaviors[0] || this.getDefaultBehavior();
  }
}
```

### Behavior Examples

```python
# Goblin AI
goblin_behaviors = [
    Behavior(
        type=BehaviorType.FLEE,
        priority=100,
        conditions=[
            Condition('hp_below', 0.2),
            Condition('no_allies_nearby')
        ],
        action=FleeAction(direction='away_from_player')
    ),
    Behavior(
        type=BehaviorType.ATTACK,
        priority=80,
        conditions=[
            Condition('player_adjacent')
        ],
        action=AttackAction(target='player')
    ),
    Behavior(
        type=BehaviorType.PURSUE,
        priority=60,
        conditions=[
            Condition('player_visible'),
            Condition('player_in_range', 5)
        ],
        action=PursueAction(target='player')
    ),
    Behavior(
        type=BehaviorType.PATROL,
        priority=20,
        conditions=[],
        action=PatrolAction(pattern='random')
    )
]
```

## NPC System

### NPC Categories

```typescript
enum NPCRole {
  MERCHANT = 'merchant',      // Buy/sell items
  QUEST_GIVER = 'quest_giver', // Provides quests
  INNKEEPER = 'innkeeper',    // Rest and recovery
  BLACKSMITH = 'blacksmith',  // Repair/upgrade equipment
  SAGE = 'sage',              // Information/lore
  GUARD = 'guard',            // Zone protection
  COMPANION = 'companion',    // Joinable ally
  VILLAGER = 'villager'       // Ambient/flavor
}

interface NPC extends Entity {
  role: NPCRole;
  personality: Personality;
  knowledge: Knowledge[];
  schedule: NPCSchedule | null;
  relationship: number;       // -100 to 100
  quests: Quest[];
  shopInventory: Item[] | null;
}
```

### NPC Personality System

```typescript
interface Personality {
  traits: PersonalityTrait[];
  speechStyle: SpeechStyle;
  motivations: string[];
  fears: string[];
  likes: string[];
  dislikes: string[];
}

enum PersonalityTrait {
  FRIENDLY = 'friendly',
  GRUMPY = 'grumpy',
  MYSTERIOUS = 'mysterious',
  CHEERFUL = 'cheerful',
  SUSPICIOUS = 'suspicious',
  SCHOLARLY = 'scholarly',
  GREEDY = 'greedy',
  NOBLE = 'noble',
  COWARDLY = 'cowardly',
  BRAVE = 'brave'
}

interface SpeechStyle {
  vocabulary: 'simple' | 'formal' | 'archaic' | 'slang';
  verbosity: 'terse' | 'normal' | 'verbose';
  quirks: string[];  // Specific speech patterns
}
```

### LLM-Powered Dialogue

```python
NPC_DIALOGUE_PROMPT = """
Generate dialogue for an NPC interaction.

NPC Profile:
- Name: {npc.name}
- Role: {npc.role}
- Personality traits: {', '.join(npc.personality.traits)}
- Speech style: {npc.personality.speech_style.vocabulary}, {npc.personality.speech_style.verbosity}
- Speech quirks: {', '.join(npc.personality.speech_style.quirks)}
- Current mood: {npc.current_mood}
- Relationship with player: {npc.relationship} (-100 to 100)

NPC Knowledge:
{format_knowledge(npc.knowledge)}

Current Context:
- Location: {context.location}
- Time of day: {context.time_of_day}
- Recent events: {context.recent_events}
- Player's last action: {context.player_action}
- Previous dialogue in this conversation:
{context.dialogue_history}

Generate the NPC's next response. Stay in character. Include:
1. Dialogue text
2. Emotional state
3. Any offers/requests
4. Relevant hints or information

Return JSON:
{{
  "dialogue": "...",
  "emotion": "...",
  "actions": [],
  "reveals_info": []
}}
"""
```

## NPC Interaction Controls

All NPC interactions use **Xbox controller** and **keyboard** - no mouse support:

### Controller NPC Interaction

| Input | Action |
|-------|--------|
| **A Button** | Talk / Continue dialogue |
| **B Button** | End conversation / Back |
| **X Button** | View NPC info |
| **Y Button** | Quick action (Buy/Quest/etc.) |
| **Left Stick/D-Pad** | Navigate dialogue options |
| **LB** | Previous dialogue option |
| **RB** | Next dialogue option |
| **LT** | Show relationship status |
| **RT** | Offer gift (if holding item) |

### Keyboard NPC Interaction

| Key | Action |
|-----|--------|
| **Space/Enter** | Talk / Continue dialogue |
| **Escape** | End conversation |
| **X** | View NPC info |
| **E** | Quick action |
| **Arrow Keys/WASD** | Navigate options |
| **1-9** | Quick select dialogue option |
| **G** | Offer gift |
| **Tab** | Toggle relationship view |

### Dialogue Interface

```
┌─────────────────────────────────────────────────────────────────┐
│                      NPC Dialogue                                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              ☺ Marcus the Merchant                       │   │
│  │                  [Friendly]                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ "Ah, a customer! Welcome to my humble shop. Times have  │   │
│  │  been hard since the goblins moved into the hills, but  │   │
│  │  I still have some fine wares for a brave adventurer    │   │
│  │  such as yourself."                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Dialogue Options:                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ >[1] "Show me what you have for sale."                  │   │ ← Selected
│  │  [2] "Tell me about the goblins."                       │   │
│  │  [3] "Have you heard any rumors lately?"                │   │
│  │  [4] "Goodbye."                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [A/Enter] Select    [B/Esc] Leave    [LB/RB] Navigate         │
└─────────────────────────────────────────────────────────────────┘
```

## Shop System

### Shop Interface

```
┌─────────────────────────────────────────────────────────────────┐
│                    Marcus's Shop                                 │
│                                                                  │
│  Your Gold: 1,250                                               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  FOR SALE                           PRICE               │   │
│  │  ────────────────────────────────  ────────             │   │
│  │ >[Healing Potion]                    50g                │   │ ← Cursor
│  │  [Mana Potion]                       40g                │   │
│  │  [Iron Sword]                        200g               │   │
│  │  [Leather Armor]                     150g               │   │
│  │  [Torch] x10                         20g                │   │
│  │  [Antidote]                          30g                │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Item Details:                                                  │
│  Healing Potion - Restores 50 HP instantly                     │
│  Weight: 0.5   Stock: 5                                        │
│                                                                  │
│  [A] Buy    [Y] Sell    [X] Info    [LB/RB] Qty    [B] Exit    │
└─────────────────────────────────────────────────────────────────┘
```

### Shop Controls

| Controller | Keyboard | Action |
|------------|----------|--------|
| A Button | Space/Enter | Buy selected item |
| Y Button | S | Switch to sell mode |
| X Button | I | View item details |
| Left Stick/D-Pad | Arrows/WASD | Navigate items |
| LB | Q | Decrease quantity |
| RB | E | Increase quantity |
| B Button | Escape | Exit shop |

## Quest System

### Quest Structure

```typescript
interface Quest {
  id: string;
  title: string;
  description: string;
  giver: string;            // NPC ID
  type: QuestType;
  objectives: QuestObjective[];
  rewards: QuestReward[];
  prerequisites: string[];  // Quest IDs
  timeLimit: number | null; // Turns, or null for no limit
  state: QuestState;
}

enum QuestType {
  MAIN = 'main',
  SIDE = 'side',
  BOUNTY = 'bounty',
  FETCH = 'fetch',
  ESCORT = 'escort',
  DISCOVERY = 'discovery'
}

interface QuestObjective {
  id: string;
  description: string;
  type: ObjectiveType;
  target: string;
  currentCount: number;
  requiredCount: number;
  completed: boolean;
  optional: boolean;
}

enum ObjectiveType {
  KILL = 'kill',
  COLLECT = 'collect',
  TALK = 'talk',
  REACH = 'reach',
  PROTECT = 'protect',
  DELIVER = 'deliver'
}
```

### Quest Log Interface

```
┌─────────────────────────────────────────────────────────────────┐
│                        Quest Log                                 │
│                                                                  │
│  [Active] [Completed] [Failed]                                  │
│   ^^^^^^                                                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ACTIVE QUESTS                                          │   │
│  │  ────────────────────────────────────────────────────   │   │
│  │ >[★] The Goblin Menace (Main Quest)                    │   │ ← Selected
│  │  [ ] Lost Heirloom (Side Quest)                        │   │
│  │  [ ] Rat Extermination (Bounty)                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  THE GOBLIN MENACE                                              │
│  ─────────────────                                              │
│  Marcus the Merchant has asked you to deal with the goblins    │
│  that have been raiding trade caravans.                        │
│                                                                  │
│  Objectives:                                                    │
│  [■] Speak with the village guard (1/1)                        │
│  [□] Find the goblin camp (0/1)                                │
│  [□] Defeat the goblin chief (0/1)                             │
│                                                                  │
│  Rewards: 500 gold, Iron Sword                                 │
│                                                                  │
│  [A] Track Quest    [X] Abandon    [LB/RB] Switch Tab          │
└─────────────────────────────────────────────────────────────────┘
```

## Entity Spawning

### Spawn Rules

```python
class EntitySpawner:
    def spawn_enemies_for_room(
        self,
        room: Room,
        difficulty: int
    ) -> List[Enemy]:
        """Spawn appropriate enemies for a room"""
        budget = self.calculate_spawn_budget(difficulty)
        enemies = []

        while budget > 0:
            valid_enemies = [
                e for e in self.enemy_templates
                if e.cost <= budget and e.min_difficulty <= difficulty
            ]

            if not valid_enemies:
                break

            enemy_template = self.weighted_random_choice(valid_enemies)
            spawn_pos = self.find_valid_spawn_position(room, enemies)

            if spawn_pos:
                enemy = self.create_enemy(enemy_template, spawn_pos)
                enemies.append(enemy)
                budget -= enemy_template.cost

        return enemies

    def spawn_npcs_for_location(
        self,
        location: Location,
        context: GameContext
    ) -> List[NPC]:
        """Spawn contextually appropriate NPCs"""
        npcs = []

        for npc_slot in location.npc_slots:
            if self.should_spawn_npc(npc_slot, context):
                npc = self.create_npc(npc_slot.role, npc_slot.position)
                npcs.append(npc)

        return npcs
```

## Pathfinding

### A* Implementation

```typescript
class Pathfinder {
  findPath(
    start: Position,
    end: Position,
    grid: TileGrid,
    entity: Entity
  ): Position[] | null {
    const openSet = new PriorityQueue<PathNode>();
    const closedSet = new Set<string>();
    const cameFrom = new Map<string, Position>();

    openSet.enqueue({
      position: start,
      gScore: 0,
      fScore: this.heuristic(start, end)
    });

    while (!openSet.isEmpty()) {
      const current = openSet.dequeue()!;

      if (this.positionEquals(current.position, end)) {
        return this.reconstructPath(cameFrom, current.position);
      }

      closedSet.add(this.posKey(current.position));

      for (const neighbor of this.getNeighbors(current.position, grid, entity)) {
        if (closedSet.has(this.posKey(neighbor))) continue;

        const tentativeG = current.gScore + this.moveCost(current.position, neighbor);
        const existing = openSet.find(n =>
          this.positionEquals(n.position, neighbor)
        );

        if (!existing || tentativeG < existing.gScore) {
          cameFrom.set(this.posKey(neighbor), current.position);
          openSet.enqueue({
            position: neighbor,
            gScore: tentativeG,
            fScore: tentativeG + this.heuristic(neighbor, end)
          });
        }
      }
    }

    return null; // No path found
  }
}
```

## Entity Events

### Event System

```typescript
enum EntityEvent {
  SPAWNED = 'spawned',
  DIED = 'died',
  DAMAGED = 'damaged',
  HEALED = 'healed',
  STATE_CHANGED = 'state_changed',
  LEVEL_UP = 'level_up',
  ITEM_DROPPED = 'item_dropped',
  DIALOGUE_STARTED = 'dialogue_started',
  DIALOGUE_ENDED = 'dialogue_ended',
  QUEST_OFFERED = 'quest_offered',
  QUEST_COMPLETED = 'quest_completed'
}

interface EntityEventData {
  entity: Entity;
  event: EntityEvent;
  data: Record<string, any>;
  timestamp: number;
}

class EntityEventBus {
  private listeners: Map<EntityEvent, EntityEventListener[]> = new Map();

  emit(event: EntityEvent, entity: Entity, data: Record<string, any>): void {
    const listeners = this.listeners.get(event) || [];
    const eventData: EntityEventData = {
      entity,
      event,
      data,
      timestamp: Date.now()
    };

    for (const listener of listeners) {
      listener(eventData);
    }
  }

  on(event: EntityEvent, listener: EntityEventListener): void {
    const listeners = this.listeners.get(event) || [];
    listeners.push(listener);
    this.listeners.set(event, listeners);
  }
}
```

## Performance Considerations

### Entity Culling

```typescript
class EntityManager {
  private activeEntities: Map<string, Entity> = new Map();
  private dormantEntities: Map<string, Entity> = new Map();

  updateActiveEntities(playerPosition: Position, viewDistance: number): void {
    // Deactivate far entities
    for (const [id, entity] of this.activeEntities) {
      if (this.distance(entity.position, playerPosition) > viewDistance * 2) {
        this.dormantEntities.set(id, entity);
        this.activeEntities.delete(id);
      }
    }

    // Activate nearby dormant entities
    for (const [id, entity] of this.dormantEntities) {
      if (this.distance(entity.position, playerPosition) <= viewDistance) {
        this.activeEntities.set(id, entity);
        this.dormantEntities.delete(id);
      }
    }
  }
}
```

## Future Enhancements

1. **Companion System:** Recruit NPCs to join your party
2. **Faction Reputation:** Complex faction relationships
3. **NPC Schedules:** Time-based NPC activities
4. **Dynamic Relationships:** NPCs remember and react to player actions
5. **Procedural Personalities:** LLM-generated unique NPC traits
