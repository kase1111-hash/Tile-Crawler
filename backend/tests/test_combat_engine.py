"""Tests for combat engine: damage calc, crit chance, flee math."""

import pytest
import random
from unittest.mock import AsyncMock, MagicMock, patch

from combat_engine import (
    CombatEngine,
    CombatState,
    ActionResult,
    CRITICAL_HIT_CHANCE,
    CRITICAL_HIT_MULTIPLIER,
    FLEE_BASE_CHANCE,
    FLEE_SPEED_MODIFIER,
)
from player_state import PlayerState, StatusEffect


@pytest.fixture
def player(tmp_path):
    """Create a fresh player."""
    return PlayerState(save_path=str(tmp_path / "player.json"))


@pytest.fixture
def combat_engine(player, tmp_path):
    """Create a combat engine with mocked dependencies."""
    from narrative_memory import NarrativeMemory
    from world_state import WorldState
    from inventory_state import InventoryState

    narrative = NarrativeMemory(save_path=str(tmp_path / "narrative.json"))
    world = WorldState(save_path=str(tmp_path / "world.json"))
    inventory = InventoryState(save_path=str(tmp_path / "inventory.json"))
    llm = MagicMock()
    llm.generate_combat_narration = AsyncMock(
        return_value=MagicMock(narration="The battle rages on.", dramatic_moment=False)
    )

    enemy_data = {
        "goblin": {"stats": {"hp": 15, "attack": 5, "defense": 2}, "xp_reward": 25},
        "skeleton": {"stats": {"hp": 30, "attack": 8, "defense": 4}, "xp_reward": 50},
    }

    return CombatEngine(
        player=player,
        narrative=narrative,
        world=world,
        llm=llm,
        enemy_data=enemy_data,
        inventory=inventory,
    )


class TestCombatState:
    """Tests for CombatState model."""

    def test_default_state(self):
        state = CombatState()
        assert state.in_combat is False
        assert state.enemy_index == -1
        assert state.enemy_hp == 0
        assert state.turn == 0

    def test_custom_state(self):
        state = CombatState(
            in_combat=True,
            enemy_index=0,
            enemy_id="goblin",
            enemy_name="Goblin",
            enemy_hp=15,
            enemy_max_hp=15,
            enemy_attack=5,
            enemy_defense=2,
            turn=1,
        )
        assert state.in_combat is True
        assert state.enemy_name == "Goblin"
        assert state.enemy_hp == 15


class TestStartCombat:
    """Tests for starting combat."""

    def test_start_combat_from_enemy_dict(self, combat_engine):
        enemy = {"id": "goblin", "name": "Goblin", "hp": 15, "attack": 5, "defense": 2}
        combat_engine.start_combat(0, enemy)

        assert combat_engine.combat is not None
        assert combat_engine.combat.in_combat is True
        assert combat_engine.combat.enemy_id == "goblin"
        assert combat_engine.combat.enemy_name == "Goblin"
        assert combat_engine.combat.enemy_hp == 15
        assert combat_engine.combat.enemy_max_hp == 15
        assert combat_engine.combat.enemy_attack == 5
        assert combat_engine.combat.enemy_defense == 2
        assert combat_engine.combat.turn == 1

    def test_start_combat_uses_template_fallback(self, combat_engine):
        """When enemy dict lacks stats, falls back to enemy_data template."""
        enemy = {"id": "goblin", "name": "Goblin"}
        combat_engine.start_combat(0, enemy)

        assert combat_engine.combat.enemy_hp == 15  # from enemy_data template
        assert combat_engine.combat.enemy_attack == 5

    def test_start_combat_unknown_enemy(self, combat_engine):
        """Unknown enemy gets sensible defaults."""
        enemy = {"id": "unknown_beast", "name": "Unknown Beast"}
        combat_engine.start_combat(0, enemy)

        assert combat_engine.combat.enemy_name == "Unknown Beast"
        assert combat_engine.combat.enemy_hp == 20  # default


class TestDamageCalculation:
    """Tests for the damage formula: max(1, attack - defense//2)."""

    @pytest.mark.asyncio
    async def test_normal_damage(self, combat_engine, player):
        """Damage = max(1, player_attack - enemy_defense // 2)."""
        enemy = {"id": "goblin", "name": "Goblin", "hp": 100, "attack": 5, "defense": 4}
        combat_engine.start_combat(0, enemy)

        # Player base attack = 5, enemy defense = 4, so damage = max(1, 5 - 4//2) = max(1, 3) = 3
        with patch("combat_engine.random.random", return_value=0.5):  # no crit
            result = await combat_engine.attack()

        assert result.success is True
        assert combat_engine.combat.enemy_hp == 97  # 100 - 3

    @pytest.mark.asyncio
    async def test_minimum_damage_is_one(self, combat_engine, player):
        """Damage is always at least 1."""
        enemy = {"id": "goblin", "name": "Goblin", "hp": 100, "attack": 5, "defense": 100}
        combat_engine.start_combat(0, enemy)

        with patch("combat_engine.random.random", return_value=0.5):
            result = await combat_engine.attack()

        assert result.success is True
        assert combat_engine.combat.enemy_hp == 99  # min damage = 1

    @pytest.mark.asyncio
    async def test_critical_hit_doubles_damage(self, combat_engine, player):
        """Critical hit multiplies damage by CRITICAL_HIT_MULTIPLIER (2)."""
        enemy = {"id": "goblin", "name": "Goblin", "hp": 100, "attack": 1, "defense": 0}
        combat_engine.start_combat(0, enemy)

        # Player attack = 5, enemy defense = 0, base damage = 5
        # Crit damage = 5 * 2 = 10
        with patch("combat_engine.random.random", return_value=0.01):  # < 0.05 = crit
            result = await combat_engine.attack()

        assert result.success is True
        assert combat_engine.combat.enemy_hp == 90  # 100 - 10

    @pytest.mark.asyncio
    async def test_attack_with_buff(self, combat_engine, player):
        """Attack buffs increase effective damage."""
        buff = StatusEffect(
            id="attack_buff",
            name="Strength",
            effect_type="buff",
            stat_modifiers={"attack": 10},
            duration=5,
            source="potion",
        )
        player.add_status_effect(buff)

        enemy = {"id": "goblin", "name": "Goblin", "hp": 100, "attack": 1, "defense": 0}
        combat_engine.start_combat(0, enemy)

        # Effective attack = 5 + 10 = 15, enemy defense = 0, damage = 15
        with patch("combat_engine.random.random", return_value=0.5):
            result = await combat_engine.attack()

        assert combat_engine.combat.enemy_hp == 85  # 100 - 15


class TestAttackNotInCombat:
    """Tests for attacking when not in combat."""

    @pytest.mark.asyncio
    async def test_attack_without_combat(self, combat_engine):
        result = await combat_engine.attack()
        assert result.success is False
        assert "Not in combat" in result.message


class TestEnemyCounterattack:
    """Tests for enemy counterattack during player attack."""

    @pytest.mark.asyncio
    async def test_enemy_counterattack_applies_damage(self, combat_engine, player):
        """Enemy attacks back after player attacks."""
        enemy = {"id": "goblin", "name": "Goblin", "hp": 200, "attack": 10, "defense": 0}
        combat_engine.start_combat(0, enemy)

        initial_hp = player.stats.current_hp
        with patch("combat_engine.random.random", return_value=0.5):
            await combat_engine.attack()

        # Enemy attack=10, player defense=5, enemy_damage = max(1, 10 - 5//2) = 8
        # Player take_damage further reduces by defense//2 = 5//2 = 2 → actual = max(1, 8-2) = 6
        assert player.stats.current_hp < initial_hp


class TestVictory:
    """Tests for combat victory."""

    @pytest.mark.asyncio
    async def test_victory_clears_combat(self, combat_engine, player):
        """Killing enemy clears combat state and awards XP."""
        enemy = {"id": "goblin", "name": "Goblin", "hp": 1, "attack": 1, "defense": 0}
        combat_engine.start_combat(0, enemy)

        with patch("combat_engine.random.random", return_value=0.5):
            result = await combat_engine.attack()

        assert result.success is True
        assert result.state_changes.get("victory") is True
        assert result.state_changes.get("combat_ended") is True
        assert combat_engine.combat is None

    @pytest.mark.asyncio
    async def test_victory_awards_xp(self, combat_engine, player):
        enemy = {"id": "goblin", "name": "Goblin", "hp": 1, "attack": 1, "defense": 0}
        combat_engine.start_combat(0, enemy)

        initial_xp = player.experience
        with patch("combat_engine.random.random", return_value=0.5):
            result = await combat_engine.attack()

        assert player.experience > initial_xp
        assert result.state_changes.get("xp_gained") == 25  # goblin xp_reward


class TestDefeat:
    """Tests for combat defeat (player death)."""

    @pytest.mark.asyncio
    async def test_defeat_triggers_respawn(self, combat_engine, player):
        """Player dying triggers respawn and position reset."""
        player.stats.current_hp = 1
        enemy = {"id": "goblin", "name": "Goblin", "hp": 200, "attack": 999, "defense": 0}
        combat_engine.start_combat(0, enemy)

        with patch("combat_engine.random.random", return_value=0.5):
            result = await combat_engine.attack()

        assert result.success is False
        assert result.state_changes.get("defeat") is True
        assert result.state_changes.get("respawned") is True
        assert combat_engine.combat is None
        assert player.is_alive is True  # respawned


class TestFleeFormula:
    """Tests for flee mechanics: flee_chance = FLEE_BASE_CHANCE + speed * FLEE_SPEED_MODIFIER."""

    @pytest.mark.asyncio
    async def test_flee_not_in_combat(self, combat_engine):
        result = await combat_engine.flee()
        assert result.success is False
        assert "Not in combat" in result.message

    @pytest.mark.asyncio
    async def test_flee_success_with_high_roll(self, combat_engine, player):
        """Flee succeeds when roll <= flee_chance."""
        enemy = {"id": "goblin", "name": "Goblin", "hp": 100, "attack": 5, "defense": 2}
        combat_engine.start_combat(0, enemy)

        # Player speed = 5, flee_chance = 50 + 5*2 = 60
        # Roll 1 should always succeed
        with patch("combat_engine.random.randint", return_value=1):
            result = await combat_engine.flee()

        assert result.success is True
        assert result.state_changes.get("fled") is True
        assert combat_engine.combat is None

    @pytest.mark.asyncio
    async def test_flee_failure_with_low_roll(self, combat_engine, player):
        """Flee fails when roll > flee_chance, enemy gets free attack."""
        enemy = {"id": "goblin", "name": "Goblin", "hp": 100, "attack": 5, "defense": 2}
        combat_engine.start_combat(0, enemy)

        initial_hp = player.stats.current_hp
        # Player speed = 5, flee_chance = 60. Roll 100 should always fail.
        with patch("combat_engine.random.randint", return_value=100):
            result = await combat_engine.flee()

        assert result.success is False
        assert player.stats.current_hp < initial_hp  # took damage from free attack
        assert combat_engine.combat is not None  # still in combat

    @pytest.mark.asyncio
    async def test_flee_chance_formula(self, combat_engine, player):
        """Verify the exact flee chance formula."""
        # base speed = 5
        expected_chance = FLEE_BASE_CHANCE + 5 * FLEE_SPEED_MODIFIER  # 50 + 10 = 60
        assert expected_chance == 60

        # With speed buff
        buff = StatusEffect(
            id="speed_buff",
            name="Haste",
            effect_type="buff",
            stat_modifiers={"speed": 10},
            duration=5,
            source="potion",
        )
        player.add_status_effect(buff)

        effective_speed = player.get_effective_stat("speed")  # 5 + 10 = 15
        expected_chance_buffed = FLEE_BASE_CHANCE + effective_speed * FLEE_SPEED_MODIFIER  # 50 + 30 = 80
        assert expected_chance_buffed == 80

    @pytest.mark.asyncio
    async def test_flee_failure_can_kill_player(self, combat_engine, player):
        """Failed flee with very low HP can kill the player."""
        player.stats.current_hp = 1
        enemy = {"id": "goblin", "name": "Goblin", "hp": 100, "attack": 999, "defense": 0}
        combat_engine.start_combat(0, enemy)

        with patch("combat_engine.random.randint", return_value=100):
            result = await combat_engine.flee()

        assert result.state_changes.get("defeat") is True
        assert result.state_changes.get("respawned") is True


class TestCombatConstants:
    """Verify combat constants have expected values."""

    def test_crit_chance(self):
        assert CRITICAL_HIT_CHANCE == 0.05

    def test_crit_multiplier(self):
        assert CRITICAL_HIT_MULTIPLIER == 2

    def test_flee_base_chance(self):
        assert FLEE_BASE_CHANCE == 50

    def test_flee_speed_modifier(self):
        assert FLEE_SPEED_MODIFIER == 2
