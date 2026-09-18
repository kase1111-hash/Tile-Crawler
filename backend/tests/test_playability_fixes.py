"""Regression tests for world consistency, equipment, treasure, scrolls and
LLM fail-fast behaviour."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from openai import APIConnectionError

from combat_engine import CombatState
from llm_engine import LLMEngine
from world_state import RoomData


# ---------------------------------------------------------------------------
# LLM engine: unreachable endpoint must not stall every move
# ---------------------------------------------------------------------------

@pytest.fixture
def online_llm():
    with patch.dict(os.environ, {"OPENAI_API_KEY": "test", "LLM_COOLDOWN_SECONDS": "60"}):
        engine = LLMEngine()
    engine.client = MagicMock()
    engine.client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=httpx.Request("POST", "http://llm.test"))
    )
    return engine


class TestLLMCooldown:
    def test_client_uses_short_timeout_and_retries(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test", "LLM_TIMEOUT_SECONDS": "7", "LLM_MAX_RETRIES": "0"}):
            engine = LLMEngine()
        assert engine.client.timeout == 7
        assert engine.client.max_retries == 0

    @pytest.mark.asyncio
    async def test_connection_error_falls_back_and_starts_cooldown(self, online_llm):
        assert online_llm.is_available() is True

        result = await online_llm.generate_room(
            0, 0, 0, "dungeon", {"south": True}, {}, ""
        )

        assert result is not None and len(result.map) > 0
        assert online_llm.is_available() is False
        assert online_llm.client.chat.completions.create.await_count == 1

        # During the cooldown no further network calls are made
        await online_llm.generate_room(1, 0, 0, "dungeon", {"north": True}, {}, "")
        assert online_llm.client.chat.completions.create.await_count == 1

    @pytest.mark.asyncio
    async def test_cooldown_expires(self, online_llm):
        await online_llm.generate_room(0, 0, 0, "dungeon", {"south": True}, {}, "")
        assert online_llm.is_available() is False
        online_llm._unavailable_until = 0.0
        assert online_llm.is_available() is True

    @pytest.mark.asyncio
    async def test_non_connection_errors_do_not_trigger_cooldown(self, online_llm):
        online_llm.client.chat.completions.create = AsyncMock(side_effect=ValueError("bad"))
        await online_llm.generate_room(0, 0, 0, "dungeon", {"south": True}, {}, "")
        assert online_llm.is_available() is True


# ---------------------------------------------------------------------------
# Game engine: exits and exploration tracking
# ---------------------------------------------------------------------------

@pytest.fixture
def engine(clean_state):
    offline = LLMEngine()
    offline.client = None
    with patch("game_engine.get_llm_engine", return_value=offline):
        from game_engine import GameEngine
        return GameEngine(
            world=clean_state["world"],
            narrative=clean_state["narrative"],
            inventory=clean_state["inventory"],
            player=clean_state["player"],
        )


class TestExitConsistency:
    def test_exits_mirror_existing_neighbours(self, engine):
        world = engine.world
        # East neighbour has no way back west; west neighbour opens east
        world.set_room(RoomData(x=1, y=0, z=0, exits={"south": True}))
        world.set_room(RoomData(x=-1, y=0, z=0, exits={"east": True}))

        for _ in range(50):
            exits = engine._determine_exits(0, 0, 0, "north")
            assert exits["south"] is True
            assert exits.get("west") is True
            assert "east" not in exits

    def test_vertical_exits_mirror_existing_floors(self, engine):
        world = engine.world
        world.set_room(RoomData(x=0, y=0, z=1, exits={"up": True}))
        world.set_room(RoomData(x=0, y=0, z=-1, exits={"north": True}))

        for _ in range(50):
            exits = engine._determine_exits(0, 0, 0, "north")
            assert exits.get("down") is True
            assert "up" not in exits

    def test_descending_keeps_the_way_back_up(self, engine):
        for _ in range(50):
            exits = engine._determine_exits(0, 0, 1, "down")
            assert exits.get("up") is True


class TestExploration:
    @pytest.mark.asyncio
    async def test_prefetched_rooms_are_not_explored(self, engine):
        await engine.new_game("Scout")
        state = engine.get_game_state()
        assert state["stats"]["rooms_explored"] == 1
        assert [(r["x"], r["y"]) for r in state["explored"]] == [(0, 0)]

        prefetched = await engine.prefetch_adjacent_rooms()
        assert prefetched.get("south") is True

        state = engine.get_game_state()
        assert state["stats"]["rooms_explored"] == 1
        assert [(r["x"], r["y"]) for r in state["explored"]] == [(0, 0)]

        # Clear the enemy so the move doesn't start a fight; then the
        # room counts once the player is actually standing in it
        engine.world.get_room(0, 1, 0).enemies = []
        await engine.move("south")
        state = engine.get_game_state()
        assert state["stats"]["rooms_explored"] == 2
        assert sorted((r["x"], r["y"]) for r in state["explored"]) == [(0, 0), (0, 1)]


# ---------------------------------------------------------------------------
# Interaction engine: equipment, treasure, scrolls
# ---------------------------------------------------------------------------

@pytest.fixture
def ideps(tmp_path):
    from interaction_engine import InteractionEngine
    from combat_engine import CombatEngine
    from player_state import PlayerState
    from narrative_memory import NarrativeMemory
    from world_state import WorldState
    from inventory_state import InventoryState

    player = PlayerState(save_path=str(tmp_path / "player.json"))
    narrative = NarrativeMemory(save_path=str(tmp_path / "narrative.json"))
    world = WorldState(save_path=str(tmp_path / "world.json"))
    inventory = InventoryState(save_path=str(tmp_path / "inventory.json"))

    llm = MagicMock()
    llm.generate_item_description = AsyncMock(return_value="You pick up the item.")
    llm.generate_combat_narration = AsyncMock(return_value=MagicMock(narration="The foe falls."))

    item_data = {
        "rusty_sword": {
            "name": "Rusty Sword", "description": "", "category": "weapon",
            "stackable": False, "slot": "main_hand", "stats": {"attack": 3},
        },
        "gold_coins": {
            "name": "Gold Coins", "description": "", "category": "treasure",
            "base_value": 1, "stackable": True, "max_stack": 9999,
        },
        "rare_gem": {
            "name": "Rare Gem", "description": "", "category": "treasure",
            "base_value": 250, "stackable": False,
        },
        "scroll_fireball": {
            "name": "Scroll of Fireball", "description": "", "category": "scroll",
            "stackable": True, "max_stack": 3,
            "effect": {"type": "spell", "spell": "fireball", "damage": 40},
        },
        "scroll_teleport": {
            "name": "Scroll of Teleport", "description": "", "category": "scroll",
            "stackable": True, "max_stack": 3,
            "effect": {"type": "spell", "spell": "teleport"},
        },
    }
    enemy_data = {"goblin": {"stats": {"hp": 15, "attack": 5, "defense": 2}, "xp_reward": 25}}

    combat_engine = CombatEngine(player=player, narrative=narrative, world=world, llm=llm,
                                 enemy_data=enemy_data, inventory=inventory)
    engine = InteractionEngine(player=player, narrative=narrative, world=world, llm=llm,
                               item_data=item_data, inventory=inventory, combat_engine=combat_engine)

    start = RoomData(x=0, y=0, z=0, exits={"south": True}, description="Start")
    world.set_room(start)
    world.update_position(0, 0, 0)

    return {"engine": engine, "player": player, "world": world,
            "inventory": inventory, "combat": combat_engine, "item_data": item_data}


def _give(inventory, item_data, item_id, quantity=1):
    t = item_data[item_id]
    inventory.add_item(item_id=item_id, name=t["name"], category=t["category"], quantity=quantity,
                       stackable=t.get("stackable", True), max_stack=t.get("max_stack", 99),
                       slot=t.get("slot"), stats=t.get("stats", {}))


class TestEquipment:
    @pytest.mark.asyncio
    async def test_use_toggles_equipment(self, ideps):
        engine, inventory = ideps["engine"], ideps["inventory"]
        _give(inventory, ideps["item_data"], "rusty_sword")

        result = await engine.use_item("rusty_sword")
        assert result.success is True
        assert inventory.get_item("rusty_sword").equipped is True
        assert inventory.get_equipped_stats()["attack"] == 3
        assert "equipped" in result.message.lower()

        result = await engine.use_item("rusty_sword")
        assert result.success is True
        assert inventory.get_item("rusty_sword").equipped is False
        assert inventory.get_equipped_stats()["attack"] == 0
        # Equipment is never consumed
        assert inventory.has_item("rusty_sword")

    @pytest.mark.asyncio
    async def test_picked_up_weapon_is_equippable(self, ideps):
        engine, inventory, world = ideps["engine"], ideps["inventory"], ideps["world"]
        world.get_current_room().items = [{"id": "rusty_sword", "name": "Rusty Sword"}]

        await engine.take_item("rusty_sword")
        result = await engine.use_item("rusty_sword")

        assert result.success is True
        assert inventory.get_equipped_stats()["attack"] == 3


class TestTreasure:
    @pytest.mark.asyncio
    async def test_treasure_becomes_gold(self, ideps):
        engine, inventory, world = ideps["engine"], ideps["inventory"], ideps["world"]
        world.get_current_room().items = [
            {"id": "gold_coins", "name": "Gold Coins", "quantity": 12},
            {"id": "rare_gem", "name": "Rare Gem"},
        ]
        start_gold = inventory.gold

        first = await engine.take_item("gold_coins")
        second = await engine.take_item("rare_gem")

        assert first.success and second.success
        assert inventory.gold == start_gold + 12 + 250
        assert not inventory.has_item("gold_coins")
        assert not inventory.has_item("rare_gem")
        assert world.get_current_room().items == []


class TestScrolls:
    @pytest.mark.asyncio
    async def test_fireball_damages_enemy(self, ideps):
        engine, combat, inventory = ideps["engine"], ideps["combat"], ideps["inventory"]
        combat.combat = CombatState(in_combat=True, enemy_id="goblin", enemy_name="Goblin",
                                    enemy_hp=100, enemy_max_hp=100, enemy_attack=1, turn=1)
        _give(inventory, ideps["item_data"], "scroll_fireball")

        result = await engine.use_item("scroll_fireball")

        assert result.success is True
        assert combat.combat.enemy_hp == 60
        assert not inventory.has_item("scroll_fireball")

    @pytest.mark.asyncio
    async def test_fireball_kill_ends_combat_with_victory(self, ideps):
        engine, combat, inventory, player = ideps["engine"], ideps["combat"], ideps["inventory"], ideps["player"]
        combat.combat = CombatState(in_combat=True, enemy_id="goblin", enemy_name="Goblin",
                                    enemy_hp=10, enemy_max_hp=10, enemy_attack=50, turn=1)
        _give(inventory, ideps["item_data"], "scroll_fireball")
        hp_before = player.stats.current_hp

        result = await engine.use_item("scroll_fireball")

        assert result.success is True
        assert result.state_changes.get("victory") is True
        assert combat.combat is None
        # The dead enemy gets no free swing
        assert player.stats.current_hp == hp_before

    @pytest.mark.asyncio
    async def test_fireball_outside_combat_is_wasted(self, ideps):
        engine, inventory = ideps["engine"], ideps["inventory"]
        _give(inventory, ideps["item_data"], "scroll_fireball")

        result = await engine.use_item("scroll_fireball")

        assert result.success is True
        assert not inventory.has_item("scroll_fireball")

    @pytest.mark.asyncio
    async def test_teleport_returns_to_entrance_and_ends_combat(self, ideps):
        engine, combat, inventory, world = ideps["engine"], ideps["combat"], ideps["inventory"], ideps["world"]
        world.set_room(RoomData(x=3, y=2, z=0, exits={"north": True}))
        world.update_position(3, 2, 0)
        combat.combat = CombatState(in_combat=True, enemy_id="goblin", enemy_name="Goblin",
                                    enemy_hp=15, enemy_max_hp=15, enemy_attack=5, turn=1)
        _give(inventory, ideps["item_data"], "scroll_teleport")

        result = await engine.use_item("scroll_teleport")

        assert result.success is True
        assert world.current_position == (0, 0, 0)
        assert combat.combat is None
