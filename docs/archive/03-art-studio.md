# Art Studio Design Document

## Overview

The Art Studio is an integrated toolset for creating, editing, and managing custom glyph tilesets for Tile-Crawler. It provides artists and designers with the ability to craft unique visual styles without requiring external font editing software.

## Purpose

- Enable in-game tileset creation and customization
- Provide pixel-art style glyph editing
- Support importing/exporting font files
- Preview tilesets in real-time game context
- Manage multiple tileset themes

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Art Studio                                │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Glyph Editor  │  │   Tileset       │  │   Preview       │ │
│  │   (Pixel Art)   │  │   Manager       │  │   Window        │ │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘ │
│           │                    │                    │           │
│           ▼                    ▼                    ▼           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   Asset Pipeline                          │  │
│  │  (Import/Export, Format Conversion, Optimization)        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Art Studio Controls

### Input System

The Art Studio uses **Xbox controller** and **keyboard** controls exclusively. Mouse input is **only available for button mapping** in the settings - not for drawing or editing.

#### Controller Navigation

| Input | Action |
|-------|--------|
| **Left Stick** | Move cursor on canvas |
| **D-Pad** | Precise single-pixel cursor movement |
| **A Button** | Draw/Place pixel |
| **B Button** | Erase pixel |
| **X Button** | Pick color from canvas |
| **Y Button** | Open color palette |
| **LB** | Previous tool |
| **RB** | Next tool |
| **LT** | Decrease brush size |
| **RT** | Increase brush size |
| **Left Stick Click** | Toggle grid overlay |
| **Right Stick Click** | Center canvas view |
| **Start** | Open menu |
| **Select** | Quick save |

#### Keyboard Controls

| Key | Action |
|-----|--------|
| **Arrow Keys** | Move cursor |
| **Space** | Draw/Place pixel |
| **Backspace/Delete** | Erase pixel |
| **P** | Pick color |
| **C** | Open color palette |
| **1-9** | Quick tool select |
| **[** / **]** | Decrease/Increase brush |
| **G** | Toggle grid |
| **Ctrl+S** | Save |
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Ctrl+C** | Copy selection |
| **Ctrl+V** | Paste |
| **Tab** | Cycle between panels |

### Cursor-Based Drawing

Since mouse input is disabled, the Art Studio uses a cursor-based drawing system:

```
┌─────────────────────────────────────────┐
│          Glyph Editor Canvas            │
│  ┌───┬───┬───┬───┬───┬───┬───┬───┐    │
│  │   │   │   │   │   │   │   │   │    │
│  ├───┼───┼───┼───┼───┼───┼───┼───┤    │
│  │   │   │ ▓ │ ▓ │ ▓ │   │   │   │    │
│  ├───┼───┼───┼───┼───┼───┼───┼───┤    │
│  │   │ ▓ │[█]│   │   │ ▓ │   │   │ ◄── Cursor position
│  ├───┼───┼───┼───┼───┼───┼───┼───┤    │
│  │   │ ▓ │   │   │   │ ▓ │   │   │    │
│  ├───┼───┼───┼───┼───┼───┼───┼───┤    │
│  │   │   │ ▓ │ ▓ │ ▓ │   │   │   │    │
│  ├───┼───┼───┼───┼───┼───┼───┼───┤    │
│  │   │   │   │   │   │   │   │   │    │
│  └───┴───┴───┴───┴───┴───┴───┴───┘    │
│                                         │
│  [A] Draw  [B] Erase  [Y] Colors       │
└─────────────────────────────────────────┘
```

## Features

### 1. Glyph Editor

The pixel-art editor for individual glyphs:

#### Canvas Features
- **Grid Sizes:** 8x8, 16x16, 32x32, 64x64 pixels
- **Zoom Levels:** 1x, 2x, 4x, 8x, 16x
- **Layers:** Support for multi-layer glyph design
- **Onion Skinning:** View adjacent glyphs for consistency

#### Drawing Tools (Cursor-Based)
- **Pencil:** Single pixel placement
- **Line:** Draw straight lines between two points
- **Rectangle:** Draw filled or outline rectangles
- **Ellipse:** Draw filled or outline circles/ellipses
- **Fill:** Flood fill enclosed areas
- **Select:** Rectangle selection for copy/paste
- **Mirror:** Horizontal/vertical symmetry drawing

#### Tool Selection Wheel

Accessible via controller (hold RB) or keyboard (hold Shift):

```
           [Pencil]
              │
    [Fill]────┼────[Line]
              │
         [Rectangle]
              │
   [Ellipse]──┼──[Select]
              │
          [Mirror]
```

### 2. Color System

#### Palette Management
- **16-Color Palettes:** Classic limited palette style
- **32-Color Extended:** More flexibility
- **Custom Palettes:** Create and save custom palettes
- **Color Picker:** HSV/RGB input with controller navigation

#### Color Picker Navigation (Controller)

```
┌─────────────────────────────────────┐
│         Color Picker                │
│  ┌─────────────────────────────┐   │
│  │                             │   │
│  │     [Saturation/Value]      │   │ ◄── Left Stick: move picker
│  │        2D Field             │   │
│  │            ◉ ← cursor       │   │
│  │                             │   │
│  └─────────────────────────────┘   │
│                                     │
│  Hue: ═══════●══════════           │ ◄── D-Pad Left/Right
│                                     │
│  R: 128  G: 64   B: 192            │
│                                     │
│  [A] Select   [B] Cancel           │
└─────────────────────────────────────┘
```

### 3. Tileset Manager

#### Tileset Organization
- **Character Mapping:** Assign glyphs to characters
- **Categories:** Organize by type (terrain, entities, items)
- **Variants:** Multiple versions of same tile type
- **Metadata:** Name, description, tags per glyph

#### Navigation Interface

```
┌─────────────────────────────────────────────────────────┐
│                   Tileset Manager                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ▓  ░  @  $  ☺  ≈  ▲  ♣  ♠  ◊  ■  □  ●  ○    │   │
│  │  †  ☼  ♦  ♥  ★  ⌂  G  O  D  S  Z  R  B  W    │   │
│  │ [M] K  ═  ║  ╔  ╗  ╚  ╝  ─  │  ┌  ┐  └  ┘    │   │ ◄── Cursor
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Selected: M (Merchant)                                 │
│  Category: Entities > NPCs > Friendly                   │
│                                                         │
│  [A] Edit  [X] Duplicate  [Y] Properties  [B] Back     │
└─────────────────────────────────────────────────────────┘
```

### 4. Preview System

#### Live Preview
- Real-time preview of glyphs in game context
- Test different zoom levels
- Preview animations if applicable
- Side-by-side comparison with other tilesets

#### Preview Controls

| Input | Action |
|-------|--------|
| **Left Stick** | Pan preview area |
| **Right Stick** | Zoom in/out |
| **A Button** | Place test tile |
| **B Button** | Clear test tile |
| **LB/RB** | Switch preview scenes |
| **Y Button** | Toggle comparison mode |

## Import/Export

### Supported Formats

#### Import
- **TTF/OTF:** Standard font files
- **PNG/BMP:** Sprite sheets (auto-slice)
- **JSON:** Tileset metadata
- **TCSET:** Tile-Crawler native format

#### Export
- **TTF:** TrueType font
- **OTF:** OpenType font
- **PNG:** Sprite sheet
- **TCSET:** Native format with full metadata

### Font Generation Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Glyph      │    │   SVG        │    │   TTF/OTF    │
│   Pixels     │───▶│   Vectors    │───▶│   Font       │
│   (Bitmap)   │    │   (Auto)     │    │   (Final)    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                                      │
        ▼                                      ▼
┌──────────────┐                      ┌──────────────┐
│   PNG        │                      │   Metadata   │
│   Spritesheet│                      │   JSON       │
└──────────────┘                      └──────────────┘
```

## User Interface Layout

### Main Studio Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  [Tool Panel]  │           Canvas Area           │  [Preview]   │
│                │                                 │              │
│  ┌──────────┐  │  ┌─────────────────────────┐   │  ┌────────┐  │
│  │ Pencil   │  │  │                         │   │  │ Live   │  │
│  │ Line     │  │  │                         │   │  │ Preview│  │
│  │ Rect     │  │  │      Editor Canvas      │   │  │        │  │
│  │ Ellipse  │  │  │                         │   │  │ ▓░▓░▓  │  │
│  │ Fill     │  │  │                         │   │  │ ░@░$░  │  │
│  │ Select   │  │  │                         │   │  │ ▓░☺░▓  │  │
│  └──────────┘  │  └─────────────────────────┘   │  └────────┘  │
│                │                                 │              │
│  ┌──────────┐  │  ┌─────────────────────────┐   │  ┌────────┐  │
│  │ Color    │  │  │     Layer Panel         │   │  │ Glyph  │  │
│  │ Palette  │  │  │  [Base] [Detail] [FX]   │   │  │ Info   │  │
│  │ ■■■■■■   │  │  └─────────────────────────┘   │  │        │  │
│  │ ■■■■■■   │  │                                 │  │ Char:@ │  │
│  └──────────┘  │                                 │  │ Size:16│  │
│                │                                 │  └────────┘  │
├────────────────┴─────────────────────────────────┴──────────────┤
│  [A] Draw   [B] Erase   [X] Pick Color   [Y] Tools   [Start] Menu│
└─────────────────────────────────────────────────────────────────┘
```

### Panel Navigation

Navigate between panels using **Tab** (keyboard) or **Select** (controller):

1. Tool Panel
2. Canvas (main editing area)
3. Preview Panel
4. Color Palette
5. Layer Panel
6. Glyph Info

## Workflow Examples

### Creating a New Glyph

1. Open Tileset Manager (Y button from main menu)
2. Navigate to empty slot with D-pad/Left Stick
3. Press A to create new glyph
4. Select canvas size (16x16 recommended)
5. Use cursor to draw pixel by pixel
6. Press Start to save and assign character

### Importing an Existing Font

1. Open Art Studio menu (Start)
2. Navigate to Import option
3. Select font file from file browser (controller navigation)
4. Choose glyphs to import
5. Confirm import settings
6. Glyphs populate tileset slots

### Quick Edit Existing Glyph

1. In game, press Select + Y for quick edit
2. Cursor appears on player tile's glyph
3. Make quick adjustments
4. Press B to return to game with changes

## Data Structures

### Glyph Data

```typescript
interface GlyphData {
  character: string;        // Unicode character mapping
  pixels: number[][];       // 2D pixel array (0-255 per channel)
  width: number;
  height: number;
  layers: GlyphLayer[];
  metadata: GlyphMetadata;
}

interface GlyphLayer {
  name: string;
  visible: boolean;
  opacity: number;
  pixels: number[][];
}

interface GlyphMetadata {
  name: string;
  category: string;
  tags: string[];
  author: string;
  created: Date;
  modified: Date;
}
```

### Tileset Data

```typescript
interface TilesetData {
  id: string;
  name: string;
  version: string;
  glyphs: Map<string, GlyphData>;
  palette: ColorPalette;
  metadata: TilesetMetadata;
}

interface ColorPalette {
  name: string;
  colors: string[];  // Hex colors
}
```

## Performance Considerations

- Canvas rendering optimized for 60 FPS editing
- Lazy loading of glyph data
- Incremental saves to prevent data loss
- Undo/redo stack with configurable depth
- Background font generation (non-blocking)

## Accessibility

- Full controller support for all features
- Keyboard shortcuts for power users
- High contrast UI option
- Zoom support for detailed work
- Audio feedback for drawing actions
- Screen reader announcements for major actions

## Future Enhancements

1. **Animation Editor:** Create animated tiles
2. **Collaborative Editing:** Share tilesets online
3. **AI-Assisted Design:** Generate glyph suggestions
4. **Template Library:** Pre-made glyph templates
5. **Community Gallery:** Browse and download tilesets
