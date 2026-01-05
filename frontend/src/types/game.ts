// Game state types for Tile-Crawler

export interface PlayerStats {
  name: string;
  level: number;
  hp: string;
  mana: string;
  xp: string;
  attack: number;
  defense: number;
  speed: number;
  magic: number;
  status_effects: string[];
}

export interface RoomState {
  map: string[];
  description: string;
  biome: string;
  exits: Record<string, boolean>;
  enemies: Enemy[];
  items: RoomItem[];
  npcs: string[];
  features: string[];
}

export interface Enemy {
  id: string;
  name: string;
  hp: number;
  attack: number;
  defense?: number;
}

export interface RoomItem {
  id: string;
  name: string;
  quantity?: number;
}

export interface InventoryItem {
  id: string;
  name: string;
  description: string;
  category: string;
  quantity: number;
  equipped: boolean;
}

export interface CombatState {
  in_combat: boolean;
  enemy_index: number;
  enemy_id: string;
  enemy_name: string;
  enemy_hp: number;
  enemy_max_hp: number;
  enemy_attack: number;
  enemy_defense: number;
  turn: number;
}

export interface NarrativeState {
  recent_events: string;
  story_summary: string;
}

export interface GameStats {
  rooms_explored: number;
  enemies_defeated: number;
  steps_taken: number;
  deaths: number;
}

export interface DialogueData {
  npc_id: string;
  npc_name: string;
  speech: string;
  mood: string;
  hints: string[];
  trade_available: boolean;
}

export interface GameState {
  player: PlayerStats;
  position: number[];
  room: RoomState;
  inventory: InventoryItem[];
  gold: number;
  combat: CombatState | null;
  narrative: NarrativeState;
  stats: GameStats;
}

export interface ActionResponse {
  success: boolean;
  message: string;
  narrative: string;
  map?: string[];
  state?: GameState;
  combat?: CombatState;
  dialogue?: DialogueData;
}

export type Direction = 'north' | 'south' | 'east' | 'west' | 'up' | 'down';

export type GameAction =
  | { type: 'move'; direction: Direction }
  | { type: 'attack' }
  | { type: 'flee' }
  | { type: 'take'; itemId: string }
  | { type: 'use'; itemId: string }
  | { type: 'talk'; message?: string }
  | { type: 'rest' };
