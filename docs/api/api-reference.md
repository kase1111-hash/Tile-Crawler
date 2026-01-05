# API Reference

## Overview

The Tile-Crawler API provides RESTful endpoints for game state management, player actions, and LLM-powered content generation. The API is built with FastAPI and communicates with the React frontend.

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://api.tilecrawler.com/api/v1
```

## Authentication

### Session-Based Auth

```http
POST /auth/session
Content-Type: application/json

{
  "player_name": "Adventurer"
}
```

**Response:**
```json
{
  "session_id": "sess_abc123xyz",
  "expires_at": "2026-01-06T12:00:00Z"
}
```

All subsequent requests require the session header:
```http
X-Session-ID: sess_abc123xyz
```

## Game State Endpoints

### Initialize Game

Start a new game session.

```http
POST /game/init
X-Session-ID: {session_id}
Content-Type: application/json

{
  "player_name": "Hero",
  "seed": "optional_seed_string",
  "difficulty": "normal"
}
```

**Response:**
```json
{
  "success": true,
  "game_id": "game_xyz789",
  "initial_state": {
    "map": [
      "▓▓▓▓▓▓▓▓▓▓",
      "▓░░░░░░░░▓",
      "▓░░░░░░░░▓",
      "▓░░░░@░░░▓",
      "▓░░░░░░░░▓",
      "▓░░░░░░░░▓",
      "▓▓▓▓░░▓▓▓▓"
    ],
    "description": "You awaken in a dimly lit chamber...",
    "player": {
      "position": {"x": 5, "y": 3},
      "hp": 50,
      "max_hp": 50,
      "mp": 20,
      "max_mp": 20,
      "level": 1
    },
    "exits": ["south"]
  }
}
```

### Get Current State

Retrieve the current game state.

```http
GET /game/state
X-Session-ID: {session_id}
```

**Response:**
```json
{
  "map": ["..."],
  "description": "...",
  "player": {...},
  "entities": [...],
  "inventory": [...],
  "active_quests": [...],
  "turn": 42
}
```

## Action Endpoints

### Movement

Move the player in a direction.

```http
POST /action/move
X-Session-ID: {session_id}
Content-Type: application/json

{
  "direction": "north"
}
```

**Valid Directions:**
- `north`, `south`, `east`, `west` (cardinal)
- `northeast`, `northwest`, `southeast`, `southwest` (diagonal)

**Input Mapping:**
| Controller Input | Keyboard Input | Direction |
|-----------------|----------------|-----------|
| D-Pad Up / Left Stick Up | W / Up Arrow | north |
| D-Pad Down / Left Stick Down | S / Down Arrow | south |
| D-Pad Left / Left Stick Left | A / Left Arrow | west |
| D-Pad Right / Left Stick Right | D / Right Arrow | east |
| Left Stick Diagonal | Q, E, Z, C | diagonals |

**Response:**
```json
{
  "success": true,
  "new_state": {
    "map": ["..."],
    "description": "You step into a narrow corridor...",
    "player": {
      "position": {"x": 5, "y": 2}
    },
    "events": [
      {
        "type": "room_enter",
        "message": "You have entered a new area."
      }
    ]
  }
}
```

### Interact

Interact with the environment or entities.

```http
POST /action/interact
X-Session-ID: {session_id}
Content-Type: application/json

{
  "target": "npc_merchant_01"
}
```

**Input Mapping:**
| Controller | Keyboard | Notes |
|------------|----------|-------|
| A Button | Space / Enter | Primary interact |
| X Button | E | Quick interact |

**Response:**
```json
{
  "success": true,
  "interaction_type": "dialogue",
  "dialogue": {
    "npc_name": "Marcus",
    "text": "Welcome, traveler! What can I do for you?",
    "options": [
      {"id": 1, "text": "Show me your wares."},
      {"id": 2, "text": "Any news from the road?"},
      {"id": 3, "text": "Farewell."}
    ]
  }
}
```

### Attack

Initiate combat or attack a target.

```http
POST /action/attack
X-Session-ID: {session_id}
Content-Type: application/json

{
  "target": "enemy_goblin_03",
  "attack_type": "basic"
}
```

**Attack Types:**
- `basic` - Standard attack
- `heavy` - Power attack (uses stamina)
- `skill` - Use equipped skill

**Input Mapping:**
| Controller | Keyboard | Attack Type |
|------------|----------|-------------|
| X Button | F | Basic attack |
| RT + X | Shift + F | Heavy attack |
| Y + Select | 1-4 | Skill attack |

**Response:**
```json
{
  "success": true,
  "combat_result": {
    "attacker": "player",
    "target": "Goblin",
    "damage": 12,
    "critical": false,
    "target_hp": 8,
    "target_max_hp": 20,
    "narrative": "Your sword strikes true, slashing across the goblin's chest!"
  }
}
```

### Use Item

Use an item from inventory.

```http
POST /action/use-item
X-Session-ID: {session_id}
Content-Type: application/json

{
  "item_id": "item_healing_potion",
  "target": "self"
}
```

**Response:**
```json
{
  "success": true,
  "effect": {
    "type": "heal",
    "amount": 50,
    "new_hp": 50,
    "narrative": "The warm potion restores your vitality."
  },
  "inventory_update": {
    "item_id": "item_healing_potion",
    "new_quantity": 4
  }
}
```

### Use Skill

Activate a skill ability.

```http
POST /action/use-skill
X-Session-ID: {session_id}
Content-Type: application/json

{
  "skill_id": "skill_power_strike",
  "target": "enemy_orc_01"
}
```

**Response:**
```json
{
  "success": true,
  "skill_result": {
    "skill_name": "Power Strike",
    "mp_cost": 10,
    "current_mp": 15,
    "effects": [
      {
        "type": "damage",
        "target": "Orc Warrior",
        "amount": 25,
        "critical": true
      }
    ],
    "narrative": "You channel your strength into a devastating blow!"
  }
}
```

## Dialogue Endpoints

### Continue Dialogue

Select a dialogue option.

```http
POST /dialogue/respond
X-Session-ID: {session_id}
Content-Type: application/json

{
  "npc_id": "npc_merchant_01",
  "option_id": 1
}
```

**Input Mapping:**
| Controller | Keyboard | Action |
|------------|----------|--------|
| D-Pad / Left Stick | Arrow Keys | Navigate options |
| A Button | Space / Enter | Select option |
| B Button | Escape | End dialogue |
| 1-9 Keys | 1-9 | Quick select option |

**Response:**
```json
{
  "success": true,
  "dialogue": {
    "npc_name": "Marcus",
    "text": "Ah, a discerning customer! Here's what I have today...",
    "action": "open_shop",
    "shop_inventory": [
      {
        "id": "item_healing_potion",
        "name": "Healing Potion",
        "price": 50,
        "quantity": 10
      }
    ]
  }
}
```

### End Dialogue

```http
POST /dialogue/end
X-Session-ID: {session_id}
Content-Type: application/json

{
  "npc_id": "npc_merchant_01"
}
```

## Inventory Endpoints

### Get Inventory

```http
GET /inventory
X-Session-ID: {session_id}
```

**Response:**
```json
{
  "items": [
    {
      "id": "item_healing_potion",
      "name": "Healing Potion",
      "quantity": 5,
      "type": "consumable",
      "description": "Restores 50 HP"
    },
    {
      "id": "item_iron_sword",
      "name": "Iron Sword",
      "quantity": 1,
      "type": "weapon",
      "equipped": true,
      "stats": {
        "attack": 10
      }
    }
  ],
  "gold": 150,
  "capacity": {
    "current": 15,
    "max": 50
  }
}
```

### Equip Item

```http
POST /inventory/equip
X-Session-ID: {session_id}
Content-Type: application/json

{
  "item_id": "item_iron_sword",
  "slot": "weapon"
}
```

### Drop Item

```http
POST /inventory/drop
X-Session-ID: {session_id}
Content-Type: application/json

{
  "item_id": "item_torch",
  "quantity": 1
}
```

## Shop Endpoints

### Buy Item

```http
POST /shop/buy
X-Session-ID: {session_id}
Content-Type: application/json

{
  "shop_id": "shop_merchant_01",
  "item_id": "item_healing_potion",
  "quantity": 3
}
```

**Response:**
```json
{
  "success": true,
  "transaction": {
    "item": "Healing Potion",
    "quantity": 3,
    "total_cost": 150,
    "new_gold": 1100
  }
}
```

### Sell Item

```http
POST /shop/sell
X-Session-ID: {session_id}
Content-Type: application/json

{
  "shop_id": "shop_merchant_01",
  "item_id": "item_goblin_ear",
  "quantity": 5
}
```

## Quest Endpoints

### Get Active Quests

```http
GET /quests/active
X-Session-ID: {session_id}
```

**Response:**
```json
{
  "quests": [
    {
      "id": "quest_goblin_menace",
      "title": "The Goblin Menace",
      "type": "main",
      "description": "Clear the goblin camp threatening the village.",
      "objectives": [
        {
          "id": "obj_1",
          "description": "Defeat 10 goblins",
          "current": 7,
          "required": 10,
          "completed": false
        },
        {
          "id": "obj_2",
          "description": "Defeat the Goblin Chief",
          "current": 0,
          "required": 1,
          "completed": false
        }
      ],
      "rewards": {
        "gold": 500,
        "experience": 200,
        "items": ["item_iron_sword"]
      }
    }
  ]
}
```

### Accept Quest

```http
POST /quests/accept
X-Session-ID: {session_id}
Content-Type: application/json

{
  "quest_id": "quest_lost_heirloom"
}
```

### Complete Quest

```http
POST /quests/complete
X-Session-ID: {session_id}
Content-Type: application/json

{
  "quest_id": "quest_goblin_menace"
}
```

## Save/Load Endpoints

### Save Game

```http
POST /save
X-Session-ID: {session_id}
Content-Type: application/json

{
  "slot": 1,
  "name": "Before the boss"
}
```

**Response:**
```json
{
  "success": true,
  "save_info": {
    "slot": 1,
    "name": "Before the boss",
    "timestamp": "2026-01-05T15:30:00Z",
    "play_time": 7200
  }
}
```

### Load Game

```http
POST /load
X-Session-ID: {session_id}
Content-Type: application/json

{
  "slot": 1
}
```

### List Saves

```http
GET /saves
X-Session-ID: {session_id}
```

**Response:**
```json
{
  "saves": [
    {
      "slot": 1,
      "name": "Before the boss",
      "level": 8,
      "location": "Dragon's Lair",
      "play_time": 7200,
      "timestamp": "2026-01-05T15:30:00Z"
    },
    {
      "slot": 2,
      "name": "Auto-save",
      "level": 8,
      "location": "Mountain Pass",
      "play_time": 6900,
      "timestamp": "2026-01-05T15:15:00Z"
    }
  ]
}
```

### Delete Save

```http
DELETE /saves/{slot}
X-Session-ID: {session_id}
```

## Settings Endpoints

### Get Settings

```http
GET /settings
X-Session-ID: {session_id}
```

**Response:**
```json
{
  "audio": {
    "master_volume": 80,
    "music_volume": 70,
    "sfx_volume": 90
  },
  "display": {
    "font_size": "medium",
    "theme": "dark",
    "show_grid": false
  },
  "controls": {
    "controller_enabled": true,
    "keyboard_enabled": true,
    "controller_bindings": {
      "move_north": "dpad_up",
      "move_south": "dpad_down",
      "interact": "button_a",
      "attack": "button_x"
    },
    "keyboard_bindings": {
      "move_north": "w",
      "move_south": "s",
      "interact": "space",
      "attack": "f"
    }
  },
  "gameplay": {
    "auto_save": true,
    "auto_save_interval": 300,
    "difficulty": "normal"
  }
}
```

### Update Settings

```http
PATCH /settings
X-Session-ID: {session_id}
Content-Type: application/json

{
  "controls": {
    "keyboard_bindings": {
      "attack": "e"
    }
  }
}
```

## Error Responses

### Standard Error Format

```json
{
  "success": false,
  "error": {
    "code": "INVALID_ACTION",
    "message": "Cannot move in that direction - wall blocking.",
    "details": {
      "attempted_direction": "north",
      "blocking_tile": "wall"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_SESSION` | 401 | Session expired or invalid |
| `INVALID_ACTION` | 400 | Action not allowed in current state |
| `TARGET_NOT_FOUND` | 404 | Specified target doesn't exist |
| `INSUFFICIENT_RESOURCES` | 400 | Not enough gold/MP/items |
| `INVENTORY_FULL` | 400 | Cannot add more items |
| `SAVE_FAILED` | 500 | Save operation failed |
| `LOAD_FAILED` | 500 | Load operation failed |
| `LLM_ERROR` | 503 | LLM service unavailable |
| `RATE_LIMITED` | 429 | Too many requests |

## WebSocket Events

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?session_id=sess_abc123');
```

### Event Types

**Server → Client:**

```json
{
  "type": "state_update",
  "data": {
    "map": ["..."],
    "events": [...]
  }
}
```

```json
{
  "type": "combat_event",
  "data": {
    "attacker": "Goblin",
    "target": "player",
    "damage": 5
  }
}
```

```json
{
  "type": "notification",
  "data": {
    "title": "Quest Complete!",
    "message": "You have completed 'The Goblin Menace'"
  }
}
```

**Client → Server:**

```json
{
  "type": "action",
  "data": {
    "action": "move",
    "direction": "north"
  }
}
```

## Rate Limiting

- **Standard requests:** 60 per minute
- **LLM-powered requests:** 20 per minute
- **Save operations:** 10 per minute

Rate limit headers:
```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704470400
```

## Input Device Notes

The API accepts actions from both Xbox controller and keyboard inputs. The frontend handles input translation - the API receives normalized action commands regardless of input device.

**Supported Input Devices:**
- Xbox Controller (recommended)
- Keyboard

**Not Supported:**
- Mouse (except for button mapping in settings)
- Touch controls (future consideration)

The `controls` settings endpoint allows customization of both controller and keyboard bindings. Mouse bindings are not available as mouse input is disabled during gameplay.
