"""
Inventory State Management for Tile-Crawler

Handles player inventory, equipment, and item management.
"""

import json
import os
from typing import Optional
from pydantic import BaseModel, Field


class InventoryItem(BaseModel):
    """An item in the player's inventory."""
    id: str
    name: str
    description: str = ""
    category: str = "misc"
    quantity: int = 1
    stackable: bool = True
    max_stack: int = 99
    equipped: bool = False
    slot: Optional[str] = None  # Equipment slot if equippable


class EquipmentSlots(BaseModel):
    """Player equipment slots."""
    head: Optional[str] = None
    body: Optional[str] = None
    main_hand: Optional[str] = None
    off_hand: Optional[str] = None
    ring_1: Optional[str] = None
    ring_2: Optional[str] = None
    amulet: Optional[str] = None


class InventoryState:
    """
    Manages player inventory and equipment.
    """

    def __init__(self, save_path: str = "inventory_state.json", max_slots: int = 20):
        self.save_path = save_path
        self.max_slots = max_slots
        self.items: dict[str, InventoryItem] = {}
        self.equipment: EquipmentSlots = EquipmentSlots()
        self.gold: int = 0
        self._load()

    def _load(self) -> None:
        """Load inventory state from disk."""
        if os.path.exists(self.save_path):
            try:
                with open(self.save_path, 'r') as f:
                    data = json.load(f)
                    self.items = {
                        k: InventoryItem(**v) for k, v in data.get("items", {}).items()
                    }
                    self.equipment = EquipmentSlots(**data.get("equipment", {}))
                    self.gold = data.get("gold", 0)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Warning: Could not load inventory state: {e}")
                self._init_default()
        else:
            self._init_default()

    def _init_default(self) -> None:
        """Initialize default inventory state."""
        self.items = {}
        self.equipment = EquipmentSlots()
        self.gold = 20  # Starting gold

        # Add starting items
        self._add_starting_items()

    def _add_starting_items(self) -> None:
        """Add default starting items."""
        starting_items = [
            InventoryItem(
                id="torch",
                name="Torch",
                description="A wooden torch soaked in pitch.",
                category="tool",
                quantity=2,
                stackable=True,
                max_stack=10
            ),
            InventoryItem(
                id="healing_potion",
                name="Healing Potion",
                description="A ruby-red liquid that mends wounds.",
                category="consumable",
                quantity=1,
                stackable=True,
                max_stack=10
            )
        ]
        for item in starting_items:
            self.items[item.id] = item

    def save(self) -> None:
        """Save inventory state to disk."""
        data = {
            "items": {k: v.model_dump() for k, v in self.items.items()},
            "equipment": self.equipment.model_dump(),
            "gold": self.gold
        }
        with open(self.save_path, 'w') as f:
            json.dump(data, f, indent=2)

    def add_item(
        self,
        item_id: str,
        name: str,
        description: str = "",
        category: str = "misc",
        quantity: int = 1,
        stackable: bool = True,
        max_stack: int = 99,
        slot: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Add an item to the inventory.
        Returns (success, message).
        """
        # Check if we already have this item and it's stackable
        if item_id in self.items and stackable:
            existing = self.items[item_id]
            new_quantity = existing.quantity + quantity
            if new_quantity <= existing.max_stack:
                existing.quantity = new_quantity
                return True, f"Added {quantity}x {name} (now have {new_quantity})"
            else:
                # Add what we can
                can_add = existing.max_stack - existing.quantity
                if can_add > 0:
                    existing.quantity = existing.max_stack
                    return True, f"Added {can_add}x {name} (stack full at {existing.max_stack})"
                return False, f"Cannot carry more {name} (stack full)"

        # Check inventory space for new item
        if len(self.items) >= self.max_slots:
            return False, "Inventory is full"

        # Add new item
        self.items[item_id] = InventoryItem(
            id=item_id,
            name=name,
            description=description,
            category=category,
            quantity=quantity,
            stackable=stackable,
            max_stack=max_stack,
            slot=slot
        )
        return True, f"Picked up {name}" + (f" x{quantity}" if quantity > 1 else "")

    def remove_item(self, item_id: str, quantity: int = 1) -> tuple[bool, str]:
        """
        Remove an item from the inventory.
        Returns (success, message).
        """
        if item_id not in self.items:
            return False, "Item not in inventory"

        item = self.items[item_id]

        # Check if item is equipped
        if item.equipped:
            return False, f"Cannot remove {item.name} while equipped"

        if item.quantity > quantity:
            item.quantity -= quantity
            return True, f"Removed {quantity}x {item.name}"
        elif item.quantity == quantity:
            del self.items[item_id]
            return True, f"Removed {item.name}"
        else:
            return False, f"Not enough {item.name} (have {item.quantity}, need {quantity})"

    def use_item(self, item_id: str) -> tuple[bool, str, Optional[dict]]:
        """
        Use a consumable item.
        Returns (success, message, effect_data).
        """
        if item_id not in self.items:
            return False, "Item not in inventory", None

        item = self.items[item_id]

        if item.category != "consumable" and item.category != "scroll":
            return False, f"Cannot use {item.name}", None

        # Remove one from stack
        success, msg = self.remove_item(item_id, 1)
        if not success:
            return False, msg, None

        # Return effect data for the game engine to process
        effect_data = {
            "item_id": item_id,
            "item_name": item.name,
            "category": item.category
        }

        return True, f"Used {item.name}", effect_data

    def equip_item(self, item_id: str) -> tuple[bool, str]:
        """Equip an item to its slot."""
        if item_id not in self.items:
            return False, "Item not in inventory"

        item = self.items[item_id]

        if not item.slot:
            return False, f"{item.name} cannot be equipped"

        slot = item.slot

        # Handle two-handed weapons
        if slot == "two_hand":
            # Unequip both hand slots
            self._unequip_slot("main_hand")
            self._unequip_slot("off_hand")
            # Equip to main_hand (two_hand uses main_hand slot)
            setattr(self.equipment, "main_hand", item_id)
            item.equipped = True
            return True, f"Equipped {item.name} (two-handed)"

        # Unequip current item in slot
        current = getattr(self.equipment, slot, None)
        if current:
            self._unequip_slot(slot)

        # Equip new item
        setattr(self.equipment, slot, item_id)
        item.equipped = True
        return True, f"Equipped {item.name}"

    def unequip_item(self, item_id: str) -> tuple[bool, str]:
        """Unequip an item."""
        if item_id not in self.items:
            return False, "Item not in inventory"

        item = self.items[item_id]

        if not item.equipped:
            return False, f"{item.name} is not equipped"

        # Find and clear the slot
        for slot_name in ["head", "body", "main_hand", "off_hand", "ring_1", "ring_2", "amulet"]:
            if getattr(self.equipment, slot_name) == item_id:
                setattr(self.equipment, slot_name, None)
                item.equipped = False
                return True, f"Unequipped {item.name}"

        return False, f"Could not find equipped slot for {item.name}"

    def _unequip_slot(self, slot: str) -> None:
        """Helper to unequip whatever is in a slot."""
        item_id = getattr(self.equipment, slot, None)
        if item_id and item_id in self.items:
            self.items[item_id].equipped = False
        setattr(self.equipment, slot, None)

    def get_item(self, item_id: str) -> Optional[InventoryItem]:
        """Get an item by ID."""
        return self.items.get(item_id)

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Check if player has an item (and quantity)."""
        item = self.items.get(item_id)
        return item is not None and item.quantity >= quantity

    def add_gold(self, amount: int) -> str:
        """Add gold to the player's purse."""
        self.gold += amount
        return f"Gained {amount} gold (total: {self.gold})"

    def remove_gold(self, amount: int) -> tuple[bool, str]:
        """Remove gold from the player's purse."""
        if self.gold >= amount:
            self.gold -= amount
            return True, f"Spent {amount} gold (remaining: {self.gold})"
        return False, f"Not enough gold (have {self.gold}, need {amount})"

    def get_inventory_list(self) -> list[dict]:
        """Get inventory as a list for display."""
        return [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "category": item.category,
                "quantity": item.quantity,
                "equipped": item.equipped
            }
            for item in self.items.values()
        ]

    def get_equipped_stats(self) -> dict:
        """Calculate total stats from equipped items."""
        stats = {
            "attack": 0,
            "defense": 0,
            "speed": 0,
            "magic": 0
        }
        # Note: Actual stat calculation would need item data from items.json
        # This is a placeholder that returns the structure
        return stats

    def get_inventory_summary(self) -> str:
        """Get a text summary of inventory for LLM context."""
        if not self.items:
            return "Empty inventory"

        lines = [f"Gold: {self.gold}"]
        for item in self.items.values():
            qty = f" x{item.quantity}" if item.quantity > 1 else ""
            eq = " [equipped]" if item.equipped else ""
            lines.append(f"- {item.name}{qty}{eq}")
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset inventory for a new game."""
        self._init_default()
        if os.path.exists(self.save_path):
            os.remove(self.save_path)


# Global instance
_inventory_state: Optional[InventoryState] = None


def get_inventory_state() -> InventoryState:
    """Get the global inventory state instance."""
    global _inventory_state
    if _inventory_state is None:
        _inventory_state = InventoryState()
    return _inventory_state


def reset_inventory_state() -> InventoryState:
    """Reset and return fresh inventory state."""
    global _inventory_state
    if _inventory_state:
        _inventory_state.reset()
    _inventory_state = InventoryState()
    return _inventory_state
