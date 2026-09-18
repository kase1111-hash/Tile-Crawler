"""
Interaction Engine for Tile-Crawler

Handles non-combat interactions: picking up items, using items,
talking to NPCs, and resting.
"""

import json
import os
from typing import Optional

from player_state import PlayerState, StatusEffect
from narrative_memory import NarrativeMemory
from world_state import WorldState
from inventory_state import InventoryState
from llm_engine import LLMEngine
from combat_engine import CombatEngine, ActionResult
from exceptions import CombatActiveError, ItemNotFoundError


class InteractionEngine:
    """Handles item interactions, NPC dialogue, and resting."""

    def __init__(
        self,
        player: PlayerState,
        narrative: NarrativeMemory,
        world: WorldState,
        llm: LLMEngine,
        item_data: dict,
        inventory: InventoryState,
        combat_engine: CombatEngine,
    ):
        self.player = player
        self.narrative = narrative
        self.world = world
        self.llm = llm
        self.item_data = item_data
        self.inventory = inventory
        self.combat_engine = combat_engine
        self.current_dialogue_npc: Optional[str] = None
        self.dialogue_history: list[str] = []

    async def take_item(self, item_id: str) -> ActionResult:
        """Pick up an item from the current room."""
        if self.combat_engine.combat and self.combat_engine.combat.in_combat:
            raise CombatActiveError("Cannot pick up items during combat.")

        room = self.world.get_current_room()
        if not room:
            return ActionResult(
                success=False,
                message="No room found",
                narrative="Something is wrong..."
            )

        # Find item in room
        item_found = None
        for item in room.items:
            if item.get("id") == item_id:
                item_found = item
                break

        if not item_found:
            raise ItemNotFoundError(f"Item '{item_id}' not found in this room.")

        # Get item data
        item_template = self.item_data.get(item_id, {})
        item_name = item_found.get("name", item_template.get("name", item_id))
        item_desc = item_template.get("description", "")
        category = item_template.get("category", "misc")
        quantity = item_found.get("quantity", 1)

        # Treasure has no use as an inventory item and there is no shop to
        # sell it at, so it goes straight into the purse at its base value.
        if category == "treasure":
            gold_value = max(1, int(item_template.get("base_value", 1))) * quantity
            x, y, z = self.world.current_position
            self.world.remove_item_from_room(x, y, z, item_id)
            self.inventory.add_gold(gold_value)
            self.narrative.add_item_event(
                action="picked up",
                item_name=item_name,
                location=(x, y, z),
                effect=f"worth {gold_value} gold",
            )
            return ActionResult(
                success=True,
                message=f"Picked up {item_name} (+{gold_value} gold)",
                narrative=f"You pocket the {item_name.lower()}, worth {gold_value} gold.",
                state_changes={"gold_gained": gold_value},
            )

        stackable = item_template.get("stackable", True)
        max_stack = item_template.get("max_stack", 99)
        slot = item_template.get("slot")
        item_stats = item_template.get("stats", {})

        # Add to inventory
        success, msg = self.inventory.add_item(
            item_id=item_id,
            name=item_name,
            description=item_desc,
            category=category,
            quantity=quantity,
            stackable=stackable,
            max_stack=max_stack,
            slot=slot,
            stats=item_stats
        )

        if success:
            # Remove from room
            x, y, z = self.world.current_position
            self.world.remove_item_from_room(x, y, z, item_id)

            # Record event
            self.narrative.add_item_event(
                action="picked up",
                item_name=item_name,
                location=(x, y, z)
            )

            # Generate description
            desc = await self.llm.generate_item_description(
                item_id, item_name, f"Picked up in a {room.biome} room"
            )

            return ActionResult(
                success=True,
                message=msg,
                narrative=desc,
                state_changes={"item_added": item_id}
            )

        return ActionResult(
            success=False,
            message=msg,
            narrative="You couldn't pick that up."
        )

    async def use_item(self, item_id: str) -> ActionResult:
        """Use an item from inventory.

        Consumables are spent for their effect; weapons and armor toggle
        between equipped and unequipped (there is no separate equip action).
        """
        owned = self.inventory.get_item(item_id)
        if owned and owned.slot:
            if owned.equipped:
                success, msg = self.inventory.unequip_item(item_id)
            else:
                success, msg = self.inventory.equip_item(item_id)
            if not success:
                return ActionResult(success=False, message=msg, narrative="You can't equip that.")
            effect_data = {"item_id": item_id, "item_name": owned.name, "category": owned.category}
            effect_msg = msg + "."
            effect_type = "equip"
        else:
            success, msg, effect_data = self.inventory.use_item(item_id)

            if not success:
                return ActionResult(
                    success=False,
                    message=msg,
                    narrative="You can't use that."
                )

            # Process item effect
            item_template = self.item_data.get(item_id, {})
            effect = item_template.get("effect", {})
            effect_type = effect.get("type", "")
            effect_msg = ""

        if effect_type == "equip":
            pass

        elif effect_type == "heal":
            heal_amount = effect.get("value", 30)
            actual_heal, heal_msg = self.player.heal(heal_amount, effect_data["item_name"])
            effect_msg = heal_msg

        elif effect_type == "restore_mana":
            mana_amount = effect.get("value", 25)
            actual_restore, mana_msg = self.player.restore_mana(mana_amount)
            effect_msg = mana_msg

        elif effect_type == "cure_poison":
            self.player.remove_status_effect("poison")
            effect_msg = "The poison fades from your system."

        elif effect_type == "buff":
            stat = effect.get("stat", "attack")
            value = effect.get("value", 5)
            duration = effect.get("duration", 10)
            buff = StatusEffect(
                id=f"buff_{stat}",
                name=f"{stat.capitalize()} Boost",
                effect_type="buff",
                stat_modifiers={stat: value},
                duration=duration,
                source=effect_data["item_name"]
            )
            effect_msg = self.player.add_status_effect(buff)

        elif effect_type == "escape":
            if self.combat_engine.combat and self.combat_engine.combat.in_combat:
                # Guaranteed escape with smoke bomb etc
                self.combat_engine.combat = None
                effect_msg = "You vanish in a cloud of smoke and escape!"
            else:
                effect_msg = "The smoke dissipates uselessly."

        elif effect_type == "light_source":
            # Torch or other light source - adds visibility buff
            radius = effect.get("radius", 4)
            duration = effect.get("duration", 100)
            light_buff = StatusEffect(
                id="light_source",
                name="Torch Light",
                effect_type="buff",
                stat_modifiers={"visibility": radius},
                duration=duration,
                source=effect_data["item_name"]
            )
            self.player.add_status_effect(light_buff)
            effect_msg = f"The {effect_data['item_name'].lower()} flickers to life, casting warm light around you."

        elif effect_type == "spell":
            effect_msg = self._cast_scroll(effect, effect_data["item_name"])

        combat = self.combat_engine.combat
        if combat and combat.in_combat and combat.enemy_hp <= 0:
            return await self.combat_engine._end_combat_victory()

        # Using an item mid-combat costs the turn: the enemy gets a free swing
        # (unless the item just ended the fight, e.g. a smoke bomb)
        if combat and combat.in_combat:
            equip_def = self.inventory.get_equipped_stats().get("defense", 0)
            taken, is_dead, damage_msg = self.player.take_damage(
                combat.enemy_attack, combat.enemy_name, equip_def
            )
            effect_msg = (
                f"{effect_msg} The {combat.enemy_name} strikes while you're "
                f"occupied! {damage_msg}"
            ).strip()
            if is_dead:
                return await self.combat_engine._end_combat_defeat()
            combat.turn += 1

        # Record event
        x, y, z = self.world.current_position
        self.narrative.add_item_event(
            action="used",
            item_name=effect_data["item_name"],
            location=(x, y, z),
            effect=effect_msg
        )

        return ActionResult(
            success=True,
            message=msg,
            narrative=effect_msg or f"You used the {effect_data['item_name']}.",
            state_changes={"item_used": item_id},
            combat_data=combat.model_dump() if combat and combat.in_combat else None
        )

    def _cast_scroll(self, effect: dict, item_name: str) -> str:
        """Resolve a scroll's spell. Returns the narrative message."""
        spell = effect.get("spell", "")
        combat = self.combat_engine.combat
        in_combat = bool(combat and combat.in_combat)

        if spell == "fireball":
            if not in_combat:
                return f"The {item_name} bursts into flame and scorches the empty air."
            damage = int(effect.get("damage", 40))
            combat.enemy_hp -= damage
            if combat.enemy_hp <= 0:
                combat.enemy_hp = 0
                return f"A roaring fireball engulfs the {combat.enemy_name} for {damage} damage!"
            return f"A fireball slams into the {combat.enemy_name} for {damage} damage!"

        if spell == "teleport":
            self.combat_engine.combat = None
            self.world.update_position(0, 0, 0)
            return "The world folds around you. You reappear at the dungeon entrance."

        if spell == "light":
            radius = effect.get("radius", 6)
            duration = effect.get("duration", 50)
            self.player.add_status_effect(StatusEffect(
                id="light_source",
                name="Torch Light",
                effect_type="buff",
                stat_modifiers={"visibility": radius},
                duration=duration,
                source=item_name,
            ))
            return "Brilliant light blooms from the scroll and hangs in the air around you."

        return f"The {item_name} crumbles to dust with no visible effect."

    async def talk(self, player_input: str = "") -> ActionResult:
        """Talk to an NPC in the current room."""
        if self.combat_engine.combat and self.combat_engine.combat.in_combat:
            raise CombatActiveError("Cannot talk during combat.")

        room = self.world.get_current_room()
        if not room or not room.npcs:
            return ActionResult(
                success=False,
                message="No one to talk to here",
                narrative="You speak to the empty room. The dungeon does not answer."
            )

        # Get NPC data
        npc_id = room.npcs[0]  # Talk to first NPC
        # TODO: cache NPC data instead of re-reading JSON on every talk()
        npc_data_path = os.path.join(os.path.dirname(__file__), "..", "data", "npcs.json")
        npc_data = {}
        if os.path.exists(npc_data_path):
            with open(npc_data_path, 'r') as f:
                all_npcs = json.load(f)
                npc_data = all_npcs.get("npcs", {}).get(npc_id, {})

        npc_name = npc_data.get("name", "Stranger")
        personality = npc_data.get("personality", "mysterious")

        # Track NPC relationship
        x, y, z = self.world.current_position
        topic = player_input[:50] if player_input else ""
        self.narrative.record_npc_encounter(
            npc_id=npc_id,
            npc_name=npc_name,
            location=(x, y, z),
            topic=topic
        )

        # Build enriched narrative context with NPC relationship
        narrative_context = self.narrative.get_context_for_llm()
        npc_context = self.narrative.get_npc_context(npc_id)
        if npc_context:
            narrative_context["npc_relationship"] = npc_context

        response = await self.llm.generate_dialogue(
            npc_id=npc_id,
            npc_name=npc_name,
            personality=personality,
            player_input=player_input or "Hello",
            narrative_context=narrative_context,
            dialogue_history=self.dialogue_history
        )

        # Record in history
        if player_input:
            self.dialogue_history.append(f"You: {player_input}")
        self.dialogue_history.append(f"{npc_name}: {response.speech}")

        # Keep history manageable
        if len(self.dialogue_history) > 10:
            self.dialogue_history = self.dialogue_history[-10:]

        # Record event
        self.narrative.add_dialogue_event(
            npc_name=npc_name,
            summary=response.speech[:100],
            location=(x, y, z)
        )

        return ActionResult(
            success=True,
            message=f"Talking to {npc_name}",
            narrative=f'{npc_name}: "{response.speech}"',
            dialogue_data={
                "npc_id": npc_id,
                "npc_name": npc_name,
                "speech": response.speech,
                "mood": response.mood,
                "hints": response.hints,
                "trade_available": response.trade_available
            }
        )

    async def rest(self) -> ActionResult:
        """Rest to recover HP/mana (only in safe rooms)."""
        room = self.world.get_current_room()

        # Check if room is safe (has campfire or is designated safe)
        is_safe = room and ("campfire" in room.features or "safe_room" in room.features)

        if not is_safe:
            return ActionResult(
                success=False,
                message="Cannot rest here - not safe!",
                narrative="This place is too dangerous to rest. Find a safe room first."
            )

        if self.combat_engine.combat and self.combat_engine.combat.in_combat:
            raise CombatActiveError("Cannot rest during combat.")

        rest_msg = self.player.full_rest()

        x, y, z = self.world.current_position
        self.narrative.add_event(
            event_type="rest",
            description="Rested at a safe location.",
            location=(x, y, z)
        )

        return ActionResult(
            success=True,
            message="Rested and recovered",
            narrative=f"You rest by the fire, recovering your strength. {rest_msg}",
            state_changes={"rested": True}
        )
