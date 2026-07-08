"""Tests for interaction engine: item effects, NPC dialogue flow, rest."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from interaction_engine import InteractionEngine
from combat_engine import CombatEngine, CombatState
from player_state import PlayerState, StatusEffect
from narrative_memory import NarrativeMemory
from world_state import WorldState, RoomData
from exceptions import CombatActiveError, ItemNotFoundError
from inventory_state import InventoryState


@pytest.fixture
def deps(tmp_path):
    """Create all dependencies for InteractionEngine."""
    player = PlayerState(save_path=str(tmp_path / "player.json"))
    narrative = NarrativeMemory(save_path=str(tmp_path / "narrative.json"))
    world = WorldState(save_path=str(tmp_path / "world.json"))
    inventory = InventoryState(save_path=str(tmp_path / "inventory.json"))

    llm = MagicMock()
    llm.generate_item_description = AsyncMock(return_value="You pick up the item.")
    llm.generate_dialogue = AsyncMock(
        return_value=MagicMock(
            speech="Hello, traveler.", mood="friendly", hints=[], trade_available=False
        )
    )

    item_data = {
        "healing_potion": {
            "name": "Healing Potion",
            "description": "Restores 30 HP",
            "category": "consumable",
            "stackable": True,
            "max_stack": 10,
            "effect": {"type": "heal", "value": 30},
        },
        "mana_potion": {
            "name": "Mana Potion",
            "description": "Restores 25 mana",
            "category": "consumable",
            "stackable": True,
            "max_stack": 10,
            "effect": {"type": "restore_mana", "value": 25},
        },
        "antidote": {
            "name": "Antidote",
            "description": "Cures poison",
            "category": "consumable",
            "stackable": True,
            "max_stack": 5,
            "effect": {"type": "cure_poison"},
        },
        "strength_elixir": {
            "name": "Strength Elixir",
            "description": "Boosts attack",
            "category": "consumable",
            "stackable": True,
            "max_stack": 5,
            "effect": {"type": "buff", "stat": "attack", "value": 5, "duration": 10},
        },
        "smoke_bomb": {
            "name": "Smoke Bomb",
            "description": "Guaranteed escape",
            "category": "consumable",
            "stackable": True,
            "max_stack": 5,
            "effect": {"type": "escape"},
        },
        "torch": {
            "name": "Torch",
            "description": "Light source",
            "category": "tool",
            "stackable": True,
            "max_stack": 5,
            "effect": {"type": "light_source", "radius": 4, "duration": 100},
        },
    }

    enemy_data = {
        "goblin": {"stats": {"hp": 15, "attack": 5, "defense": 2}, "xp_reward": 25},
    }

    combat_engine = CombatEngine(
        player=player,
        narrative=narrative,
        world=world,
        llm=llm,
        enemy_data=enemy_data,
        inventory=inventory,
    )

    engine = InteractionEngine(
        player=player,
        narrative=narrative,
        world=world,
        llm=llm,
        item_data=item_data,
        inventory=inventory,
        combat_engine=combat_engine,
    )

    return {
        "engine": engine,
        "player": player,
        "narrative": narrative,
        "world": world,
        "inventory": inventory,
        "combat_engine": combat_engine,
        "llm": llm,
    }


def _add_room_with_items(world, items=None, npcs=None, features=None):
    """Helper to add a room to the world with items/NPCs."""
    room = RoomData(
        x=0, y=0, z=0,
        map=["▓▓▓▓▓", "▓░░░▓", "▓░@░▓", "▓░░░▓", "▓▓▓▓▓"],
        description="A test room",
        biome="dungeon",
        exits={"south": True},
        enemies=[],
        items=items or [],
        npcs=npcs or [],
        features=features or [],
    )
    world.set_room(room)
    world.update_position(0, 0, 0)


class TestTakeItem:
    """Tests for picking up items."""

    @pytest.mark.asyncio
    async def test_take_item_success(self, deps):
        engine, world, inventory = deps["engine"], deps["world"], deps["inventory"]
        _add_room_with_items(world, items=[{"id": "healing_potion", "name": "Healing Potion"}])

        result = await engine.take_item("healing_potion")

        assert result.success is True
        assert result.state_changes.get("item_added") == "healing_potion"

    @pytest.mark.asyncio
    async def test_take_item_not_in_room(self, deps):
        engine, world = deps["engine"], deps["world"]
        _add_room_with_items(world, items=[])

        with pytest.raises(ItemNotFoundError):
            await engine.take_item("healing_potion")

    @pytest.mark.asyncio
    async def test_take_item_during_combat_blocked(self, deps):
        engine, combat_engine = deps["engine"], deps["combat_engine"]
        combat_engine.combat = CombatState(in_combat=True, enemy_id="goblin")

        with pytest.raises(CombatActiveError):
            await engine.take_item("healing_potion")

    @pytest.mark.asyncio
    async def test_take_item_no_room(self, deps):
        engine = deps["engine"]
        result = await engine.take_item("healing_potion")
        assert result.success is False


class TestUseItemEffects:
    """Tests for item effect processing."""

    def _give_item(self, inventory, item_data, item_id):
        """Add an item to inventory for use."""
        template = item_data[item_id]
        inventory.add_item(
            item_id=item_id,
            name=template["name"],
            description=template["description"],
            category=template["category"],
            quantity=1,
            stackable=template.get("stackable", True),
            max_stack=template.get("max_stack", 99),
        )

    @pytest.mark.asyncio
    async def test_heal_effect(self, deps):
        engine, player, inventory = deps["engine"], deps["player"], deps["inventory"]
        player.stats.current_hp = 50  # damaged
        self._give_item(inventory, deps["engine"].item_data, "healing_potion")

        # Need to set world position for narrative recording
        _add_room_with_items(deps["world"])

        result = await engine.use_item("healing_potion")

        assert result.success is True
        assert player.stats.current_hp == 80  # 50 + 30

    @pytest.mark.asyncio
    async def test_heal_caps_at_max(self, deps):
        engine, player, inventory = deps["engine"], deps["player"], deps["inventory"]
        player.stats.current_hp = 90  # only 10 below max (100)
        self._give_item(inventory, deps["engine"].item_data, "healing_potion")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("healing_potion")

        assert result.success is True
        assert player.stats.current_hp == 100  # capped at max_hp

    @pytest.mark.asyncio
    async def test_mana_restore_effect(self, deps):
        engine, player, inventory = deps["engine"], deps["player"], deps["inventory"]
        player.stats.current_mana = 10
        self._give_item(inventory, deps["engine"].item_data, "mana_potion")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("mana_potion")

        assert result.success is True
        assert player.stats.current_mana == 35  # 10 + 25

    @pytest.mark.asyncio
    async def test_cure_poison_effect(self, deps):
        engine, player, inventory = deps["engine"], deps["player"], deps["inventory"]

        # Apply poison
        poison = StatusEffect(
            id="poison", name="Poison", effect_type="debuff",
            damage_per_turn=5, duration=10, source="spider"
        )
        player.add_status_effect(poison)
        assert any(e.id == "poison" for e in player.status_effects)

        self._give_item(inventory, deps["engine"].item_data, "antidote")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("antidote")

        assert result.success is True
        assert not any(e.id == "poison" for e in player.status_effects)

    @pytest.mark.asyncio
    async def test_buff_effect(self, deps):
        engine, player, inventory = deps["engine"], deps["player"], deps["inventory"]
        self._give_item(inventory, deps["engine"].item_data, "strength_elixir")
        _add_room_with_items(deps["world"])

        base_attack = player.get_effective_stat("attack")
        result = await engine.use_item("strength_elixir")

        assert result.success is True
        assert player.get_effective_stat("attack") == base_attack + 5

    @pytest.mark.asyncio
    async def test_escape_effect_in_combat(self, deps):
        engine, combat_engine, inventory = deps["engine"], deps["combat_engine"], deps["inventory"]
        combat_engine.combat = CombatState(in_combat=True, enemy_id="goblin", enemy_name="Goblin")
        self._give_item(inventory, deps["engine"].item_data, "smoke_bomb")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("smoke_bomb")

        assert result.success is True
        assert combat_engine.combat is None  # escaped

    @pytest.mark.asyncio
    async def test_escape_effect_outside_combat(self, deps):
        engine, inventory = deps["engine"], deps["inventory"]
        self._give_item(inventory, deps["engine"].item_data, "smoke_bomb")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("smoke_bomb")

        assert result.success is True
        assert "dissipates" in result.narrative.lower()

    @pytest.mark.asyncio
    async def test_light_source_effect(self, deps):
        engine, player, inventory = deps["engine"], deps["player"], deps["inventory"]
        self._give_item(inventory, deps["engine"].item_data, "torch")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("torch")

        assert result.success is True
        assert any(e.id == "light_source" for e in player.status_effects)

    @pytest.mark.asyncio
    async def test_use_item_not_in_inventory(self, deps):
        engine = deps["engine"]
        _add_room_with_items(deps["world"])

        result = await engine.use_item("nonexistent")

        assert result.success is False

    @pytest.mark.asyncio
    async def test_use_item_in_combat_costs_a_turn(self, deps):
        """The enemy gets a free attack when you drink a potion mid-fight."""
        engine, combat_engine, player, inventory = (
            deps["engine"], deps["combat_engine"], deps["player"], deps["inventory"]
        )
        combat_engine.combat = CombatState(
            in_combat=True, enemy_id="goblin", enemy_name="Goblin",
            enemy_hp=15, enemy_max_hp=15, enemy_attack=8, turn=1
        )
        player.stats.current_hp = 50
        self._give_item(inventory, deps["engine"].item_data, "healing_potion")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("healing_potion")

        assert result.success is True
        # Healed 30 then took the counterattack, so HP < 80
        assert player.stats.current_hp < 80
        assert combat_engine.combat.turn == 2
        assert result.combat_data is not None
        assert "strikes" in result.narrative.lower()

    @pytest.mark.asyncio
    async def test_use_item_in_combat_counterattack_can_defeat(self, deps):
        """A lethal counterattack resolves as a normal defeat (respawn)."""
        engine, combat_engine, player, inventory = (
            deps["engine"], deps["combat_engine"], deps["player"], deps["inventory"]
        )
        combat_engine.combat = CombatState(
            in_combat=True, enemy_id="goblin", enemy_name="Goblin",
            enemy_hp=15, enemy_max_hp=15, enemy_attack=1000, turn=1
        )
        player.stats.current_hp = 1
        self._give_item(inventory, deps["engine"].item_data, "healing_potion")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("healing_potion")

        assert result.success is False
        assert result.state_changes.get("defeat") is True
        assert combat_engine.combat is None
        assert player.stats.current_hp == player.stats.max_hp // 2  # respawned

    @pytest.mark.asyncio
    async def test_escape_item_in_combat_avoids_counterattack(self, deps):
        """Ending combat with a smoke bomb must not grant the enemy a swing."""
        engine, combat_engine, player, inventory = (
            deps["engine"], deps["combat_engine"], deps["player"], deps["inventory"]
        )
        combat_engine.combat = CombatState(
            in_combat=True, enemy_id="goblin", enemy_name="Goblin",
            enemy_hp=15, enemy_max_hp=15, enemy_attack=1000, turn=1
        )
        hp_before = player.stats.current_hp
        self._give_item(inventory, deps["engine"].item_data, "smoke_bomb")
        _add_room_with_items(deps["world"])

        result = await engine.use_item("smoke_bomb")

        assert result.success is True
        assert combat_engine.combat is None
        assert player.stats.current_hp == hp_before


class TestTalk:
    """Tests for NPC dialogue flow."""

    @pytest.mark.asyncio
    async def test_talk_no_npcs(self, deps):
        engine, world = deps["engine"], deps["world"]
        _add_room_with_items(world, npcs=[])

        result = await engine.talk("Hello")

        assert result.success is False
        assert "No one to talk to" in result.message

    @pytest.mark.asyncio
    async def test_talk_during_combat_blocked(self, deps):
        engine, combat_engine = deps["engine"], deps["combat_engine"]
        combat_engine.combat = CombatState(in_combat=True, enemy_id="goblin")

        with pytest.raises(CombatActiveError):
            await engine.talk("Hello")

    @pytest.mark.asyncio
    async def test_talk_success(self, deps):
        engine, world = deps["engine"], deps["world"]
        _add_room_with_items(world, npcs=["old_sage"])

        # Mock NPC data file
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("os.path.exists", side_effect=lambda p: "npcs.json" not in p):
                result = await engine.talk("Hello there")

        assert result.success is True
        assert result.dialogue_data is not None
        assert result.dialogue_data["speech"] == "Hello, traveler."

    @pytest.mark.asyncio
    async def test_dialogue_history_maintained(self, deps):
        engine, world = deps["engine"], deps["world"]
        _add_room_with_items(world, npcs=["old_sage"])

        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("os.path.exists", side_effect=lambda p: "npcs.json" not in p):
                await engine.talk("Hello")
                await engine.talk("Tell me more")

        assert len(engine.dialogue_history) >= 2

    @pytest.mark.asyncio
    async def test_dialogue_history_trimmed(self, deps):
        engine, world = deps["engine"], deps["world"]
        _add_room_with_items(world, npcs=["old_sage"])

        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch("os.path.exists", side_effect=lambda p: "npcs.json" not in p):
                for i in range(15):
                    await engine.talk(f"Message {i}")

        assert len(engine.dialogue_history) <= 10


class TestRest:
    """Tests for resting mechanics."""

    @pytest.mark.asyncio
    async def test_rest_in_safe_room(self, deps):
        engine, player, world = deps["engine"], deps["player"], deps["world"]
        player.stats.current_hp = 50
        player.stats.current_mana = 20
        _add_room_with_items(world, features=["campfire"])

        result = await engine.rest()

        assert result.success is True
        assert player.stats.current_hp == player.stats.max_hp
        assert player.stats.current_mana == player.stats.max_mana
        assert result.state_changes.get("rested") is True

    @pytest.mark.asyncio
    async def test_rest_in_unsafe_room(self, deps):
        engine, world = deps["engine"], deps["world"]
        _add_room_with_items(world, features=["torch_sconce"])

        result = await engine.rest()

        assert result.success is False
        assert "not safe" in result.message.lower()

    @pytest.mark.asyncio
    async def test_rest_during_combat_blocked(self, deps):
        engine, combat_engine, world = deps["engine"], deps["combat_engine"], deps["world"]
        _add_room_with_items(world, features=["campfire"])
        combat_engine.combat = CombatState(in_combat=True, enemy_id="goblin")

        with pytest.raises(CombatActiveError):
            await engine.rest()

    @pytest.mark.asyncio
    async def test_rest_with_safe_room_feature(self, deps):
        engine, player, world = deps["engine"], deps["player"], deps["world"]
        player.stats.current_hp = 1
        _add_room_with_items(world, features=["safe_room"])

        result = await engine.rest()

        assert result.success is True
        assert player.stats.current_hp == player.stats.max_hp
