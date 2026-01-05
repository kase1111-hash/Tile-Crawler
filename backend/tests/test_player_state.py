"""
Tests for player_state.py - Player stats, health, and leveling.
"""

import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player_state import PlayerState, PlayerStats, StatusEffect


class TestPlayerStats:
    """Tests for PlayerStats model."""

    def test_default_stats(self):
        """Test default player stats."""
        stats = PlayerStats()
        assert stats.max_hp == 100
        assert stats.current_hp == 100
        assert stats.max_mana == 50
        assert stats.current_mana == 50
        assert stats.base_attack == 5
        assert stats.base_defense == 5


class TestPlayerState:
    """Tests for PlayerState manager."""

    def test_init_default(self, temp_dir):
        """Test initializing player state."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))
        assert ps.name == "Adventurer"
        assert ps.level == 1
        assert ps.experience == 0
        assert ps.is_alive == True

    def test_take_damage(self, temp_dir):
        """Test taking damage."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        damage, is_dead, msg = ps.take_damage(20, "test")

        assert damage > 0
        assert is_dead == False
        assert ps.stats.current_hp < 100
        assert "damage" in msg.lower()

    def test_take_fatal_damage(self, temp_dir):
        """Test fatal damage causes death."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        damage, is_dead, msg = ps.take_damage(200, "test")

        assert is_dead == True
        assert ps.is_alive == False
        assert ps.stats.current_hp == 0
        assert ps.deaths == 1

    def test_heal(self, temp_dir):
        """Test healing."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))
        ps.stats.current_hp = 50

        healed, msg = ps.heal(30, "potion")

        assert healed == 30
        assert ps.stats.current_hp == 80
        assert "healed" in msg.lower()

    def test_heal_cannot_exceed_max(self, temp_dir):
        """Test healing doesn't exceed max HP."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))
        ps.stats.current_hp = 90

        healed, msg = ps.heal(50, "potion")

        assert healed == 10  # Only healed to max
        assert ps.stats.current_hp == 100

    def test_gain_experience(self, temp_dir):
        """Test gaining experience."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        leveled, msg = ps.gain_experience(50)

        assert leveled == False
        assert ps.experience == 50
        assert "gained" in msg.lower()

    def test_level_up(self, temp_dir):
        """Test leveling up."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        leveled, msg = ps.gain_experience(150)  # More than 100 needed

        assert leveled == True
        assert ps.level == 2
        assert ps.stats.max_hp == 110  # +10 per level
        assert "level up" in msg.lower()

    def test_use_mana(self, temp_dir):
        """Test using mana."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        success, msg = ps.use_mana(20)

        assert success == True
        assert ps.stats.current_mana == 30

    def test_use_mana_insufficient(self, temp_dir):
        """Test using mana when insufficient."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        success, msg = ps.use_mana(100)

        assert success == False
        assert ps.stats.current_mana == 50  # Unchanged

    def test_add_status_effect(self, temp_dir):
        """Test adding status effects."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        effect = StatusEffect(
            id="poison",
            name="Poison",
            effect_type="dot",
            damage_per_turn=5,
            duration=3
        )

        msg = ps.add_status_effect(effect)

        assert len(ps.status_effects) == 1
        assert ps.status_effects[0].id == "poison"

    def test_process_status_effects(self, temp_dir):
        """Test processing status effects each turn."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        effect = StatusEffect(
            id="poison",
            name="Poison",
            effect_type="dot",
            damage_per_turn=5,
            duration=2
        )
        ps.add_status_effect(effect)

        messages = ps.process_status_effects()

        assert len(messages) > 0
        assert ps.stats.current_hp < 100  # Took damage
        assert ps.status_effects[0].duration == 1  # Duration decreased

    def test_respawn(self, temp_dir):
        """Test respawning after death."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))
        ps.take_damage(200, "test")  # Kill player

        msg = ps.respawn()

        assert ps.is_alive == True
        assert ps.stats.current_hp == 50  # Half HP
        assert len(ps.status_effects) == 0

    def test_full_rest(self, temp_dir):
        """Test full rest recovery."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))
        ps.stats.current_hp = 30
        ps.stats.current_mana = 10

        msg = ps.full_rest()

        assert ps.stats.current_hp == 100
        assert ps.stats.current_mana == 50

    def test_get_effective_stat_with_modifiers(self, temp_dir):
        """Test getting stats with modifiers applied."""
        ps = PlayerState(save_path=os.path.join(temp_dir, "player.json"))

        buff = StatusEffect(
            id="strength_buff",
            name="Strength",
            effect_type="buff",
            stat_modifiers={"attack": 10},
            duration=5
        )
        ps.add_status_effect(buff)

        effective_attack = ps.get_effective_stat("attack")

        assert effective_attack == 15  # 5 base + 10 buff

    def test_save_and_load(self, temp_dir):
        """Test saving and loading player state."""
        save_path = os.path.join(temp_dir, "player.json")
        ps = PlayerState(save_path=save_path)

        ps.name = "TestHero"
        ps.gain_experience(50)
        ps.take_damage(20, "test")
        ps.save()

        # Load in new instance
        ps2 = PlayerState(save_path=save_path)

        assert ps2.name == "TestHero"
        assert ps2.experience == 50
        assert ps2.stats.current_hp < 100
