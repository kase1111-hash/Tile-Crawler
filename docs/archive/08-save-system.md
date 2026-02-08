# Save System Design Document

## Overview

The Save System provides persistent storage for game state, allowing players to save their progress and resume later. It handles player data, world state, narrative memory, and configuration settings across multiple save slots.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Save System                                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Save Manager                           │   │
│  │  (Orchestrates save/load operations)                    │   │
│  └───────────────────────────┬─────────────────────────────┘   │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         │                    │                    │             │
│         ▼                    ▼                    ▼             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │   Player      │  │   World       │  │  Settings     │       │
│  │   State       │  │   State       │  │  Config       │       │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘       │
│          │                  │                  │                │
│          ▼                  ▼                  ▼                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Storage Layer                           │   │
│  │  (JSON files, Local Storage, Cloud Sync)                │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Save Data Structure

### Complete Save File

```typescript
interface SaveFile {
  version: string;           // Save format version
  metadata: SaveMetadata;
  player: PlayerSaveData;
  world: WorldSaveData;
  narrative: NarrativeSaveData;
  quests: QuestSaveData;
  settings: GameSettings;
  checksum: string;          // Integrity verification
}

interface SaveMetadata {
  slot: number;
  name: string;
  createdAt: string;
  lastPlayedAt: string;
  playTime: number;          // Seconds
  playerLevel: number;
  location: string;
  thumbnail?: string;        // Base64 encoded screenshot
}
```

### Player State

```typescript
interface PlayerSaveData {
  name: string;
  class: string;
  level: number;
  experience: number;
  stats: {
    base: PrimaryStats;
    allocated: PrimaryStats;
  };
  currentHP: number;
  currentMP: number;
  position: Position;
  equipment: EquipmentSlots;
  inventory: InventoryItem[];
  skills: LearnedSkill[];
  skillPoints: number;
  statPoints: number;
  gold: number;
  statusEffects: StatusEffect[];
}

interface InventoryItem {
  id: string;
  itemId: string;
  quantity: number;
  durability?: number;
  enchantments?: string[];
}
```

### World State

```typescript
interface WorldSaveData {
  seed: string;
  currentZone: string;
  exploredRooms: Map<string, RoomSaveData>;
  globalFlags: Map<string, boolean>;
  entityStates: Map<string, EntityState>;
  timeElapsed: number;       // In-game time (turns)
}

interface RoomSaveData {
  id: string;
  coordinates: Position;
  visited: boolean;
  cleared: boolean;
  items: ItemDrop[];
  enemies: EnemyState[];
  npcs: NPCState[];
  changes: RoomChange[];     // Modified tiles, etc.
}
```

### Narrative State

```typescript
interface NarrativeSaveData {
  storyLog: StoryEvent[];
  activeThemes: string[];
  playerChoices: PlayerChoice[];
  npcRelationships: Map<string, number>;
  discoveredLore: string[];
  dialogueHistory: Map<string, DialogueEntry[]>;
}

interface StoryEvent {
  id: string;
  timestamp: number;
  type: string;
  summary: string;
  details: Record<string, any>;
}
```

## Save/Load Operations

### Save Process

```python
class SaveManager:
    def save_game(self, slot: int, name: str) -> SaveResult:
        """Save current game state to a slot"""

        # 1. Gather all state
        save_data = SaveFile(
            version=SAVE_VERSION,
            metadata=self._create_metadata(slot, name),
            player=self._serialize_player(),
            world=self._serialize_world(),
            narrative=self._serialize_narrative(),
            quests=self._serialize_quests(),
            settings=self._serialize_settings(),
            checksum=""  # Calculated after serialization
        )

        # 2. Serialize to JSON
        json_data = self._to_json(save_data)

        # 3. Calculate checksum
        save_data.checksum = self._calculate_checksum(json_data)
        json_data = self._to_json(save_data)

        # 4. Compress (optional)
        if COMPRESS_SAVES:
            json_data = self._compress(json_data)

        # 5. Write to storage
        self._write_to_storage(slot, json_data)

        return SaveResult(success=True, slot=slot)
```

### Load Process

```python
class SaveManager:
    def load_game(self, slot: int) -> LoadResult:
        """Load game state from a slot"""

        # 1. Read from storage
        json_data = self._read_from_storage(slot)

        if not json_data:
            return LoadResult(success=False, error="Save not found")

        # 2. Decompress (if needed)
        if self._is_compressed(json_data):
            json_data = self._decompress(json_data)

        # 3. Parse JSON
        save_data = self._from_json(json_data)

        # 4. Verify checksum
        if not self._verify_checksum(save_data):
            return LoadResult(success=False, error="Save corrupted")

        # 5. Version migration (if needed)
        if save_data.version != SAVE_VERSION:
            save_data = self._migrate_save(save_data)

        # 6. Restore state
        self._restore_player(save_data.player)
        self._restore_world(save_data.world)
        self._restore_narrative(save_data.narrative)
        self._restore_quests(save_data.quests)
        self._restore_settings(save_data.settings)

        return LoadResult(success=True, metadata=save_data.metadata)
```

## Save Slots Interface

### Save/Load Menu Controls

All save system interactions use **Xbox controller** and **keyboard** only:

#### Controller Controls

| Input | Action |
|-------|--------|
| **Left Stick/D-Pad** | Navigate save slots |
| **A Button** | Select slot / Confirm |
| **B Button** | Back / Cancel |
| **X Button** | Delete save (with confirmation) |
| **Y Button** | View save details |
| **LB** | Previous page of saves |
| **RB** | Next page of saves |
| **Start** | Quick save (in-game) |
| **Select** | Quick load (in-game) |

#### Keyboard Controls

| Key | Action |
|-----|--------|
| **Arrow Keys/WASD** | Navigate slots |
| **Space/Enter** | Select / Confirm |
| **Escape** | Back / Cancel |
| **Delete** | Delete save |
| **I** | View save details |
| **Page Up** | Previous page |
| **Page Down** | Next page |
| **F5** | Quick save |
| **F9** | Quick load |

### Save Menu UI

```
┌─────────────────────────────────────────────────────────────────┐
│                       SAVE GAME                                  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SLOT 1 - "Hero's Journey"                              │   │
│  │  Level 12 Warrior | Darkwood Forest                     │   │
│  │  Played: 5h 23m | Saved: Jan 5, 2026 3:45 PM           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ >SLOT 2 - "New Adventure"                               │   │ ← Selected
│  │  Level 5 Mage | Crystal Caves                           │   │
│  │  Played: 1h 10m | Saved: Jan 4, 2026 8:12 PM           │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  SLOT 3 - Empty                                         │   │
│  │                                                         │   │
│  │  [Create New Save]                                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Page 1/3                                                       │
│                                                                  │
│  [A] Save Here    [X] Delete    [Y] Details    [B] Cancel      │
└─────────────────────────────────────────────────────────────────┘
```

### Save Details View

```
┌─────────────────────────────────────────────────────────────────┐
│                    SAVE DETAILS                                  │
│                                                                  │
│  Slot 2: "New Adventure"                                        │
│                                                                  │
│  ┌──────────────────────┬──────────────────────────────────┐   │
│  │                      │  CHARACTER                       │   │
│  │    [Screenshot]      │  Name: Elara                     │   │
│  │                      │  Class: Mage                     │   │
│  │    Crystal Caves     │  Level: 5                        │   │
│  │                      │  HP: 45/45  MP: 60/60            │   │
│  │                      │                                  │   │
│  └──────────────────────┴──────────────────────────────────┘   │
│                                                                  │
│  STATISTICS                                                     │
│  ─────────────────────────────────────────────────────────     │
│  Play Time: 1 hour, 10 minutes                                 │
│  Enemies Defeated: 47                                          │
│  Rooms Explored: 23                                            │
│  Quests Completed: 3                                           │
│  Deaths: 2                                                     │
│                                                                  │
│  ACTIVE QUESTS                                                  │
│  ─────────────────────────────────────────────────────────     │
│  - The Crystal Heart (Main)                                    │
│  - Missing Miners (Side)                                       │
│                                                                  │
│  [A] Load    [X] Delete    [B] Back                            │
└─────────────────────────────────────────────────────────────────┘
```

## Auto-Save System

### Auto-Save Triggers

```python
class AutoSaveManager:
    AUTO_SAVE_TRIGGERS = [
        'room_entered',        # When entering a new room
        'quest_completed',     # After completing a quest
        'boss_defeated',       # After defeating a boss
        'item_acquired',       # When getting important items
        'checkpoint_reached',  # At designated checkpoints
        'time_interval'        # Every N minutes of play
    ]

    def __init__(self):
        self.last_auto_save = time.time()
        self.auto_save_interval = 300  # 5 minutes

    def on_game_event(self, event: str, data: dict) -> None:
        if event in self.AUTO_SAVE_TRIGGERS:
            if self._should_auto_save(event):
                self._perform_auto_save()

    def _should_auto_save(self, event: str) -> bool:
        # Time-based check
        if event == 'time_interval':
            return time.time() - self.last_auto_save >= self.auto_save_interval

        # Event-based saves
        return True

    def _perform_auto_save(self) -> None:
        self.save_manager.save_game(
            slot=AUTO_SAVE_SLOT,
            name=f"Auto-Save ({datetime.now().strftime('%H:%M')})"
        )
        self.last_auto_save = time.time()
```

## Version Migration

### Migration System

```python
class SaveMigrator:
    MIGRATIONS = {
        '1.0': migrate_1_0_to_1_1,
        '1.1': migrate_1_1_to_1_2,
        '1.2': migrate_1_2_to_2_0,
    }

    def migrate_save(self, save_data: SaveFile) -> SaveFile:
        current_version = save_data.version

        while current_version != SAVE_VERSION:
            if current_version not in self.MIGRATIONS:
                raise MigrationError(f"No migration path from {current_version}")

            migration_func = self.MIGRATIONS[current_version]
            save_data = migration_func(save_data)
            current_version = save_data.version

        return save_data

def migrate_1_0_to_1_1(save_data: SaveFile) -> SaveFile:
    """Example migration: Add new skill points field"""
    if 'skillPoints' not in save_data.player:
        save_data.player['skillPoints'] = 0

    save_data.version = '1.1'
    return save_data
```

## Storage Backends

### Local Storage (JSON Files)

```python
class LocalStorageBackend:
    def __init__(self, save_directory: str):
        self.save_dir = Path(save_directory)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def save(self, slot: int, data: str) -> None:
        path = self.save_dir / f"save_{slot}.json"
        with open(path, 'w') as f:
            f.write(data)

    def load(self, slot: int) -> Optional[str]:
        path = self.save_dir / f"save_{slot}.json"
        if not path.exists():
            return None
        with open(path, 'r') as f:
            return f.read()

    def delete(self, slot: int) -> bool:
        path = self.save_dir / f"save_{slot}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_saves(self) -> List[SaveMetadata]:
        saves = []
        for path in self.save_dir.glob("save_*.json"):
            try:
                data = json.loads(path.read_text())
                saves.append(data['metadata'])
            except:
                continue
        return sorted(saves, key=lambda s: s['lastPlayedAt'], reverse=True)
```

### Browser Local Storage

```typescript
class BrowserStorageBackend implements StorageBackend {
  private prefix = 'tilecrawler_save_';

  save(slot: number, data: string): void {
    localStorage.setItem(`${this.prefix}${slot}`, data);
  }

  load(slot: number): string | null {
    return localStorage.getItem(`${this.prefix}${slot}`);
  }

  delete(slot: number): boolean {
    const key = `${this.prefix}${slot}`;
    if (localStorage.getItem(key)) {
      localStorage.removeItem(key);
      return true;
    }
    return false;
  }

  listSaves(): SaveMetadata[] {
    const saves: SaveMetadata[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(this.prefix)) {
        try {
          const data = JSON.parse(localStorage.getItem(key)!);
          saves.push(data.metadata);
        } catch {
          continue;
        }
      }
    }
    return saves.sort((a, b) =>
      new Date(b.lastPlayedAt).getTime() - new Date(a.lastPlayedAt).getTime()
    );
  }
}
```

## Data Integrity

### Checksum Verification

```python
import hashlib

class SaveIntegrity:
    def calculate_checksum(self, save_data: dict) -> str:
        """Calculate SHA-256 checksum of save data"""
        # Remove existing checksum before calculation
        data_copy = save_data.copy()
        data_copy.pop('checksum', None)

        # Serialize deterministically
        json_str = json.dumps(data_copy, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def verify_checksum(self, save_data: dict) -> bool:
        """Verify save data integrity"""
        stored_checksum = save_data.get('checksum')
        if not stored_checksum:
            return False

        calculated = self.calculate_checksum(save_data)
        return stored_checksum == calculated
```

### Backup System

```python
class SaveBackupManager:
    MAX_BACKUPS = 3

    def create_backup(self, slot: int) -> None:
        """Create a backup before overwriting"""
        current_save = self.storage.load(slot)
        if current_save:
            backup_path = f"save_{slot}_backup_{int(time.time())}.json"
            self.storage.save_backup(backup_path, current_save)
            self._cleanup_old_backups(slot)

    def restore_backup(self, slot: int, backup_index: int) -> bool:
        """Restore from a backup"""
        backups = self._list_backups(slot)
        if backup_index >= len(backups):
            return False

        backup_data = self.storage.load_backup(backups[backup_index])
        self.storage.save(slot, backup_data)
        return True

    def _cleanup_old_backups(self, slot: int) -> None:
        """Keep only the most recent backups"""
        backups = self._list_backups(slot)
        while len(backups) > self.MAX_BACKUPS:
            oldest = backups.pop()
            self.storage.delete_backup(oldest)
```

## Performance Optimization

### Incremental Saves

```python
class IncrementalSaveManager:
    def __init__(self):
        self.last_save_state = None
        self.change_buffer = []

    def track_change(self, path: str, value: any) -> None:
        """Track incremental changes"""
        self.change_buffer.append({
            'path': path,
            'value': value,
            'timestamp': time.time()
        })

    def save_incremental(self, slot: int) -> None:
        """Save only changed data"""
        if not self.change_buffer:
            return

        delta = {
            'changes': self.change_buffer,
            'base_version': self.last_save_version
        }

        self.storage.save_delta(slot, delta)
        self.change_buffer = []

    def save_full(self, slot: int) -> None:
        """Full save with snapshot"""
        full_state = self.gather_full_state()
        self.storage.save(slot, full_state)
        self.last_save_state = full_state
        self.change_buffer = []
```

## Error Handling

### Save Error Recovery

```python
class SaveErrorHandler:
    def handle_save_error(self, error: Exception, slot: int) -> SaveResult:
        if isinstance(error, IOError):
            # Storage issue - try alternate location
            return self._try_alternate_storage(slot)
        elif isinstance(error, SerializationError):
            # Data issue - try minimal save
            return self._create_emergency_save(slot)
        else:
            # Unknown error - notify user
            return SaveResult(
                success=False,
                error=f"Save failed: {str(error)}",
                recovery_options=['retry', 'change_slot', 'continue_without_saving']
            )

    def _create_emergency_save(self, slot: int) -> SaveResult:
        """Create a minimal save with essential data only"""
        essential_data = {
            'player': self._get_essential_player_data(),
            'position': self._get_current_position(),
            'inventory': self._get_inventory(),
            'emergency': True
        }
        return self.storage.save(slot, essential_data)
```

## Future Enhancements

1. **Cloud Sync:** Synchronize saves across devices
2. **Save Sharing:** Export/import saves for sharing
3. **Save Analytics:** Track play patterns and statistics
4. **Replay System:** Record and replay gameplay sessions
5. **Achievement Integration:** Link saves with achievement progress
