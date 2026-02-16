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
            return ActionResult(
                success=False,
                message="Cannot pick up items during combat!",
                narrative="Focus on the battle at hand!"
            )

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
            return ActionResult(
                success=False,
                message=f"Item '{item_id}' not found in this room",
                narrative="You don't see that item here."
            )

        # Get item data
        item_template = self.item_data.get(item_id, {})
        item_name = item_found.get("name", item_template.get("name", item_id))
        item_desc = item_template.get("description", "")
        category = item_template.get("category", "misc")
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
            quantity=item_found.get("quantity", 1),
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
        """Use an item from inventory."""
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

        if effect_type == "heal":
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
            state_changes={"item_used": item_id}
        )

    async def talk(self, player_input: str = "") -> ActionResult:
        """Talk to an NPC in the current room."""
        if self.combat_engine.combat and self.combat_engine.combat.in_combat:
            return ActionResult(
                success=False,
                message="Cannot talk during combat!",
                narrative="Now is not the time for conversation!"
            )

        room = self.world.get_current_room()
        if not room or not room.npcs:
            return ActionResult(
                success=False,
                message="No one to talk to here",
                narrative="You speak to the empty room. The dungeon does not answer."
            )

        # Get NPC data
        npc_id = room.npcs[0]  # Talk to first NPC
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
            return ActionResult(
                success=False,
                message="Cannot rest during combat!",
                narrative="The enemy won't let you rest!"
            )

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
