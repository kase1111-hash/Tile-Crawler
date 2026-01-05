# Glyph Rendering System Design Document

## Overview

The Glyph Rendering System is the visual core of Tile-Crawler, responsible for transforming text-based tilemap data into visually appealing game graphics using custom font tilesets. This system bridges traditional ASCII roguelike aesthetics with modern visual presentation.

## Core Concepts

### What is Glyph Rendering?

Instead of using traditional sprite-based graphics, Tile-Crawler renders its world using a custom font where each character (glyph) represents a specific visual tile. This approach offers:

- **Lightweight assets:** A single font file contains all tile graphics
- **Perfect grid alignment:** Monospace fonts guarantee consistent spacing
- **Text-based compatibility:** LLM can output tilemaps as plain text
- **Scalable graphics:** Vector fonts scale without quality loss
- **Easy theming:** Swap fonts to completely change visual style

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Glyph Rendering Pipeline                      │
│                                                                  │
│  ┌────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │   Tilemap      │    │   Glyph         │    │   Rendered   │ │
│  │   Data         │───▶│   Mapper        │───▶│   Output     │ │
│  │   (JSON/Text)  │    │                 │    │   (Canvas)   │ │
│  └────────────────┘    └─────────────────┘    └──────────────┘ │
│                              │                                   │
│                              ▼                                   │
│                     ┌─────────────────┐                         │
│                     │   Font Asset    │                         │
│                     │   (TTF/OTF)     │                         │
│                     └─────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

## Character Mapping

### Standard Glyph Set

| Character | Tile Type | Description |
|-----------|-----------|-------------|
| `▓` | Wall | Solid impassable wall |
| `░` | Floor | Walkable floor tile |
| `@` | Player | Player character |
| `$` | Item | Collectible item |
| `☺` | NPC | Non-player character |
| `≈` | Water | Water/liquid tile |
| `▲` | Mountain | Elevated terrain |
| `♣` | Tree | Vegetation |
| `♠` | Bush | Dense vegetation |
| `◊` | Crystal | Magical item/structure |
| `■` | Solid Block | Generic solid |
| `□` | Empty Block | Generic empty |
| `●` | Filled Circle | Various uses |
| `○` | Empty Circle | Various uses |
| `†` | Grave | Graveyard element |
| `☼` | Light Source | Torch/lamp |
| `♦` | Gem | Valuable item |
| `♥` | Health | Health pickup |
| `★` | Star | Special marker |
| `⌂` | House/Door | Building entrance |

### Extended Box Drawing

For dungeon walls and structures:

```
╔═══╗    ┌───┐
║   ║    │   │
╠═══╣    ├───┤
║   ║    │   │
╚═══╝    └───┘
```

### Entity Glyphs

| Character | Entity Type |
|-----------|-------------|
| `@` | Player |
| `G` | Goblin |
| `O` | Orc |
| `D` | Dragon |
| `S` | Skeleton |
| `Z` | Zombie |
| `R` | Rat |
| `B` | Bat |
| `W` | Wolf |
| `M` | Merchant |
| `K` | King/Boss |

## Rendering Implementation

### Font Loading

```typescript
// GlyphFont.ts
interface GlyphFontConfig {
  fontFamily: string;
  fontSize: number;
  lineHeight: number;
  letterSpacing: number;
}

class GlyphFont {
  private config: GlyphFontConfig;
  private loaded: boolean = false;

  async load(fontUrl: string): Promise<void> {
    const font = new FontFace(this.config.fontFamily, `url(${fontUrl})`);
    await font.load();
    document.fonts.add(font);
    this.loaded = true;
  }
}
```

### CSS Configuration

```css
@font-face {
  font-family: 'DungeonTiles';
  src: url('./fonts/DungeonTiles.ttf') format('truetype');
  font-display: block; /* Prevent FOUT */
}

.tilemap-container {
  font-family: 'DungeonTiles', monospace;
  font-size: 32px;
  line-height: 1;
  letter-spacing: 0;
  white-space: pre;
  user-select: none;
}
```

### React Component

```tsx
// TilemapRenderer.tsx
interface TilemapProps {
  map: string[];
  tileSize: number;
  playerPosition: { x: number; y: number };
}

const TilemapRenderer: React.FC<TilemapProps> = ({
  map,
  tileSize,
  playerPosition
}) => {
  return (
    <pre
      className="tilemap-container"
      style={{ fontSize: `${tileSize}px` }}
      aria-label="Game map"
      role="img"
    >
      {map.join('\n')}
    </pre>
  );
};
```

## Layer System

The rendering system supports multiple layers for complex scenes:

```
┌─────────────────────────────────┐
│         UI Layer (Top)          │  - HUD, menus, tooltips
├─────────────────────────────────┤
│        Effect Layer             │  - Particles, animations
├─────────────────────────────────┤
│        Entity Layer             │  - Player, NPCs, items
├─────────────────────────────────┤
│        Object Layer             │  - Furniture, chests
├─────────────────────────────────┤
│        Terrain Layer (Bottom)   │  - Floors, walls, water
└─────────────────────────────────┘
```

### Layer Composition

```typescript
interface RenderLayer {
  id: string;
  zIndex: number;
  visible: boolean;
  opacity: number;
  data: string[][];
}

class LayerCompositor {
  private layers: Map<string, RenderLayer> = new Map();

  compose(): string[][] {
    const sortedLayers = [...this.layers.values()]
      .filter(l => l.visible)
      .sort((a, b) => a.zIndex - b.zIndex);

    // Compose layers from bottom to top
    return this.mergeLayers(sortedLayers);
  }
}
```

## Color Support

### COLR/CPAL Fonts

Modern font formats support multi-colored glyphs:

```typescript
interface ColoredGlyph {
  baseChar: string;
  foreground: string;
  background: string;
  effects?: GlyphEffect[];
}

type GlyphEffect = 'glow' | 'pulse' | 'shimmer';
```

### CSS-Based Coloring

For simpler color schemes using CSS:

```css
.tile-wall { color: #4a4a4a; }
.tile-floor { color: #8b7355; }
.tile-water { color: #4169e1; }
.tile-player { color: #ffd700; }
.tile-enemy { color: #dc143c; }
.tile-item { color: #32cd32; }
.tile-npc { color: #9370db; }
```

## Animation System

### Supported Animations

1. **Tile Transitions:** Smooth movement between tiles
2. **Pulse Effects:** Highlighting interactive elements
3. **Damage Flash:** Visual feedback for combat
4. **Particle Effects:** Environmental effects (CSS-based)

### Animation Implementation

```typescript
interface TileAnimation {
  type: 'move' | 'pulse' | 'flash' | 'fade';
  duration: number;
  easing: string;
  frames?: string[]; // For character animation
}

class AnimationController {
  async playMoveAnimation(
    entity: string,
    from: Position,
    to: Position,
    duration: number
  ): Promise<void> {
    // CSS transition-based smooth movement
  }

  async playDamageFlash(
    position: Position,
    color: string
  ): Promise<void> {
    // Brief color flash effect
  }
}
```

## Input Feedback Rendering

### Controller/Keyboard Visual Indicators

The rendering system provides visual feedback for input actions:

```typescript
interface InputFeedback {
  // Show directional indicator when moving
  showMovementIndicator(direction: Direction): void;

  // Highlight interactable tiles when near
  highlightInteractables(positions: Position[]): void;

  // Show action preview (attack range, etc.)
  showActionPreview(action: GameAction): void;

  // Display button prompts for current context
  showButtonPrompts(prompts: ButtonPrompt[]): void;
}

interface ButtonPrompt {
  button: ControllerButton | KeyboardKey;
  action: string;
  position: 'bottom-left' | 'bottom-right' | 'contextual';
}
```

### Contextual Button Prompts

The UI displays relevant button prompts based on context:

```
┌─────────────────────────────────────────┐
│                                         │
│            [Game View]                  │
│                                         │
│     ☺ ← NPC nearby                      │
│     @                                   │
│                                         │
├─────────────────────────────────────────┤
│  [A] Talk   [X] Attack   [Y] Inventory  │  ← Controller prompts
│  [Space]    [F]          [I]            │  ← Keyboard alternatives
└─────────────────────────────────────────┘
```

## Performance Optimization

### Rendering Strategies

1. **Dirty Rectangle Tracking:** Only re-render changed tiles
2. **Viewport Culling:** Only render visible portion of map
3. **Font Caching:** Pre-render common glyphs to canvas
4. **RequestAnimationFrame:** Sync with display refresh

### Viewport Management

```typescript
interface Viewport {
  x: number;
  y: number;
  width: number;  // In tiles
  height: number; // In tiles

  centerOn(position: Position): void;
  isVisible(position: Position): boolean;
  getVisibleTiles(): Tile[][];
}
```

## Accessibility Considerations

### Screen Reader Support

```tsx
<div
  role="application"
  aria-label="Tile-Crawler game board"
>
  <div aria-live="polite" className="sr-only">
    {/* Announce game events */}
    {lastEvent}
  </div>
  <pre aria-hidden="true">
    {/* Visual tilemap - hidden from screen readers */}
    {map}
  </pre>
</div>
```

### High Contrast Mode

Support for high contrast themes for visibility:

```css
@media (prefers-contrast: high) {
  .tilemap-container {
    --wall-color: #ffffff;
    --floor-color: #000000;
    --player-color: #ffff00;
    --enemy-color: #ff0000;
  }
}
```

## Custom Tileset Creation

### Requirements

1. **Monospace Design:** All glyphs must have equal width
2. **Consistent Height:** Line height must be uniform
3. **Clear Silhouettes:** Tiles distinguishable at small sizes
4. **Character Coverage:** Map all standard ASCII + extended set

### Recommended Tools

- **FontForge:** Free, open-source font editor
- **Glyphs:** Professional Mac font editor
- **Birdfont:** Cross-platform font creator

### Testing Checklist

- [ ] All standard glyphs render correctly
- [ ] Grid alignment is pixel-perfect
- [ ] Colors display properly (if using COLR)
- [ ] Font scales well at different sizes
- [ ] Performance is acceptable (60 FPS)

## Future Enhancements

1. **Shader Effects:** WebGL-based post-processing
2. **Dynamic Lighting:** Tile-based light/shadow system
3. **Weather Effects:** Rain, snow, fog overlays
4. **Particle System:** More complex visual effects
5. **Tileset Hot-Swapping:** Change themes in-game
