# RPG Systems Design Document

## Overview

The RPG Systems form the mechanical backbone of Tile-Crawler, providing character progression, combat mechanics, equipment management, and skill systems. These systems work in harmony with the LLM layer to create meaningful gameplay choices.

## Core Systems

```
┌─────────────────────────────────────────────────────────────────┐
│                        RPG Systems                               │
│                                                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │  Character  │ │   Combat    │ │  Equipment  │ │   Skill   │ │
│  │   Stats     │ │   System    │ │   System    │ │   Tree    │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └─────┬─────┘ │
│         │               │               │               │       │
│         └───────────────┴───────────────┴───────────────┘       │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   Game Balance Engine                    │   │
│  │  (Damage calculation, level scaling, difficulty curves) │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Character Statistics

### Primary Stats

| Stat | Abbreviation | Description | Effects |
|------|--------------|-------------|---------|
| **Strength** | STR | Physical power | Melee damage, carry capacity |
| **Dexterity** | DEX | Agility and finesse | Accuracy, dodge, ranged damage |
| **Constitution** | CON | Endurance | HP, poison/disease resistance |
| **Intelligence** | INT | Mental acuity | Magic damage, skill points |
| **Wisdom** | WIS | Perception | Detection, magic resistance |
| **Charisma** | CHA | Social ability | NPC reactions, prices |

### Derived Stats

```typescript
interface DerivedStats {
  maxHP: number;        // Base 10 + (CON * 5) + (Level * 3)
  maxMP: number;        // Base 5 + (INT * 3) + (Level * 2)
  attack: number;       // STR + weapon damage + bonuses
  defense: number;      // DEX/2 + armor + bonuses
  accuracy: number;     // DEX + skill bonuses
  evasion: number;      // DEX + armor penalty + bonuses
  initiative: number;   // DEX + WIS/2
  critChance: number;   // Base 5% + DEX/10
  critDamage: number;   // Base 150% + STR/5%
}
```

### Stat Calculation

```python
class StatCalculator:
    def calculate_derived_stats(self, character: Character) -> DerivedStats:
        base = character.base_stats
        equipment = character.equipment.get_total_bonuses()
        buffs = character.active_buffs.get_total_bonuses()

        return DerivedStats(
            max_hp=10 + (base.con * 5) + (character.level * 3) + equipment.hp + buffs.hp,
            max_mp=5 + (base.int * 3) + (character.level * 2) + equipment.mp + buffs.mp,
            attack=base.str + equipment.attack + buffs.attack,
            defense=(base.dex // 2) + equipment.defense + buffs.defense,
            accuracy=base.dex + equipment.accuracy + buffs.accuracy,
            evasion=base.dex - equipment.armor_penalty + buffs.evasion,
            initiative=base.dex + (base.wis // 2) + buffs.initiative,
            crit_chance=0.05 + (base.dex / 1000) + equipment.crit_chance,
            crit_damage=1.5 + (base.str / 500) + equipment.crit_damage
        )
```

## Combat System

### Combat Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      Turn-Based Combat Flow                      │
│                                                                  │
│   ┌─────────────┐                                               │
│   │ Combat      │                                               │
│   │ Initiated   │                                               │
│   └──────┬──────┘                                               │
│          │                                                       │
│          ▼                                                       │
│   ┌─────────────┐     ┌──────────────────────────────────────┐ │
│   │ Determine   │     │ Initiative Order:                     │ │
│   │ Initiative  │────▶│ 1. Player (Init: 15)                 │ │
│   └──────┬──────┘     │ 2. Goblin A (Init: 12)               │ │
│          │            │ 3. Goblin B (Init: 8)                │ │
│          │            └──────────────────────────────────────┘ │
│          ▼                                                       │
│   ┌─────────────┐                                               │
│   │ Turn Loop   │◀─────────────────────────────────┐           │
│   └──────┬──────┘                                  │           │
│          │                                          │           │
│          ▼                                          │           │
│   ┌─────────────┐     ┌─────────────┐              │           │
│   │ Current     │────▶│ Execute     │              │           │
│   │ Actor Acts  │     │ Action      │              │           │
│   └─────────────┘     └──────┬──────┘              │           │
│                              │                      │           │
│                              ▼                      │           │
│                       ┌─────────────┐              │           │
│                       │ Apply       │              │           │
│                       │ Effects     │              │           │
│                       └──────┬──────┘              │           │
│                              │                      │           │
│                              ▼                      │           │
│                       ┌─────────────┐   No         │           │
│                       │ Combat      │──────────────┘           │
│                       │ Over?       │                           │
│                       └──────┬──────┘                           │
│                              │ Yes                              │
│                              ▼                                   │
│                       ┌─────────────┐                           │
│                       │ Resolve     │                           │
│                       │ Combat      │                           │
│                       └─────────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

### Combat Controls

Combat uses **Xbox controller** and **keyboard** exclusively:

#### Controller Combat Controls

| Input | Action |
|-------|--------|
| **Left Stick** | Navigate targets / Menu options |
| **D-Pad** | Quick select actions (Up: Attack, Down: Defend, Left: Item, Right: Skill) |
| **A Button** | Confirm action / Execute attack |
| **B Button** | Cancel / Back |
| **X Button** | Primary Attack |
| **Y Button** | Open skill menu |
| **LB** | Previous target |
| **RB** | Next target |
| **LT** | Defend / Block stance |
| **RT** | Heavy attack / Power move |
| **Left Stick Click** | Toggle auto-battle |
| **Start** | Pause / Tactics menu |

#### Keyboard Combat Controls

| Key | Action |
|-----|--------|
| **Arrow Keys / WASD** | Navigate targets / Menu |
| **1** | Basic Attack |
| **2** | Defend |
| **3** | Use Item |
| **4** | Special Skill |
| **Space / Enter** | Confirm |
| **Escape** | Cancel / Back |
| **Tab** | Cycle targets |
| **Shift + Tab** | Cycle targets (reverse) |
| **Q** | Quick skill 1 |
| **E** | Quick skill 2 |
| **R** | Quick skill 3 |
| **F** | Heavy attack |
| **Shift** | Hold for defend stance |

### Combat UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                       Combat Screen                              │
│                                                                  │
│    Enemy Side                              Player Side           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │     G     G                                    @          │  │
│  │   Goblin  Goblin                            Player        │  │
│  │   HP ████░░░░  HP █████░░░░                 HP ████████   │  │
│  │   [12/20]       [15/20]                      [45/50]     │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ > Attack selected target                                  │  │
│  │   Estimated damage: 8-12                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐              │
│  │[X]Attack│ │[LT]Defend│ │[Y]Skills│ │[LB]Items│              │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘              │
│                                                                  │
│  [LB/RB] Change Target    [A] Confirm    [B] Cancel             │
└─────────────────────────────────────────────────────────────────┘
```

### Damage Calculation

```python
class DamageCalculator:
    def calculate_damage(
        self,
        attacker: Character,
        defender: Character,
        action: CombatAction
    ) -> DamageResult:
        # Base damage
        base_damage = action.base_damage + attacker.stats.attack

        # Accuracy check
        hit_chance = (attacker.stats.accuracy - defender.stats.evasion + 70) / 100
        hit_chance = max(0.05, min(0.95, hit_chance))  # 5% min, 95% max

        if random.random() > hit_chance:
            return DamageResult(damage=0, hit=False, crit=False)

        # Critical hit check
        is_crit = random.random() < attacker.stats.crit_chance
        if is_crit:
            base_damage *= attacker.stats.crit_damage

        # Defense reduction
        damage_reduction = defender.stats.defense / (defender.stats.defense + 50)
        final_damage = base_damage * (1 - damage_reduction)

        # Apply elemental modifiers
        final_damage *= self.get_elemental_modifier(action.element, defender)

        # Randomize slightly (+/- 10%)
        final_damage *= random.uniform(0.9, 1.1)

        return DamageResult(
            damage=int(final_damage),
            hit=True,
            crit=is_crit
        )
```

## Equipment System

### Equipment Slots

```typescript
interface EquipmentSlots {
  weapon: Weapon | null;
  offhand: Shield | Weapon | null;  // Dual-wield or shield
  head: Armor | null;
  body: Armor | null;
  hands: Armor | null;
  feet: Armor | null;
  accessory1: Accessory | null;
  accessory2: Accessory | null;
}
```

### Item Rarity

| Rarity | Color | Drop Rate | Stat Bonus |
|--------|-------|-----------|------------|
| Common | White | 60% | 0% |
| Uncommon | Green | 25% | +10-20% |
| Rare | Blue | 10% | +25-40% |
| Epic | Purple | 4% | +50-75% |
| Legendary | Orange | 1% | +100%+ |

### Equipment UI Navigation

```
┌─────────────────────────────────────────────────────────────────┐
│                      Equipment Screen                            │
│                                                                  │
│   Character Model          Equipment Slots                       │
│  ┌─────────────────┐      ┌───────────────────────────────────┐ │
│  │                 │      │  [Head]     Iron Helmet      +5 DEF │ │
│  │       ☺         │      │  [Body]     Leather Armor   +8 DEF │ │
│  │      /|\        │      │ >[Weapon]   Steel Sword    +12 ATK │ │ ← Cursor
│  │      / \        │      │  [Offhand]  Wooden Shield   +3 DEF │ │
│  │                 │      │  [Hands]    Empty                   │ │
│  │ Level: 5        │      │  [Feet]     Boots           +2 DEF │ │
│  │ Class: Warrior  │      │  [Acc. 1]   Ring of Power  +5 STR │ │
│  └─────────────────┘      │  [Acc. 2]   Empty                   │ │
│                           └───────────────────────────────────┘ │
│                                                                  │
│  Stats:                    Item Details:                        │
│  ATK: 24 (+12)            Steel Sword (Rare)                    │
│  DEF: 18 (+18)            "A well-forged blade."                │
│  ACC: 15                   +12 Attack                           │
│  EVA: 8 (-3)               +5% Critical Chance                  │
│                                                                  │
│  [A] Equip    [X] Compare    [Y] Info    [B] Back               │
└─────────────────────────────────────────────────────────────────┘
```

## Skill System

### Skill Categories

```typescript
enum SkillCategory {
  COMBAT = 'combat',      // Damage abilities
  MAGIC = 'magic',        // Spells
  SUPPORT = 'support',    // Buffs/heals
  PASSIVE = 'passive',    // Always-on effects
  UTILITY = 'utility'     // Non-combat skills
}

interface Skill {
  id: string;
  name: string;
  category: SkillCategory;
  mpCost: number;
  cooldown: number;       // Turns
  requirements: SkillRequirement[];
  effects: SkillEffect[];
  description: string;
}
```

### Skill Tree

```
                    ┌─────────────┐
                    │   WARRIOR   │
                    │   (Base)    │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
     ┌───────────┐  ┌───────────┐  ┌───────────┐
     │  Power    │  │  Defense  │  │  Weapon   │
     │  Strike   │  │  Stance   │  │  Mastery  │
     └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
           │              │              │
     ┌─────┴─────┐  ┌─────┴─────┐  ┌─────┴─────┐
     │           │  │           │  │           │
     ▼           ▼  ▼           ▼  ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Cleave  │ │Shield   │ │ Riposte │ │ Dual    │
│         │ │ Bash    │ │         │ │ Wield   │
└─────────┘ └─────────┘ └─────────┘ └─────────┘
```

### Skill Tree Navigation

```
┌─────────────────────────────────────────────────────────────────┐
│                       Skill Tree                                 │
│                                                                  │
│                     ┌─────────────┐                             │
│                     │   ★ BASE    │                             │
│                     └──────┬──────┘                             │
│                            │                                     │
│            ┌───────────────┼───────────────┐                    │
│            │               │               │                    │
│        ┌───┴───┐      ┌────┴────┐     ┌────┴───┐               │
│        │ ★ ATK │      │[★]DEF   │     │ ○ MAG  │               │ ← Cursor on DEF
│        └───┬───┘      └────┬────┘     └────┬───┘               │
│            │               │               │                    │
│       ┌────┴────┐    ┌─────┴────┐    ┌─────┴────┐              │
│       │ ★ SKILL│    │ ○ SKILL │    │ ○ SKILL │              │
│       └─────────┘    └──────────┘    └──────────┘              │
│                                                                  │
│  ★ = Unlocked    ○ = Locked    [★] = Selected                  │
│                                                                  │
│  Selected: Defense Stance                                        │
│  "Reduce incoming damage by 30% for 3 turns"                    │
│  MP Cost: 8    Cooldown: 5 turns                                │
│  Requirements: Level 3, Base Skill                              │
│                                                                  │
│  Skill Points: 3                                                │
│                                                                  │
│  [Left Stick/D-Pad] Navigate    [A] Unlock/Info    [B] Back    │
└─────────────────────────────────────────────────────────────────┘
```

## Level Progression

### Experience Table

```python
def calculate_xp_for_level(level: int) -> int:
    """Experience required to reach a level"""
    return int(100 * (level ** 1.5))

# Level 1: 100 XP
# Level 2: 283 XP
# Level 3: 520 XP
# Level 5: 1,118 XP
# Level 10: 3,162 XP
# Level 20: 8,944 XP
```

### Level Up Rewards

```typescript
interface LevelUpRewards {
  statPoints: number;      // Points to allocate to primary stats
  skillPoints: number;     // Points for skill tree
  hpIncrease: number;      // Flat HP bonus
  mpIncrease: number;      // Flat MP bonus
  unlockedSkills: string[]; // Skills that become available
}

const LEVEL_UP_REWARDS: Record<number, LevelUpRewards> = {
  2: { statPoints: 2, skillPoints: 1, hpIncrease: 5, mpIncrease: 2, unlockedSkills: [] },
  3: { statPoints: 2, skillPoints: 1, hpIncrease: 5, mpIncrease: 2, unlockedSkills: ['power_strike'] },
  5: { statPoints: 3, skillPoints: 1, hpIncrease: 10, mpIncrease: 5, unlockedSkills: ['cleave'] },
  // ...
};
```

## Status Effects

### Effect Types

| Effect | Type | Description |
|--------|------|-------------|
| Poison | Damage | X damage per turn for Y turns |
| Burn | Damage | X fire damage per turn |
| Bleed | Damage | X damage when moving |
| Stun | Control | Skip next turn |
| Slow | Debuff | -50% initiative |
| Blind | Debuff | -50% accuracy |
| Weaken | Debuff | -25% attack |
| Regen | Buff | Heal X per turn |
| Haste | Buff | +50% initiative |
| Shield | Buff | Absorb X damage |
| Strengthen | Buff | +25% attack |

### Effect Processing

```python
class StatusEffectProcessor:
    def process_turn_start(self, character: Character) -> List[EffectResult]:
        results = []
        for effect in character.status_effects:
            if effect.triggers_on == 'turn_start':
                result = self.apply_effect(character, effect)
                results.append(result)

            effect.remaining_turns -= 1
            if effect.remaining_turns <= 0:
                character.status_effects.remove(effect)
                results.append(EffectResult(
                    effect_name=effect.name,
                    message=f"{effect.name} wore off"
                ))

        return results
```

## Inventory Management

### Inventory UI

```
┌─────────────────────────────────────────────────────────────────┐
│                        Inventory                                 │
│                                                                  │
│  Categories: [All] [Weapons] [Armor] [Items] [Quest]            │
│              ^^^^                                                │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ >[Healing Potion] x5     Restores 50 HP                   │  │
│  │  [Mana Potion] x3        Restores 30 MP                   │  │
│  │  [Antidote] x2           Cures poison                     │  │
│  │  [Torch] x8              Illuminates dark areas           │  │
│  │  [Steel Sword]           ATK +12 (Equipped)               │  │
│  │  [Iron Helmet]           DEF +5 (Equipped)                │  │
│  │  [Rusty Key]             Opens something...               │  │
│  │  [Ancient Map]           Quest item                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Weight: 45/100                Gold: 1,250                      │
│                                                                  │
│  [A] Use    [X] Equip    [Y] Drop    [LB/RB] Category          │
│  [Left Stick/D-Pad] Navigate              [B] Close            │
└─────────────────────────────────────────────────────────────────┘
```

### Item Management Controls

| Controller | Keyboard | Action |
|------------|----------|--------|
| A Button | Space/Enter | Use item |
| X Button | E | Equip/Unequip |
| Y Button | D | Drop item |
| LB/RB | Q/E | Switch category |
| Left Stick/D-Pad | Arrows/WASD | Navigate |
| B Button | Escape/I | Close inventory |

## Balance Considerations

### Difficulty Scaling

```python
class DifficultyScaler:
    def scale_enemy(self, base_enemy: Enemy, zone_level: int, player_level: int) -> Enemy:
        level_diff = zone_level - player_level
        scale_factor = 1.0 + (level_diff * 0.1)  # 10% per level difference

        scaled = base_enemy.copy()
        scaled.hp = int(base_enemy.hp * scale_factor)
        scaled.attack = int(base_enemy.attack * scale_factor)
        scaled.defense = int(base_enemy.defense * scale_factor)
        scaled.xp_reward = int(base_enemy.xp_reward * scale_factor)

        return scaled
```

### Economy Balance

```python
ECONOMY_CONSTANTS = {
    'gold_per_enemy_level': 10,
    'item_sell_ratio': 0.25,        # Sell for 25% of buy price
    'repair_cost_ratio': 0.1,       # 10% of item value
    'inn_rest_cost_per_level': 5,
    'skill_respec_cost': 100,
}
```

## Future Enhancements

1. **Class System:** Multiple playable classes with unique skills
2. **Crafting:** Combine items to create new equipment
3. **Enchanting:** Add magical properties to items
4. **Companions:** Recruit NPCs to fight alongside player
5. **PvP Arena:** Competitive multiplayer combat
