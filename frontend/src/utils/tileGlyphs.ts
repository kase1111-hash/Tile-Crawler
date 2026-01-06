/**
 * Tile Glyph Utilities
 *
 * Helpers for using custom TileCrawler font glyphs in rendering.
 * Glyphs are mapped to Unicode Private Use Area (U+E000-U+EBFF).
 */

// Glyph codepoint bands by category
export const GLYPH_BANDS = {
  EMPTY: [0xE000, 0xE0FF],
  GROUND: [0xE100, 0xE1FF],
  WALL: [0xE200, 0xE2FF],
  DOOR: [0xE300, 0xE3FF],
  FLUID: [0xE400, 0xE4FF],
  PROP: [0xE500, 0xE5FF],
  ITEM: [0xE600, 0xE6FF],
  ENTITY: [0xE700, 0xE7FF],
  EFFECT: [0xE800, 0xE8FF],
  UI: [0xE900, 0xE9FF],
  OVERLAY: [0xEA00, 0xEAFF],
  ANIMATION: [0xEB00, 0xEBFF],
} as const;

// Common glyph codepoints (from glyphs.json)
export const GLYPHS = {
  // Empty
  VOID: 0xE000,
  AIR: 0xE001,

  // Ground/Floor
  FLOOR_STONE: 0xE100,
  FLOOR_CRACKED: 0xE101,
  FLOOR_DIRT: 0xE102,
  FLOOR_GRASS: 0xE103,
  FLOOR_SAND: 0xE104,
  FLOOR_WOOD: 0xE105,
  FLOOR_TILE: 0xE106,
  FLOOR_MOSS: 0xE107,

  // Walls
  WALL_STONE: 0xE200,
  WALL_BRICK: 0xE201,
  WALL_DUNGEON: 0xE202,
  WALL_CAVE: 0xE203,
  WALL_CRACKED: 0xE204,
  WALL_MOSS: 0xE205,
  WALL_TORCH: 0xE206,

  // Doors
  DOOR_WOOD_CLOSED: 0xE300,
  DOOR_WOOD_OPEN: 0xE301,
  DOOR_IRON_CLOSED: 0xE302,
  DOOR_IRON_OPEN: 0xE303,
  DOOR_SECRET: 0xE304,
  DOOR_GATE: 0xE305,
  DOOR_ARCH: 0xE306,

  // Fluids
  WATER: 0xE400,
  WATER_DEEP: 0xE401,
  LAVA: 0xE402,
  LAVA_FLOW: 0xE403,
  ACID: 0xE404,
  BLOOD: 0xE405,
  SWAMP: 0xE406,

  // Props
  STAIRS_DOWN: 0xE500,
  STAIRS_UP: 0xE501,
  CHEST_CLOSED: 0xE502,
  CHEST_OPEN: 0xE503,
  ALTAR: 0xE504,
  PILLAR: 0xE505,
  FOUNTAIN: 0xE506,
  TRAP: 0xE507,
  TRAP_ACTIVE: 0xE508,
  BARREL: 0xE509,
  CRATE: 0xE50A,

  // Items
  ITEM_POTION: 0xE600,
  ITEM_SCROLL: 0xE601,
  ITEM_GOLD: 0xE602,
  ITEM_KEY: 0xE603,
  ITEM_WEAPON: 0xE604,
  ITEM_ARMOR: 0xE605,
  ITEM_FOOD: 0xE606,
  ITEM_TORCH: 0xE607,

  // Entities
  PLAYER: 0xE700,
  PLAYER_ATTACK: 0xE701,
  PLAYER_HIT: 0xE702,
  ENEMY_RAT: 0xE710,
  ENEMY_GOBLIN: 0xE711,
  ENEMY_SKELETON: 0xE712,
  ENEMY_ORC: 0xE713,
  ENEMY_TROLL: 0xE714,
  NPC_MERCHANT: 0xE720,
  NPC_SAGE: 0xE721,
  NPC_GUARD: 0xE722,

  // Effects
  EFFECT_HIT: 0xE800,
  EFFECT_MISS: 0xE801,
  EFFECT_MAGIC: 0xE802,
  EFFECT_FIRE: 0xE803,
  EFFECT_ICE: 0xE804,
  EFFECT_POISON: 0xE805,
  EFFECT_LIGHT: 0xE806,

  // UI
  UI_CURSOR: 0xE900,
  UI_HEART_FULL: 0xE901,
  UI_HEART_HALF: 0xE902,
  UI_HEART_EMPTY: 0xE903,
  UI_MANA_FULL: 0xE904,
  UI_MANA_EMPTY: 0xE905,
} as const;

// Fallback ASCII characters for when font isn't loaded
export const ASCII_FALLBACKS: Record<number, string> = {
  [GLYPHS.VOID]: ' ',
  [GLYPHS.AIR]: ' ',
  [GLYPHS.FLOOR_STONE]: '.',
  [GLYPHS.FLOOR_CRACKED]: ',',
  [GLYPHS.FLOOR_DIRT]: '░',
  [GLYPHS.FLOOR_GRASS]: '"',
  [GLYPHS.FLOOR_WOOD]: '=',
  [GLYPHS.WALL_STONE]: '#',
  [GLYPHS.WALL_BRICK]: '▓',
  [GLYPHS.WALL_DUNGEON]: '█',
  [GLYPHS.DOOR_WOOD_CLOSED]: '+',
  [GLYPHS.DOOR_WOOD_OPEN]: '/',
  [GLYPHS.WATER]: '~',
  [GLYPHS.WATER_DEEP]: '≈',
  [GLYPHS.LAVA]: '▓',
  [GLYPHS.STAIRS_DOWN]: '>',
  [GLYPHS.STAIRS_UP]: '<',
  [GLYPHS.CHEST_CLOSED]: '■',
  [GLYPHS.CHEST_OPEN]: '□',
  [GLYPHS.ALTAR]: '╬',
  [GLYPHS.TRAP]: '^',
  [GLYPHS.ITEM_POTION]: '!',
  [GLYPHS.ITEM_GOLD]: '$',
  [GLYPHS.ITEM_KEY]: 'k',
  [GLYPHS.PLAYER]: '@',
  [GLYPHS.ENEMY_RAT]: 'r',
  [GLYPHS.ENEMY_GOBLIN]: 'g',
  [GLYPHS.ENEMY_SKELETON]: 's',
  [GLYPHS.NPC_MERCHANT]: '☺',
};

/**
 * Convert a glyph codepoint to its Unicode character.
 */
export function glyphChar(codepoint: number): string {
  return String.fromCodePoint(codepoint);
}

/**
 * Get the character for a glyph, with ASCII fallback.
 */
export function getGlyph(codepoint: number, useFallback = false): string {
  if (useFallback && ASCII_FALLBACKS[codepoint]) {
    return ASCII_FALLBACKS[codepoint];
  }
  return String.fromCodePoint(codepoint);
}

/**
 * Parse a glyph codepoint string (e.g., "U+E100") to number.
 */
export function parseCodepoint(str: string): number {
  return parseInt(str.replace('U+', ''), 16);
}

/**
 * Check if a codepoint is in the tile glyph range.
 */
export function isTileGlyph(codepoint: number): boolean {
  return codepoint >= 0xE000 && codepoint <= 0xEBFF;
}

/**
 * Get the category for a glyph codepoint.
 */
export function getGlyphCategory(codepoint: number): string | null {
  for (const [category, [start, end]] of Object.entries(GLYPH_BANDS)) {
    if (codepoint >= start && codepoint <= end) {
      return category;
    }
  }
  return null;
}

/**
 * Map common ASCII dungeon characters to tile glyphs.
 */
export function asciiToGlyph(char: string): number | null {
  const map: Record<string, number> = {
    ' ': GLYPHS.VOID,
    '.': GLYPHS.FLOOR_STONE,
    ',': GLYPHS.FLOOR_CRACKED,
    '#': GLYPHS.WALL_STONE,
    '▓': GLYPHS.WALL_BRICK,
    '+': GLYPHS.DOOR_WOOD_CLOSED,
    '/': GLYPHS.DOOR_WOOD_OPEN,
    '~': GLYPHS.WATER,
    '≈': GLYPHS.WATER_DEEP,
    '>': GLYPHS.STAIRS_DOWN,
    '<': GLYPHS.STAIRS_UP,
    '@': GLYPHS.PLAYER,
    '$': GLYPHS.ITEM_GOLD,
    '!': GLYPHS.ITEM_POTION,
    '^': GLYPHS.TRAP,
    '■': GLYPHS.CHEST_CLOSED,
    '□': GLYPHS.CHEST_OPEN,
    '☺': GLYPHS.NPC_MERCHANT,
    '&': GLYPHS.ENEMY_GOBLIN,
  };
  return map[char] ?? null;
}

/**
 * Convert an ASCII map line to tile glyphs.
 */
export function convertLineToGlyphs(line: string): string {
  return Array.from(line)
    .map(char => {
      const glyph = asciiToGlyph(char);
      return glyph ? String.fromCodePoint(glyph) : char;
    })
    .join('');
}

/**
 * Check if the TileCrawler font is loaded and available.
 */
export async function isFontLoaded(): Promise<boolean> {
  if (typeof document === 'undefined') return false;

  try {
    await document.fonts.load('16px TileCrawler');
    return document.fonts.check('16px TileCrawler');
  } catch {
    return false;
  }
}
