# Data Schemas

## Overview

This document defines the data structures and schemas used throughout Tile-Crawler for game state, entities, items, and configuration.

## Core Types

### Position

```typescript
interface Position {
  x: number;  // Horizontal coordinate (0 = left)
  y: number;  // Vertical coordinate (0 = top)
}
```

### Direction

```typescript
type CardinalDirection = 'north' | 'south' | 'east' | 'west';
type DiagonalDirection = 'northeast' | 'northwest' | 'southeast' | 'southwest';
type Direction = CardinalDirection | DiagonalDirection;

// Movement vectors
const DIRECTION_VECTORS: Record<Direction, Position> = {
  north: { x: 0, y: -1 },
  south: { x: 0, y: 1 },
  east: { x: 1, y: 0 },
  west: { x: -1, y: 0 },
  northeast: { x: 1, y: -1 },
  northwest: { x: -1, y: -1 },
  southeast: { x: 1, y: 1 },
  southwest: { x: -1, y: 1 }
};
```

## Player Schema

### Player

```typescript
interface Player {
  id: string;
  name: string;
  class: PlayerClass;
  level: number;
  experience: number;
  experienceToNextLevel: number;

  // Resources
  currentHP: number;
  maxHP: number;
  currentMP: number;
  maxMP: number;

  // Position
  position: Position;
  facing: Direction;

  // Stats
  baseStats: PrimaryStats;
  allocatedStats: PrimaryStats;
  derivedStats: DerivedStats;

  // Equipment & Inventory
  equipment: EquipmentSlots;
  inventory: InventorySlot[];
  gold: number;

  // Skills
  skills: LearnedSkill[];
  skillPoints: number;
  statPoints: number;

  // Status
  statusEffects: ActiveStatusEffect[];

  // Meta
  playTime: number;  // seconds
  deaths: number;
  enemiesDefeated: number;
}

type PlayerClass = 'warrior' | 'mage' | 'rogue' | 'cleric';
```

### Primary Stats

```typescript
interface PrimaryStats {
  strength: number;      // STR: Physical damage, carry capacity
  dexterity: number;     // DEX: Accuracy, evasion, crit
  constitution: number;  // CON: HP, resistances
  intelligence: number;  // INT: Magic damage, MP
  wisdom: number;        // WIS: Detection, magic resist
  charisma: number;      // CHA: NPC relations, prices
}
```

### Derived Stats

```typescript
interface DerivedStats {
  attack: number;
  defense: number;
  accuracy: number;
  evasion: number;
  criticalChance: number;   // 0.0 - 1.0
  criticalDamage: number;   // Multiplier (e.g., 1.5)
  initiative: number;
  moveSpeed: number;
  carryCapacity: number;
}
```

### Equipment Slots

```typescript
interface EquipmentSlots {
  weapon: EquippedItem | null;
  offhand: EquippedItem | null;    // Shield or second weapon
  head: EquippedItem | null;
  body: EquippedItem | null;
  hands: EquippedItem | null;
  feet: EquippedItem | null;
  accessory1: EquippedItem | null;
  accessory2: EquippedItem | null;
}

interface EquippedItem {
  itemId: string;
  instanceId: string;   // Unique instance for tracking durability/enchants
  durability?: number;
  enchantments?: Enchantment[];
}
```

## Item Schemas

### Base Item

```typescript
interface Item {
  id: string;
  name: string;
  description: string;
  type: ItemType;
  rarity: ItemRarity;
  weight: number;
  value: number;        // Base gold value
  stackable: boolean;
  maxStack: number;
  icon: string;         // Glyph character
}

type ItemType =
  | 'weapon'
  | 'armor'
  | 'accessory'
  | 'consumable'
  | 'material'
  | 'quest'
  | 'key'
  | 'misc';

type ItemRarity =
  | 'common'
  | 'uncommon'
  | 'rare'
  | 'epic'
  | 'legendary';
```

### Weapon

```typescript
interface Weapon extends Item {
  type: 'weapon';
  weaponType: WeaponType;
  damage: DamageRange;
  damageType: DamageType;
  attackSpeed: number;   // Attacks per turn (usually 1)
  range: number;         // Tiles (1 = melee)
  twoHanded: boolean;
  requirements: StatRequirements;
  bonuses: StatBonuses;
}

type WeaponType =
  | 'sword'
  | 'axe'
  | 'mace'
  | 'dagger'
  | 'spear'
  | 'bow'
  | 'crossbow'
  | 'staff'
  | 'wand';

interface DamageRange {
  min: number;
  max: number;
}

type DamageType =
  | 'physical'
  | 'fire'
  | 'ice'
  | 'lightning'
  | 'poison'
  | 'holy'
  | 'dark';
```

### Armor

```typescript
interface Armor extends Item {
  type: 'armor';
  armorType: ArmorType;
  slot: ArmorSlot;
  defense: number;
  resistances: Resistances;
  armorPenalty: number;  // Evasion penalty
  requirements: StatRequirements;
  bonuses: StatBonuses;
}

type ArmorType = 'cloth' | 'leather' | 'chain' | 'plate';
type ArmorSlot = 'head' | 'body' | 'hands' | 'feet';

interface Resistances {
  fire?: number;
  ice?: number;
  lightning?: number;
  poison?: number;
  holy?: number;
  dark?: number;
}
```

### Consumable

```typescript
interface Consumable extends Item {
  type: 'consumable';
  consumableType: ConsumableType;
  effects: ConsumableEffect[];
  cooldown?: number;  // Turns before can use again
}

type ConsumableType =
  | 'potion'
  | 'food'
  | 'scroll'
  | 'bomb';

interface ConsumableEffect {
  type: EffectType;
  value: number;
  duration?: number;  // Turns (for buffs/debuffs)
  target: EffectTarget;
}

type EffectType =
  | 'heal_hp'
  | 'heal_mp'
  | 'buff_attack'
  | 'buff_defense'
  | 'cure_poison'
  | 'cure_all'
  | 'damage_fire'
  | 'damage_ice';

type EffectTarget = 'self' | 'single_enemy' | 'all_enemies' | 'area';
```

### Inventory Slot

```typescript
interface InventorySlot {
  itemId: string;
  instanceId: string;
  quantity: number;
  durability?: number;
  enchantments?: Enchantment[];
}
```

## Entity Schemas

### Base Entity

```typescript
interface Entity {
  id: string;
  instanceId: string;
  name: string;
  glyph: string;
  position: Position;
  faction: Faction;
  state: EntityState;
}

type Faction =
  | 'player'
  | 'friendly'
  | 'neutral'
  | 'hostile'
  | 'wildlife';

type EntityState =
  | 'idle'
  | 'patrol'
  | 'alert'
  | 'hostile'
  | 'fleeing'
  | 'talking'
  | 'dead';
```

### Enemy

```typescript
interface Enemy extends Entity {
  enemyType: string;
  level: number;

  // Combat stats
  currentHP: number;
  maxHP: number;
  attack: number;
  defense: number;
  accuracy: number;
  evasion: number;
  initiative: number;

  // Behavior
  aiType: AIType;
  detectionRange: number;
  aggroRange: number;
  behaviors: BehaviorConfig[];

  // Rewards
  experienceReward: number;
  goldReward: GoldRange;
  lootTable: LootTableEntry[];

  // Status
  statusEffects: ActiveStatusEffect[];
}

type AIType =
  | 'melee_basic'
  | 'ranged_basic'
  | 'caster'
  | 'support'
  | 'boss';

interface GoldRange {
  min: number;
  max: number;
}

interface LootTableEntry {
  itemId: string;
  dropChance: number;  // 0.0 - 1.0
  quantityRange: { min: number; max: number };
}
```

### NPC

```typescript
interface NPC extends Entity {
  role: NPCRole;
  personality: Personality;
  knowledge: KnowledgeEntry[];
  relationship: number;  // -100 to 100

  // Dialogue
  dialogueTree?: DialogueTree;
  greetings: string[];

  // Shop (if merchant)
  shopInventory?: ShopItem[];

  // Quests (if quest giver)
  availableQuests?: string[];

  // Schedule
  schedule?: NPCSchedule;
}

type NPCRole =
  | 'merchant'
  | 'quest_giver'
  | 'innkeeper'
  | 'blacksmith'
  | 'sage'
  | 'guard'
  | 'companion'
  | 'villager';

interface Personality {
  traits: PersonalityTrait[];
  speechStyle: SpeechStyle;
  motivations: string[];
  fears: string[];
}

type PersonalityTrait =
  | 'friendly'
  | 'grumpy'
  | 'mysterious'
  | 'cheerful'
  | 'suspicious'
  | 'scholarly'
  | 'greedy'
  | 'noble'
  | 'cowardly'
  | 'brave';

interface SpeechStyle {
  vocabulary: 'simple' | 'formal' | 'archaic' | 'slang';
  verbosity: 'terse' | 'normal' | 'verbose';
  quirks: string[];
}
```

## World Schemas

### Room

```typescript
interface Room {
  id: string;
  coordinates: Position;
  zone: string;
  biome: BiomeType;

  // Layout
  tilemap: string[];
  width: number;
  height: number;

  // Content
  description: string;
  entities: Entity[];
  items: ItemDrop[];
  exits: Exit[];

  // State
  visited: boolean;
  cleared: boolean;
  changes: RoomChange[];

  // Events
  events: RoomEvent[];
  secrets: Secret[];
}

type BiomeType =
  | 'dungeon'
  | 'forest'
  | 'cave'
  | 'castle'
  | 'ruins'
  | 'swamp'
  | 'desert'
  | 'mountain';

interface Exit {
  direction: Direction;
  targetRoom: string;
  locked: boolean;
  keyRequired?: string;
}

interface ItemDrop {
  itemId: string;
  instanceId: string;
  position: Position;
  quantity: number;
}

interface RoomChange {
  type: 'tile_changed' | 'item_removed' | 'entity_removed';
  position: Position;
  oldValue: string;
  newValue: string;
  timestamp: number;
}
```

### Zone

```typescript
interface Zone {
  id: string;
  name: string;
  description: string;
  biome: BiomeType;
  difficulty: number;  // 1-10

  // Rooms
  rooms: Map<string, Room>;
  startRoom: string;
  bossRoom?: string;

  // Connections
  connections: ZoneConnection[];

  // Theme
  narrativeTheme: string;
  ambientDescriptions: string[];

  // Spawning
  enemyTable: SpawnTableEntry[];
  npcTable: SpawnTableEntry[];
  itemTable: SpawnTableEntry[];
}

interface ZoneConnection {
  direction: Direction;
  targetZone: string;
  requirements?: string[];
}

interface SpawnTableEntry {
  id: string;
  weight: number;
  minLevel?: number;
  maxLevel?: number;
}
```

## Quest Schemas

### Quest

```typescript
interface Quest {
  id: string;
  title: string;
  description: string;
  type: QuestType;
  giver: string;  // NPC ID

  // Progress
  state: QuestState;
  objectives: QuestObjective[];

  // Requirements
  prerequisites: string[];  // Quest IDs
  levelRequirement?: number;

  // Rewards
  rewards: QuestRewards;

  // Optional
  timeLimit?: number;  // Turns
  failureConditions?: FailureCondition[];
}

type QuestType =
  | 'main'
  | 'side'
  | 'bounty'
  | 'fetch'
  | 'escort'
  | 'discovery';

type QuestState =
  | 'available'
  | 'active'
  | 'completed'
  | 'failed'
  | 'turned_in';

interface QuestObjective {
  id: string;
  description: string;
  type: ObjectiveType;
  target: string;
  currentProgress: number;
  requiredProgress: number;
  completed: boolean;
  optional: boolean;
}

type ObjectiveType =
  | 'kill'
  | 'collect'
  | 'talk'
  | 'reach'
  | 'protect'
  | 'deliver'
  | 'survive';

interface QuestRewards {
  experience: number;
  gold: number;
  items: RewardItem[];
  reputation?: ReputationReward[];
  unlocks?: string[];  // Quest IDs, zones, etc.
}

interface RewardItem {
  itemId: string;
  quantity: number;
}
```

## Skill Schemas

### Skill

```typescript
interface Skill {
  id: string;
  name: string;
  description: string;
  category: SkillCategory;
  type: SkillType;

  // Cost
  mpCost: number;
  cooldown: number;  // Turns

  // Requirements
  levelRequirement: number;
  statRequirements?: StatRequirements;
  prerequisiteSkills?: string[];

  // Effects
  effects: SkillEffect[];
  targeting: TargetingConfig;

  // Visual
  icon: string;
  animation?: string;
}

type SkillCategory =
  | 'combat'
  | 'magic'
  | 'support'
  | 'passive'
  | 'utility';

type SkillType =
  | 'active'
  | 'passive'
  | 'toggle';

interface SkillEffect {
  type: SkillEffectType;
  value: number;
  scaling?: StatScaling;
  duration?: number;
  chance?: number;
}

type SkillEffectType =
  | 'damage'
  | 'heal'
  | 'buff'
  | 'debuff'
  | 'summon'
  | 'teleport'
  | 'stealth';

interface TargetingConfig {
  type: TargetType;
  range: number;
  areaOfEffect?: AreaOfEffect;
}

type TargetType =
  | 'self'
  | 'single_ally'
  | 'single_enemy'
  | 'all_allies'
  | 'all_enemies'
  | 'area';
```

### Learned Skill

```typescript
interface LearnedSkill {
  skillId: string;
  level: number;
  experience: number;
  cooldownRemaining: number;
  assigned: boolean;
  quickSlot?: number;  // 1-4 for quick access
}
```

## Status Effect Schemas

```typescript
interface StatusEffect {
  id: string;
  name: string;
  description: string;
  type: StatusEffectType;
  category: StatusCategory;

  // Effect
  effect: StatusEffectValue;
  stackable: boolean;
  maxStacks: number;

  // Visual
  icon: string;
  color: string;
}

type StatusEffectType =
  | 'damage_over_time'
  | 'heal_over_time'
  | 'stat_modifier'
  | 'control'
  | 'immunity';

type StatusCategory =
  | 'buff'
  | 'debuff'
  | 'neutral';

interface ActiveStatusEffect {
  effectId: string;
  source: string;
  stacks: number;
  remainingDuration: number;
  ticksRemaining: number;
}
```

## Input & Controls Schemas

### Input Configuration

```typescript
interface InputConfig {
  controllerEnabled: boolean;
  keyboardEnabled: boolean;
  controllerBindings: ControllerBindings;
  keyboardBindings: KeyboardBindings;
  controllerDeadzone: number;  // 0.0 - 1.0
  inputRepeatDelay: number;    // ms
  inputRepeatRate: number;     // ms
}

interface ControllerBindings {
  // Movement
  moveNorth: ControllerInput;
  moveSouth: ControllerInput;
  moveEast: ControllerInput;
  moveWest: ControllerInput;

  // Actions
  interact: ControllerInput;
  attack: ControllerInput;
  defend: ControllerInput;
  useItem: ControllerInput;

  // UI
  openInventory: ControllerInput;
  openMap: ControllerInput;
  openMenu: ControllerInput;
  confirm: ControllerInput;
  cancel: ControllerInput;

  // Navigation
  nextTarget: ControllerInput;
  prevTarget: ControllerInput;
}

type ControllerInput =
  | 'button_a'
  | 'button_b'
  | 'button_x'
  | 'button_y'
  | 'dpad_up'
  | 'dpad_down'
  | 'dpad_left'
  | 'dpad_right'
  | 'left_stick_up'
  | 'left_stick_down'
  | 'left_stick_left'
  | 'left_stick_right'
  | 'left_stick_click'
  | 'right_stick_click'
  | 'left_bumper'
  | 'right_bumper'
  | 'left_trigger'
  | 'right_trigger'
  | 'start'
  | 'select';

interface KeyboardBindings {
  moveNorth: string;   // e.g., 'w' or 'ArrowUp'
  moveSouth: string;
  moveEast: string;
  moveWest: string;
  moveNortheast: string;
  moveNorthwest: string;
  moveSoutheast: string;
  moveSouthwest: string;
  interact: string;
  attack: string;
  defend: string;
  useItem: string;
  openInventory: string;
  openMap: string;
  openMenu: string;
  confirm: string;
  cancel: string;
  quickSave: string;
  quickLoad: string;
}
```

**Note:** Mouse bindings are intentionally not included. Mouse input is disabled during gameplay and is only available for button mapping in the settings menu.

## Save File Schema

### Complete Save Structure

```typescript
interface SaveFile {
  version: string;
  metadata: SaveMetadata;
  player: PlayerSaveData;
  world: WorldSaveData;
  narrative: NarrativeSaveData;
  quests: QuestSaveData;
  settings: SettingsSaveData;
  checksum: string;
}

interface SaveMetadata {
  slot: number;
  name: string;
  createdAt: string;      // ISO 8601
  lastPlayedAt: string;   // ISO 8601
  playTime: number;       // Seconds
  playerLevel: number;
  location: string;
  difficulty: string;
  thumbnail?: string;     // Base64
}
```

## API Response Schemas

### Standard Response

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  timestamp: string;
}

interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}
```

### Game State Response

```typescript
interface GameStateResponse {
  map: string[];
  description: string;
  player: PlayerState;
  entities: EntityState[];
  items: ItemDrop[];
  events: GameEvent[];
  turn: number;
}

interface GameEvent {
  type: string;
  message: string;
  data?: Record<string, unknown>;
  timestamp: number;
}
```

## Validation

All schemas should be validated using JSON Schema or TypeScript type checking. Key validations include:

- **Position:** x and y must be non-negative integers
- **Stats:** Must be positive integers (1-999 typical range)
- **HP/MP:** Current cannot exceed max
- **Percentages:** Must be 0.0 - 1.0
- **IDs:** Must be non-empty strings matching pattern `^[a-z_]+$`
- **Quantities:** Must be positive integers

## Version History

| Version | Changes |
|---------|---------|
| 1.0 | Initial schema definitions |
| 1.1 | Added skill system schemas |
| 1.2 | Added input configuration schemas |
| 2.0 | Restructured entity hierarchy |
