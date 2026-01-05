"""
Tests for inventory_state.py - Player inventory management.
"""

import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from inventory_state import InventoryState, InventoryItem


class TestInventoryItem:
    """Tests for InventoryItem model."""

    def test_create_item(self):
        """Test creating an inventory item."""
        item = InventoryItem(
            id="sword",
            name="Iron Sword",
            category="weapon"
        )
        assert item.id == "sword"
        assert item.name == "Iron Sword"
        assert item.quantity == 1
        assert item.equipped == False


class TestInventoryState:
    """Tests for InventoryState manager."""

    def test_init_default(self, temp_dir):
        """Test initializing inventory with default items."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        assert inv.gold == 20  # Starting gold
        assert "torch" in inv.items  # Starting item
        assert "healing_potion" in inv.items  # Starting item

    def test_add_item_new(self, temp_dir):
        """Test adding a new item."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        success, msg = inv.add_item(
            item_id="sword",
            name="Iron Sword",
            category="weapon"
        )

        assert success == True
        assert "sword" in inv.items
        assert inv.items["sword"].name == "Iron Sword"

    def test_add_item_stack(self, temp_dir):
        """Test adding to existing stack."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        # Torch is a starting item with quantity 2
        success, msg = inv.add_item(
            item_id="torch",
            name="Torch",
            category="tool",
            quantity=3
        )

        assert success == True
        assert inv.items["torch"].quantity == 5  # 2 + 3

    def test_add_item_inventory_full(self, temp_dir):
        """Test adding item when inventory is full."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"), max_slots=3)

        # Already have 2 items, add one more to fill
        inv.add_item("item1", "Item 1")

        # This should fail
        success, msg = inv.add_item("item2", "Item 2")

        assert success == False
        assert "full" in msg.lower()

    def test_remove_item(self, temp_dir):
        """Test removing an item."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        success, msg = inv.remove_item("torch", 1)

        assert success == True
        assert inv.items["torch"].quantity == 1  # Had 2, now 1

    def test_remove_item_all(self, temp_dir):
        """Test removing all of an item."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        success, msg = inv.remove_item("healing_potion", 1)

        assert success == True
        assert "healing_potion" not in inv.items

    def test_remove_item_not_enough(self, temp_dir):
        """Test removing more than available."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        success, msg = inv.remove_item("healing_potion", 10)

        assert success == False
        assert "not enough" in msg.lower()

    def test_use_item(self, temp_dir):
        """Test using a consumable item."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        success, msg, effect = inv.use_item("healing_potion")

        assert success == True
        assert effect is not None
        assert effect["item_id"] == "healing_potion"
        assert "healing_potion" not in inv.items  # Consumed

    def test_use_item_non_consumable(self, temp_dir):
        """Test using a non-consumable item fails."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))
        inv.add_item("sword", "Iron Sword", category="weapon")

        success, msg, effect = inv.use_item("sword")

        assert success == False
        assert effect is None

    def test_has_item(self, temp_dir):
        """Test checking if item exists."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        assert inv.has_item("torch") == True
        assert inv.has_item("torch", 2) == True
        assert inv.has_item("torch", 10) == False
        assert inv.has_item("nonexistent") == False

    def test_add_gold(self, temp_dir):
        """Test adding gold."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        msg = inv.add_gold(50)

        assert inv.gold == 70  # 20 + 50
        assert "50" in msg

    def test_remove_gold(self, temp_dir):
        """Test removing gold."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        success, msg = inv.remove_gold(10)

        assert success == True
        assert inv.gold == 10

    def test_remove_gold_insufficient(self, temp_dir):
        """Test removing more gold than available."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        success, msg = inv.remove_gold(100)

        assert success == False
        assert inv.gold == 20  # Unchanged

    def test_equip_item(self, temp_dir):
        """Test equipping an item."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))
        inv.add_item("sword", "Iron Sword", category="weapon", slot="main_hand")

        success, msg = inv.equip_item("sword")

        assert success == True
        assert inv.items["sword"].equipped == True
        assert inv.equipment.main_hand == "sword"

    def test_unequip_item(self, temp_dir):
        """Test unequipping an item."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))
        inv.add_item("sword", "Iron Sword", category="weapon", slot="main_hand")
        inv.equip_item("sword")

        success, msg = inv.unequip_item("sword")

        assert success == True
        assert inv.items["sword"].equipped == False
        assert inv.equipment.main_hand is None

    def test_get_inventory_list(self, temp_dir):
        """Test getting inventory as list."""
        inv = InventoryState(save_path=os.path.join(temp_dir, "inv.json"))

        items = inv.get_inventory_list()

        assert isinstance(items, list)
        assert len(items) >= 2  # Starting items
        assert all("id" in item for item in items)

    def test_save_and_load(self, temp_dir):
        """Test saving and loading inventory."""
        save_path = os.path.join(temp_dir, "inv.json")
        inv = InventoryState(save_path=save_path)

        inv.add_item("sword", "Iron Sword", category="weapon")
        inv.add_gold(100)
        inv.save()

        # Load in new instance
        inv2 = InventoryState(save_path=save_path)

        assert "sword" in inv2.items
        assert inv2.gold == 120  # 20 starting + 100
